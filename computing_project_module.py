"""
computing_project_module.py

Helper functions for the computing project.

Main tools:
1)  Find all valid subwords of a given length with a given prefix.
    This runs via a depth-first prefix-tree search, with optional multiprocessing.

2)  Checks if a subword (signed or unsigned) is valid.

3)  Finds all minimal invalid subwords up to a given length.
"""

import csv
import time
from multiprocessing import Pool, cpu_count
from math import log10 as log
import re

### GLOBAL VARIABLES
USE_MULTIPROCESSING = True  # Do we use multiprocessing for finding all valid/invalid subwords?
IGNORE_POWERS = True        # Do we enforce square-free?
PRODUCE_OUTPUT = True       # Do we save the output to a csv file?
IGNORE_SIGNS = False        # Do we check unsigned words?

# Define new data type replacing Arrangement class
# rank:         integer, storing the number of punctures
# regions:      tuple of regions, each a tuple of integers storing the boundary word
# assignment:   a tuple of integers, specifying the generator associated to each edge
type State = tuple[int, tuple[tuple[int, ...], ...], tuple[int, ...]]


#################################################################################
### Private functions
#################################################################################

def _validate_word(word: list[int], rank: int) -> None:
    """
    Validates that a word is a valid reduced word of given rank.
    """

    if not isinstance(word, list) or not word:
        raise ValueError("prefix must be a non-empty list")
    for i, s in enumerate(word):
        if not isinstance(s, int) or s == 0:
            raise TypeError(f"prefix[{i}] must be a non-zero integer, got {s!r}")
        if abs(s) > rank:
            raise ValueError(f"prefix[{i}] has abs value {abs(s)} > rank {rank}")
    for i in range(len(word) - 1):
        if word[i] == -word[i + 1]:
            raise ValueError(f"prefix is not reduced: positions {i} and {i + 1} "
                             f"are {word[i]} and {word[i + 1]}")
        if IGNORE_POWERS and word[i] == word[i + 1]:
            raise ValueError(f"prefix is not reduced (repeated letter): positions {i} and {i + 1}")


def _make_initial_state(rank: int, starting_letter: int) -> State:
    """
    Build the initial State given the rank and starting letter.

    Returns:
        The starting State.
    """
    # Different cases for positive and negative generators.
    if starting_letter > 0:
        arrangement = [-(rank + 1)]
        for i in range(starting_letter + 1, rank + 1):
            arrangement += [i, -i]
        for i in range(1, starting_letter):
            arrangement += [i, -i]
        arrangement.append(rank + 1)
        arrangement += [starting_letter, -starting_letter]
    else:
        arrangement = [rank + 1, -(rank + 1), starting_letter]
        for i in range(-starting_letter + 1, rank + 1):
            arrangement += [i, -i]
        for i in range(1, -starting_letter):
            arrangement += [i, -i]
        arrangement.append(-starting_letter)

    regions = (tuple(arrangement),)
    assignment = tuple(range(1, rank + 1)) + (abs(starting_letter),)
    return rank + 1, regions, assignment


def _update_via_window(state: State, window: int) -> State:
    """
    Update the state when passing through a window (i.e. an edge that separates two
    distinct regions.)

    Args:
        state: The current State
        window: A valid window: a non-zero integer present in the first
                sublist whose negation is NOT also in the first sublist.

    Returns:
        The new State
    """

    # Basic set-up
    edge_count, regions, assignment = state
    next_edge   = edge_count + 1
    sign        = 1 if window > 0 else -1
    signed_next = sign * next_edge
    first       = regions[0]

    # Finds the region we're moving into
    neg_window_idx = -1
    for i, sub in enumerate(regions):
        if -window in sub:
            neg_window_idx = i
            break

    # Splits the region we're currently in into new_first and new_after_w
    w_idx       = first.index(window)
    new_first   = first[:w_idx] + (signed_next,)
    new_after_w = (window,) + first[w_idx + 1:]

    # Updates the region we're moving into into new_active
    neg_w_sub = regions[neg_window_idx]
    neg_w_idx = neg_w_sub.index(-window)
    new_active = (
        (-signed_next,)
        + neg_w_sub[neg_w_idx + 1:]
        + neg_w_sub[:neg_w_idx]
        + (-window,)
    )

    # Make the new list of lists describing the region
    new_regions = (
        (new_active, new_first, new_after_w)
        + tuple(sub for i, sub in enumerate(regions[1:], 1)
                if i != neg_window_idx)
    )
    new_assignment = assignment + (assignment[abs(window) - 1],)
    return next_edge, new_regions, new_assignment


def _update_via_endpoint(state: State, endpoint: int, abs_idx: int) -> State:
    """
    Update the state when passing through an endpoint (i.e. an edge leading to a puncture.)

    Args:
        state: The current State
        endpoint: A valid endpoint: non-zero integer such that abs(endpoint) and -abs(endpoint)
                  appear as a consecutive pair in the first sublist.
        abs_idx: The pre-computed index of abs(endpoint) in the active region.

    Returns:
        The new State
    """

    # General set-up
    edge_count, regions, assignment = state
    next_edge    = edge_count + 1
    pos_endpoint = abs(endpoint)
    first        = regions[0]

    # Names the two substrings of the boundary of the active region
    a = first[:abs_idx]
    b = first[abs_idx + 2:]

    # Splits and updates the active region.
    if endpoint > 0:
        new_active = (-next_edge,) + b + (pos_endpoint, -pos_endpoint)
        new_second = a + (next_edge,)
    else:
        new_active = (next_edge, -next_edge) + a + (pos_endpoint,)
        new_second = (-pos_endpoint,) + b

    new_regions    = (new_active, new_second) + regions[1:]
    new_assignment = assignment + (assignment[abs(endpoint) - 1],)
    return next_edge, new_regions, new_assignment


def _update_via_mirror(state: State, mirror: int, pos_idx: int, neg_idx: int) -> State:
    """
    Update the state when passing through a mirror (i.e. an edge where neither endpoint is a puncture,
    but both sides are the same region.)

    Args:
        state: The current State
        mirror: A valid mirror, i.e. a non-zero integer where both mirror and -mirror must appear in
                    the first region, but not as a consecutive pair.
        pos_idx: The pre-computed index of mirror in the active region.
        neg_idx: The pre-computed index of -mirror in the active region.

    Returns:
        The new State
    """

    # General set-up
    edge_count, regions, assignment = state
    next_edge   = edge_count + 1
    sign        = 1 if mirror > 0 else -1
    signed_next = sign * next_edge
    first       = regions[0]

    # The cases where the -mirror appears before and after mirror are basically completely
    # different. This works like the other two.
    if neg_idx < pos_idx:
        a = first[:neg_idx]
        b = first[neg_idx + 1:pos_idx]
        c = first[pos_idx + 1:]
        new_active  = (-signed_next,) + b + (signed_next,) + a + (-mirror,)
        new_second = (mirror,) + c
    else:
        a = first[:pos_idx]
        b = first[pos_idx + 1:neg_idx]
        c = first[neg_idx + 1:]
        new_active  = (-signed_next,) + c + (mirror,) + b + (-mirror,)
        new_second = a + (signed_next,)

    new_regions    = (new_active, new_second) + regions[1:]
    new_assignment = assignment + (assignment[abs(mirror) - 1],)
    return next_edge, new_regions, new_assignment


def _apply_update(state: State, edge: int) -> State:
    """
    Update the arrangement by calling the right function for a window, endpoint, or mirror.

    Args:
        state: The current State
        edge: The edge we want to pass through.

    Raises:
        ValueError: If edge is not found in the active region.

    Returns:
        The next State.
    """
    # Some set-up. Initialises everything to None because python is annoying.
    first = state[1][0]
    abs_edge = abs(edge)

    pos_abs_idx = None
    neg_abs_idx = None
    pos_sgn_idx = None
    neg_sgn_idx = None

    for i, v in enumerate(first):
        if v == abs_edge:
            pos_abs_idx = i
        elif v == -abs_edge:
            neg_abs_idx = i
        if v == edge:
            pos_sgn_idx = i
        elif v == -edge:
            neg_sgn_idx = i

    if pos_sgn_idx is not None and neg_sgn_idx is None:
        return _update_via_window(state, edge)

    if pos_abs_idx is not None and neg_abs_idx == pos_abs_idx + 1:
        return _update_via_endpoint(state, edge, pos_abs_idx)

    if pos_sgn_idx is not None and neg_sgn_idx is not None:
        return _update_via_mirror(state, edge, pos_sgn_idx, neg_sgn_idx)

    raise ValueError(f"Cannot update with edge={edge}: not in first region {first}")


def _advance_states(states: set[State], letter: int) -> set[State]:
    """
    Given a set of states and a next letter, return the set of states
    reachable by following any valid edge in each state's first region
    that matches the letter.

    Args:
        states: The set of states
        letter: The next letter

    Returns:
        The set of reachable states, possibly empty.
        Returns an empty set if no transition is possible.
    """
    # This is hopefully fairly self-explanatory?
    abs_l = abs(letter)
    l_pos = letter > 0
    next_states = set()
    for state in states:
        assignment = state[2]
        first = state[1][0]
        for edge in first:
            abs_e = edge if edge > 0 else -edge
            if assignment[abs_e - 1] == abs_l and (edge > 0) == l_pos:
                next_states.add(_apply_update(state, edge))
    return next_states


def _trie_subtree(args: tuple) -> tuple[int, int]:
    """
    Count (true_words, total_words) in the subtree of all reduced words of
    the given rank and length that start with a given prefix.

    Uses a stack (NOT algebraic) for depth-first search reasons.
    Stack entries: (depth, letter, parent_states)
      depth         -- current word length (2..length)
      letter        -- the letter being appended at this depth
      parent_states -- set[State] valid after the prefix up to depth-1

    When popped, we advance parent_states by letter to get next_states:
      - If next_states is empty: prune; add (2*rank-1)^(length-depth) to total.
      - If depth == length:      leaf; this word is True, increment both counts.
      - Otherwise:               push children (depth+1, next_letter, next_states)
                                 for all next_letters != -letter.
    Args:
        args: A tuple (rank, length, start_depth, start_letter, start_states)
            rank         -- number of punctures
            length       -- total word length being enumerated
            start_depth  -- depth of the node we're starting from (>= 2)
            start_letter -- the letter at start_depth - 1 (to know what to forbid)
            start_states -- set[State] valid after the prefix up to start_depth - 1

    Returns:
        (true_count, total_count)
    """
    # Some set-up, unpacking the argument
    rank, length, start_depth, start_letter, start_states = args
    alphabet      = list(range(-rank, 0)) + list(range(1, rank + 1))
    branch_factor = 2 * rank - 2 if IGNORE_POWERS else 2 * rank - 1
    true_count    = 0
    total_count   = 0

    # Seed the stack (next letters).
    # Push in reverse order so we process in forward alphabet order because I like that more.
    stack = [
        (start_depth, sl, start_states)
        for sl in reversed(alphabet)
        if sl != -start_letter and (sl != start_letter or not IGNORE_POWERS)
    ]

    while stack:
        depth, letter, parent_states = stack.pop()
        next_states = _advance_states(parent_states, letter)

        if not next_states:
            # Prune: every word extending this prefix is unrealisable.
            # The number of such words is branch_factor^(length-depth).
            total_count += branch_factor ** (length - depth)
            continue

        if depth == length:
            # Leaf: word is realisable.
            true_count  += 1
            total_count += 1
            continue

        for next_letter in reversed(alphabet):
            if next_letter != -letter and (next_letter != letter or not IGNORE_POWERS):
                stack.append((depth + 1, next_letter, next_states))

    return true_count, total_count


def _trie_subtree_collect(args: tuple) -> list[tuple[int, ...]]:
    """
    Collect all realisable words in a subtree, returning them as a list of tuples.
    Same traversal as _trie_subtree but tracks the current prefix in each stack
    entry and collects valid words at leaves instead of counting.

    Args:
        args: A tuple (rank, length, start_depth, start_letter, start_states, start_prefix)
            rank         -- number of punctures
            length       -- total word length being enumerated
            start_depth  -- depth of the node we're starting from (>= 2)
            start_letter -- the letter at start_depth - 1 (to know what to forbid)
            start_states -- set[State] valid after the prefix up to start_depth - 1
            start_prefix -- tuple of letters in the word so far (up to start_depth - 1)

    Returns:
        List of complete words (each a tuple of ints) that are realisable.
    """
    rank, length, start_depth, start_letter, start_states, start_prefix = args
    alphabet = list(range(-rank, 0)) + list(range(1, rank + 1))
    words = []

    stack = [
        (start_depth, sl, start_states, start_prefix)
        for sl in reversed(alphabet)
        if sl != -start_letter and (sl != start_letter or not IGNORE_POWERS)
    ]

    while stack:
        depth, letter, parent_states, prefix = stack.pop()
        next_states = _advance_states(parent_states, letter)
        current_prefix = prefix + (letter,)

        if not next_states:
            continue

        if depth == length:
            words.append(current_prefix)
            continue

        for next_letter in reversed(alphabet):
            if next_letter != -letter and (next_letter != letter or not IGNORE_POWERS):
                stack.append((depth + 1, next_letter, next_states, current_prefix))

    return words



def _check_unsigned_subword(rank: int, subword: list[int]) -> tuple[bool, list[int]]:
    """
    Check whether any signing of an unsigned subword is realisable, returning
    both the result and the longest realisable signed prefix found.

    Performs a DFS over the 2^len(subword) possible sign assignments, using
    the same trie-pruning strategy as check_subword: if _advance_states returns
    empty for some (prefix, sign choice), the entire subtree below that node is
    discarded.  Respects the IGNORE_POWERS global the same way check_subword does.

    Args:
        rank:    A positive integer, the number of punctures.
        subword: A non-empty list of *positive* integers, each with value <= rank,
                 representing the unsigned letters of the word.

    Returns:
        (True,  signed_word)   if some signing of subword is realisable,
                               where signed_word is one such signing (same length as subword).
        (False, longest_prefix) otherwise, where longest_prefix is the longest
                               signed prefix w[:k] for which some signing of
                               subword[:k] is realisable.  Always has length >= 1
                               since any single letter is realisable.

    Raises:
        TypeError:  If rank is not a positive integer, or any entry of subword
                    is not a positive integer.
        ValueError: If subword is empty, or any entry exceeds rank.
    """

    # Single-letter words are always realisable.
    if len(subword) == 1:
        return True, [subword[0]]

    # Stack entries: (pos, last_signed_letter, states, prefix)
    #   pos                -- index of the *next* unsigned letter to sign (>= 1)
    #   last_signed_letter -- the signed letter chosen at pos - 1
    #   states             -- set[State] reachable after processing subword[:pos]
    #   prefix             -- tuple of signed letters chosen so far (length == pos)
    #
    # Invariant: states is always non-empty when an entry is pushed, so
    # prefix is always a valid realisable signed subword when popped.
    stack: list[tuple[int, int, set, tuple]] = []
    for sign in (1, -1):
        signed_first = sign * subword[0]
        stack.append((1, signed_first, {_make_initial_state(rank, signed_first)}, (signed_first,)))

    best_prefix = (subword[0],)  # length 1 is always realisable

    while stack:
        pos, last_letter, states, prefix = stack.pop()

        # Every popped entry has non-empty states, so prefix is a valid reachable
        # signed subword. Update best_prefix if this is the deepest we've reached.
        if len(prefix) > len(best_prefix):
            best_prefix = prefix

        for sign in (1, -1):
            next_letter = sign * subword[pos]

            # Prune non-reduced branches.
            if next_letter == -last_letter:
                continue
            if IGNORE_POWERS and next_letter == last_letter:
                continue

            next_states = _advance_states(states, next_letter)
            if not next_states:
                continue

            next_prefix = prefix + (next_letter,)

            if pos + 1 == len(subword):
                return True, list(next_prefix)

            stack.append((pos + 1, next_letter, next_states, next_prefix))

    return False, list(best_prefix)


def _check_signed_subword(rank: int, subword: list[int]) -> tuple[bool, list[int]]:
    """
    Check whether subword is realisable.

    Args:
        rank:    A positive integer, the number of punctures.
        subword: A non-empty reduced list of non-zero integers, each with
                 abs value <= rank.

    Returns:
        True if possible_arrangements is non-empty after processing all of
        subword, False if it becomes empty at any point.
        Then the length of the largest valid prefix.

    Raises:
        TypeError:  If rank is not a positive integer, or subword is not a
                    list of non-zero integers.
        ValueError: If subword is empty, any entry has abs value > rank,
                    or subword is not reduced.
    """
    states = {_make_initial_state(rank, subword[0])}
    for s in range(1,len(subword)):
        states = _advance_states(states, subword[s])
        if not states:
            return False, subword[:s]
    return True, subword


def _find_minimal_invalid_subtree_from_second(args: tuple) -> list[tuple[int, ...]]:
    """
    Find minimal invalid words starting with 1 then a given second letter.
    args: (rank, max_length, second_letter, initial_suffix_state_sets)
        initial_suffix_state_sets: the suffix-state list after reading just (1,)
    """
    rank, max_length, second_letter, parent_ss = args
    alphabet = list(range(-rank, 0)) + list(range(1, rank + 1))
    results  = []

    # Advance the parent state-sets by second_letter.
    new_ss = []
    for i, ss in enumerate(parent_ss):
        advanced = _advance_states(ss, second_letter)
        if i > 0 and not advanced:
            return []   # proper subword (1,) is always valid, so this shouldn't fire;
                        # but guard anyway
        new_ss.append(advanced)
    # Append fresh state-set for the single-letter suffix (second_letter,)
    new_ss.append({_make_initial_state(rank, second_letter)})
    word = (1, second_letter)

    if not new_ss[0]:
        # (1, second_letter) itself is minimal invalid
        return [word]

    if len(word) >= max_length:
        return []

    # Now run the standard DFS from this starting point
    stack = [(word, new_ss)]
    while stack:
        word, suffix_state_sets = stack.pop()
        if len(word) >= max_length:
            continue
        for next_letter in reversed(alphabet):
            if next_letter == -word[-1]:
                continue
            if IGNORE_POWERS and next_letter == word[-1]:
                continue
            new_suffix_ss = []
            pruned = False
            for i, ss in enumerate(suffix_state_sets):
                advanced = _advance_states(ss, next_letter)
                if i > 0 and not advanced:
                    pruned = True
                    break
                new_suffix_ss.append(advanced)
            if pruned:
                continue
            new_suffix_ss.append({_make_initial_state(rank, next_letter)})
            new_word = word + (next_letter,)
            if not new_suffix_ss[0]:
                results.append(new_word)
            else:
                stack.append((new_word, new_suffix_ss))

    return results

#################################################################################
### Public functions
#################################################################################


def count_realisable(rank: int, length: int, prefix: list[int] | None = None) -> tuple[int, int]:
    """
    Count (true_words, total_words) over all reduced words of given rank and length
    that extend a given prefix, using trie traversal with subtree pruning.

    Args:
        rank:   The number of punctures, >= 1.
        length: The total word length. Must be >= len(prefix).
        prefix: A non-empty reduced list of ints, each with abs value <= rank.
                Defaults to [1].

    Returns:
        (true_count, total_count) where total_count is the number of reduced words
        of the given rank and length that extend the prefix.
    """
    if prefix is None:
        prefix = [1]

    # Data validation for prefix
    _validate_word(prefix, rank)
    if length < len(prefix):
        raise ValueError(f"length ({length}) must be >= len(prefix) ({len(prefix)})")

    # Generate starting state from prefix
    states = {_make_initial_state(rank, prefix[0])}
    for letter in prefix[1:]:
        states = _advance_states(states, letter)
        if not states:
            return 0, 0   # prefix itself is unrealisable

    prefix_depth = len(prefix)
    last_letter  = prefix[-1]
    alphabet     = list(range(-rank, 0)) + list(range(1, rank + 1))
    valid_next   = [
        l for l in alphabet
        if l != -last_letter and (not IGNORE_POWERS or l != last_letter)
    ]

    # Some edge cases that it's worth dealing with separately
    if length == prefix_depth:
        return 1, 1

    if length == prefix_depth + 1:
        true_count  = sum(1 for nl in valid_next if _advance_states(states, nl))
        total_count = len(valid_next)
        return true_count, total_count

    # General case
    tasks = [ (rank, length, prefix_depth + 2, nl, _advance_states(states, nl)) for nl in valid_next]

    if USE_MULTIPROCESSING:
        with Pool() as pool:
            results = pool.map(_trie_subtree, tasks)
    else:
        results = [_trie_subtree(t) for t in tasks]

    return sum(r[0] for r in results), sum(r[1] for r in results)


def collect_realisable(rank: int, length: int, filename: str, prefix: list[int] | None = None) -> int:
    """
    Write all realisable words of given rank and length that extend a given
    prefix to a CSV file, one word per row.

    Args:
        rank:     The number of punctures, >= 1.
        length:   The total word length. Must be >= len(prefix).
        filename: Path to the output CSV file.
        prefix:   A non-empty reduced list of ints, each with abs value <= rank.
                  Defaults to [1].

    Returns:
        The number of words written.
    """
    if prefix is None:
        prefix = [1]

    # Data validation
    _validate_word(prefix,rank)
    if length < len(prefix):
        raise ValueError(f"length ({length}) must be >= len(prefix) ({len(prefix)})")

    # Main loop
    states = {_make_initial_state(rank, prefix[0])}
    for letter in prefix[1:]:
        states = _advance_states(states, letter)
        if not states:
            # Prefix is unrealisable; write nothing
            open(filename, 'w').close()
            return 0

    prefix_tuple = tuple(prefix)
    prefix_depth = len(prefix)
    last_letter  = prefix[-1]
    alphabet     = list(range(-rank, 0)) + list(range(1, rank + 1))
    valid_next   = [
        l for l in alphabet
        if l != -last_letter and (not IGNORE_POWERS or l != last_letter)
    ]

    # Some more edge cases
    words = []

    if length == prefix_depth:
        words = [prefix_tuple]

    elif length == prefix_depth + 1:
        words = [prefix_tuple + (nl,) for nl in valid_next if _advance_states(states, nl)]

    else:
        tasks = [(rank, length, prefix_depth + 2, nl, next_states, prefix_tuple + (nl,))
            for nl in valid_next for next_states in (_advance_states(states, nl),) if next_states]

        if USE_MULTIPROCESSING:
            with Pool() as pool:
                results = pool.map(_trie_subtree_collect, tasks)
        else:
            results = [_trie_subtree_collect(t) for t in tasks]

        words = [word for word_list in results for word in word_list]

    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        for word in words:
            writer.writerow(word)

    return len(words)


def check_subword(rank: int, subword: list[int]) -> tuple[bool, list[int]]:
    if not isinstance(rank, int) or rank <= 0:
        raise TypeError(f"rank must be a positive integer, got {rank!r}")
    _validate_word(subword, rank)

    if IGNORE_SIGNS:
        return _check_unsigned_subword(rank, subword)
    else:
        return _check_signed_subword(rank, subword)

def find_minimal_invalid(rank: int, max_length: int) -> list[tuple[int, ...]]:
    """
    Find all minimal invalid words of given rank with length <= max_length,
    up to cyclic permutation and reflection (i.e. canonical representatives
    starting with 1 only).
    """
    if not isinstance(rank, int) or rank < 1:
        raise TypeError(f"rank must be a positive integer, got {rank!r}")
    if not isinstance(max_length, int) or max_length < 1:
        raise TypeError(f"max_length must be a positive integer, got {max_length!r}")

    alphabet     = list(range(-rank, 0)) + list(range(1, rank + 1))
    initial_ss   = [{_make_initial_state(rank, 1)}]

    # Handle the length-1 case: (1,) itself is trivially valid, nothing to do.
    if max_length == 1:
        return []

    # Split on the second letter for multiprocessing, exactly as count_realisable does.
    # (Second letter can be anything except -1, i.e. anything that keeps the word reduced.)
    valid_second = [l for l in alphabet if l != -1 and (not IGNORE_POWERS or l != 1)]
    tasks = [(rank, max_length, l, initial_ss) for l in valid_second]

    if USE_MULTIPROCESSING:
        with Pool() as pool:
            results = pool.map(_find_minimal_invalid_subtree_from_second, tasks)
    else:
        results = [_find_minimal_invalid_subtree_from_second(t) for t in tasks]

    all_words = [word for sublist in results for word in sublist]
    return sorted(all_words, key=lambda w: (len(w), w))


def load_alicja_sequences(filepath: str) -> list[list[int]]:
    """
    Load a .txt file containing '*'-separated letter sequences, one per line,
    each terminated by a semicolon. Letters may be followed by '^(-1)' to
    indicate a negative integer. Duplicate sublists are removed, preserving
    first-occurrence order.

    Args:
        filepath: Path to the .txt file.

    Returns:
        A list of unique lists of integers, one per non-empty line.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If any token is not a recognised letter (a-e) with an
                    optional '^(-1)' suffix.
    """
    token_re = re.compile(r'^([a-e])(\^\(-1\))?$')

    seen = set()
    results = []
    LETTER_TO_NUM = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5}

    with open(filepath, encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip().rstrip(';').strip()
            if not line:
                continue
            converted = []
            for token in line.split('*'):
                token = token.strip()
                m = token_re.match(token)
                if not m:
                    raise ValueError(
                        f"Unexpected token {token!r} at line {line_num} — "
                        f"expected a letter a-e with optional '^(-1)' suffix"
                    )
                num = LETTER_TO_NUM[m.group(1)]
                if m.group(2):
                    num = -num
                converted.append(num)
            key = tuple(converted)
            if key not in seen:
                seen.add(key)
                results.append(converted)

    return results


if __name__ == "__main__":

    rank   = 5
    length = 6
    prefix = [-1,2]

    branch_factor = (rank * 2 - 2) if IGNORE_POWERS else (rank * 2 - 1)
    expected = branch_factor ** (length - len(prefix))

    n_cores = cpu_count()
    print(f"Rank={rank}, Length={length}, Prefix={prefix}")
    print(f"Total reduced words : {expected:,}")
    print(f"Multiprocessing     : {'ON (' + str(n_cores) + ' cores)' if USE_MULTIPROCESSING else 'OFF'}")
    print()

    if PRODUCE_OUTPUT:
        t_start = time.perf_counter()
        true_count = collect_realisable(rank, length,"out.csv", prefix)
        elapsed = time.perf_counter() - t_start

    else:
        t_start = time.perf_counter()
        true_count, total_count = count_realisable(rank, length, prefix)
        elapsed = time.perf_counter() - t_start

        # total_count should equal expected; sanity check
        assert total_count == expected, (
            f"Word count mismatch: got {total_count}, expected {expected}"
        )

    print("═" * 60)
    print(f"  Total words     : {expected:,}")
    print(f"  True count      : {true_count:,}")
    print(f"  False count     : {expected - true_count:,}")
    print(f"  Proportion True : 10^{log(true_count / expected):.3f}")
    print(f"  Total time      : {elapsed:.3f}s")
    print("═" * 60)

