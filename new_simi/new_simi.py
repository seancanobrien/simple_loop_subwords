"""
computing_project_functional.py

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

from regions_functional import State, make_state, forward, seg_possibilities_given_gen

### GLOBAL VARIABLES
USE_MULTIPROCESSING = True  # Do we use multiprocessing for finding all valid/invalid subwords?
IGNORE_POWERS = True        # Do we enforce square-free?
PRODUCE_OUTPUT = True       # Do we save the output to a csv file?
IGNORE_SIGNS = False        # Do we check unsigned words?


#################################################################################
### Private functions
#################################################################################

def _validate_word(word: list[int], rank: int) -> None:
    """
    Validates that a word is a valid reduced word of given rank.

    Raises:
            TypeError: If the word contains something other than a non-zero integer
            ValueError: If there is another formatting issue.
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


def _advance_states(states: set[State], letter: int) -> set[State]:
    """
    Given a set of states and a next letter, return all states reachable by
    crossing any segment in each state's end-region that contributes that letter.

    Returns an empty set if no transition is possible.
    """
    next_states = set()
    for state in states:
        for seg in seg_possibilities_given_gen(state, letter):
            next_states.add(forward(state, seg))
    return next_states


def _trie_subtree_count(args: tuple) -> tuple[int, int]:
    """
    Count (true_words, total_words) in the subtree of all reduced words of
    the given rank and length that start with a given prefix.

    Uses a stack for depth-first search.
    Stack entries: (depth, letter, parent_states)
      depth         -- current word length
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
    rank, length, start_depth, start_letter, start_states = args
    alphabet      = list(range(-rank, 0)) + list(range(1, rank + 1))
    branch_factor = 2 * rank - 2 if IGNORE_POWERS else 2 * rank - 1
    true_count    = 0
    total_count   = 0

    stack = [(start_depth, sl, start_states) for sl in reversed(alphabet)
        if sl != -start_letter and (sl != start_letter or not IGNORE_POWERS)]

    while stack:
        depth, letter, parent_states = stack.pop()
        next_states = _advance_states(parent_states, letter)

        if not next_states:
            total_count += branch_factor ** (length - depth)
            continue

        if depth == length:
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
    Same traversal as _trie_subtree_count but tracks the current prefix in each
    stack entry and collects valid words at leaves instead of counting.

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

    Stack entries: (pos, last_signed_letter, states, prefix)
       pos                -- index of the next unsigned letter to sign (>= 1)
       last_signed_letter -- the signed letter chosen at pos - 1
       states             -- set[State] reachable after processing subword[:pos]
       prefix             -- tuple of signed letters chosen so far (length == pos)

    Returns:
        (True,  signed_word)    if some signing of subword is realisable.
        (False, longest_prefix) otherwise; longest_prefix always has length >= 1.
    """
    if len(subword) == 1:
        return True, [subword[0]]

    initial     = make_state(rank)
    best_prefix = (subword[0],)
    stack       = []
    for sign in (1, -1):
        signed_first = sign * subword[0]
        stack.append((1, signed_first, _advance_states({initial}, signed_first), (signed_first,)))

    while stack:
        pos, last_letter, states, prefix = stack.pop()
        if len(prefix) > len(best_prefix):
            best_prefix = prefix

        for sign in (1, -1):
            next_letter = sign * subword[pos]
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
    Check whether subword is realisable, returning the result and longest valid prefix.

    Returns:
        (True,  subword)  if realisable.
        (False, prefix)   where prefix is the longest realisable prefix found.
    """
    states = {make_state(rank)}
    for s, letter in enumerate(subword):
        states = _advance_states(states, letter)
        if not states:
            return False, subword[:s]
    return True, subword


def _find_minimal_invalid_subtree_from_second(args: tuple) -> list[tuple[int, ...]]:
    """
    Find minimal invalid words starting with 1 then a given second letter.

    Args:
        args: a tuple (rank, max_length, second_letter, initial_suffix_state_sets)
            initial_suffix_state_sets: the suffix-state list after reading just (1,)
    """
    rank, max_length, second_letter, parent_ss = args
    alphabet = list(range(-rank, 0)) + list(range(1, rank + 1))
    results  = []

    new_ss = []
    for i, ss in enumerate(parent_ss):
        advanced = _advance_states(ss, second_letter)
        if i > 0 and not advanced:
            return []
        new_ss.append(advanced)
    new_ss.append(_advance_states({make_state(rank)}, second_letter))
    word = (1, second_letter)

    if not new_ss[0]:
        return [word]

    if len(word) >= max_length:
        return []

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
            new_suffix_ss.append(_advance_states({make_state(rank)}, next_letter))
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

    _validate_word(prefix, rank)
    if length < len(prefix):
        raise ValueError(f"length ({length}) must be >= len(prefix) ({len(prefix)})")

    states = {make_state(rank)}
    for letter in prefix:
        states = _advance_states(states, letter)
        if not states:
            return 0, 0

    prefix_depth = len(prefix)
    last_letter  = prefix[-1]
    alphabet     = list(range(-rank, 0)) + list(range(1, rank + 1))
    valid_next   = [
        l for l in alphabet
        if l != -last_letter and (not IGNORE_POWERS or l != last_letter)
    ]

    if length == prefix_depth:
        return 1, 1

    if length == prefix_depth + 1:
        true_count  = sum(1 for nl in valid_next if _advance_states(states, nl))
        total_count = len(valid_next)
        return true_count, total_count

    tasks = [(rank, length, prefix_depth + 2, nl, _advance_states(states, nl)) for nl in valid_next]

    if USE_MULTIPROCESSING:
        with Pool() as pool:
            results = pool.map(_trie_subtree_count, tasks)
    else:
        results = [_trie_subtree_count(t) for t in tasks]

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

    _validate_word(prefix, rank)
    if length < len(prefix):
        raise ValueError(f"length ({length}) must be >= len(prefix) ({len(prefix)})")

    states = {make_state(rank)}
    for letter in prefix:
        states = _advance_states(states, letter)
        if not states:
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


def count_minimal_invalid(rank: int, max_length: int) -> int:
    """
    Count all minimal invalid words of given rank with length <= max_length,
    up to cyclic permutation and reflection (i.e. canonical representatives
    starting with 1 only).

    Raises:
        TypeError if rank or max_length aren't positive integers.

    Returns:
        The number of minimal invalid words found.
    """
    if not isinstance(rank, int) or rank < 1:
        raise TypeError(f"rank must be a positive integer, got {rank!r}")
    if not isinstance(max_length, int) or max_length < 1:
        raise TypeError(f"max_length must be a positive integer, got {max_length!r}")

    if max_length == 1:
        return 0

    alphabet     = list(range(-rank, 0)) + list(range(1, rank + 1))
    initial_ss   = [_advance_states({make_state(rank)}, 1)]
    valid_second = [l for l in alphabet if l != -1 and (not IGNORE_POWERS or l != 1)]
    tasks        = [(rank, max_length, l, initial_ss) for l in valid_second]

    if USE_MULTIPROCESSING:
        with Pool() as pool:
            results = pool.map(_find_minimal_invalid_subtree_from_second, tasks)
    else:
        results = [_find_minimal_invalid_subtree_from_second(t) for t in tasks]

    return sum(len(sublist) for sublist in results)


def collect_minimal_invalid(rank: int, max_length: int, filename: str) -> int:
    """
    Find all minimal invalid words of given rank with length <= max_length,
    up to cyclic permutation and reflection (i.e. canonical representatives
    starting with 1 only). Then write them to a CSV file (one word per row),
    and return the count.

    Raises:
        TypeError if rank or max_length aren't positive integers.

    Returns:
        The number of words written.
    """
    if not isinstance(rank, int) or rank < 1:
        raise TypeError(f"rank must be a positive integer, got {rank!r}")
    if not isinstance(max_length, int) or max_length < 1:
        raise TypeError(f"max_length must be a positive integer, got {max_length!r}")

    if max_length == 1:
        open(filename, 'w').close()
        return 0

    alphabet     = list(range(-rank, 0)) + list(range(1, rank + 1))
    initial_ss   = [_advance_states({make_state(rank)}, 1)]
    valid_second = [l for l in alphabet if l != -1 and (not IGNORE_POWERS or l != 1)]
    tasks        = [(rank, max_length, l, initial_ss) for l in valid_second]

    if USE_MULTIPROCESSING:
        with Pool() as pool:
            results = pool.map(_find_minimal_invalid_subtree_from_second, tasks)
    else:
        results = [_find_minimal_invalid_subtree_from_second(t) for t in tasks]

    all_words = sorted((word for sublist in results for word in sublist),
                       key=lambda w: (len(w), w))
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        for word in all_words:
            writer.writerow(word)
    return len(all_words)


def load_alicja_sequences(filepath: str) -> list[list[int]]:
    """
    Reads a file formatted like Alicja's, and returns a list in the expected format.

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
    prefix = [-1, 2]

    branch_factor = (rank * 2 - 2) if IGNORE_POWERS else (rank * 2 - 1)
    expected = branch_factor ** (length - len(prefix))

    n_cores = cpu_count()
    print(f"Rank={rank}, Length={length}, Prefix={prefix}")
    print(f"Total reduced words : {expected:,}")
    print(f"Multiprocessing     : {'ON (' + str(n_cores) + ' cores)' if USE_MULTIPROCESSING else 'OFF'}")
    print()

    if PRODUCE_OUTPUT:
        t_start = time.perf_counter()
        true_count = collect_realisable(rank, length, "out.csv", prefix)
        elapsed = time.perf_counter() - t_start

    else:
        t_start = time.perf_counter()
        true_count, total_count = count_realisable(rank, length, prefix)
        elapsed = time.perf_counter() - t_start

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
