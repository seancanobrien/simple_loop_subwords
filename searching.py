import itertools
from regions import (
    make_state,
    forward,
    seg_possibilities_given_gen
)

"""
RegionsManager: same API as before, but DFS now copies cheap tuples
instead of deepcopy-ing class instances.
"""

def _validate_word(word: list[int], rank: int) -> None:
    if not isinstance(word, list) or not word:
        raise ValueError("word must be a non-empty list")
    for i, s in enumerate(word):
        if not isinstance(s, int) or s == 0:
            raise TypeError(f"word[{i}] must be a non-zero integer, got {s!r}")
        if abs(s) > rank:
            raise ValueError(f"word[{i}] has abs value {abs(s)} > rank {rank}")
    for i in range(len(word) - 1):
        if word[i] == -word[i + 1]:
            raise ValueError(f"word is not reduced at positions {i}, {i + 1}")
        if IGNORE_POWERS and word[i] == word[i + 1]:
            raise ValueError(f"word has repeated letter at positions {i}, {i + 1}")

# ------------------------------------------------
# evaluate (signed word)
# ------------------------------------------------

def evaluate(n: int, word: list[int]) -> bool:
        _validate_word(word, n)
        initial = make_state(n)
        return _dfs(initial, word, 0)

def _dfs(state, word: list[int], idx: int) -> bool:
        if idx == len(word):
            return True
        letter = word[idx]
        options = seg_possibilities_given_gen(state, letter)
        if not options:
            return False
        for seg in options:
            new_state = forward(state, seg)
            if _dfs(new_state, word, idx + 1):
                return True
        return False

# ------------------------------------------------
# evaluate_unsigned
# ------------------------------------------------

def valid_assignment_of_signs(n: int, word: list[int]) -> list[int] | None:
    _validate_word(word, n)
    success, assignment = _dfs_unsigned(make_state(n), word, 0, [])
    return assignment if success else None

def _dfs_unsigned(state, word: list[int], idx: int, path: list[int]):
    if idx == len(word):
        return True, path
    letter = word[idx]
    for signed_letter in (letter, -letter):
        options = seg_possibilities_given_gen(state, signed_letter)
        if not options:
            continue
        for seg in options:
            new_state = forward(state, seg)
            success, result_path = _dfs_unsigned(
                new_state, word, idx + 1, path + [signed_letter]
            )
            if success:
                return True, result_path
    return False, None

# ------------------------------------------------
# evaluate_all_perms_and_signs
# ------------------------------------------------

def valid_permutation_and_assignment_of_signs(n: int, word: list[int]) -> list[int] | None:
    _validate_word(word, n)
    symbols = sorted(set(word))
    for perm in itertools.permutations(symbols):
        mapping = dict(zip(symbols, perm))
        relabelled = [mapping[x] for x in word]
        success, assignment = _dfs_unsigned(
            make_state(n), relabelled, 0, []
        )
        if success:
            return assignment
    return None

# ------------------------------------------------
# Simi function implementations using BFS search
# ------------------------------------------------

import csv
import re
import time
from math import log10 as log

USE_MULTIPROCESSING = True  # Do we use multiprocessing for finding all valid/invalid subwords?
IGNORE_POWERS = True        # Do we enforce square-free?
PRODUCE_OUTPUT = True       # Do we save the output to a csv file?
IGNORE_SIGNS = False        # Do we check unsigned words?

# Advance a set of states according to next letter
# pruning is automatic
def _advance(states: set, letter: int) -> set:
    """Advance a set of states by one letter; returns all reachable next states."""
    return {forward(s, seg) for s in states for seg in seg_possibilities_given_gen(s, letter)}


def _realisable_words(states: set, prefix: tuple, length: int, rank: int):
    """Yield all realisable words of given length extending prefix from states."""
    if len(prefix) == length:
        yield prefix
        return
    last = prefix[-1]
    for letter in range(-rank, rank + 1):
        if letter == 0 or letter == -last or (IGNORE_POWERS and letter == last):
            continue
        next_states = _advance(states, letter)
        if next_states:
            yield from _realisable_words(next_states, prefix + (letter,), length, rank)


def count_realisable(rank: int, length: int, prefix: list[int] | None = None) -> tuple[int, int]:
    """
    Count (true_words, total_words) over all reduced words of given rank and length
    that extend a given prefix.
    """
    if prefix is None:
        prefix = [1]
    _validate_word(prefix, rank)
    if length < len(prefix):
        raise ValueError(f"length ({length}) must be >= len(prefix) ({len(prefix)})")

    states = {make_state(rank)}
    for letter in prefix:
        states = _advance(states, letter)
        if not states:
            return 0, 0

    branch = 2 * rank - (2 if IGNORE_POWERS else 1)
    total  = branch ** (length - len(prefix))
    true_count = sum(1 for _ in _realisable_words(states, tuple(prefix), length, rank))
    return true_count, total


def collect_realisable(rank: int, length: int, filename: str, prefix: list[int] | None = None) -> int:
    """Write all realisable words of given rank and length to a CSV file. Returns count."""
    if prefix is None:
        prefix = [1]
    _validate_word(prefix, rank)
    if length < len(prefix):
        raise ValueError(f"length ({length}) must be >= len(prefix) ({len(prefix)})")

    states = {make_state(rank)}
    for letter in prefix:
        states = _advance(states, letter)
        if not states:
            open(filename, 'w').close()
            return 0

    words = list(_realisable_words(states, tuple(prefix), length, rank))
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        for word in words:
            writer.writerow(word)
    return len(words)


def _minimal_invalid_words(suffix_sets: list, word: tuple, max_length: int, rank: int):
    """
    Yield minimally invalid words. suffix_sets[k] = states after reading word[k:]
    from make_state(rank). A word is minimally invalid when suffix_sets[0] is empty
    and all suffix_sets[k > 0] are non-empty.
    """
    if not suffix_sets[0]:
        yield word
        return
    if len(word) >= max_length:
        return
    last = word[-1]
    for letter in range(-rank, rank + 1):
        if letter == 0 or letter == -last or (IGNORE_POWERS and letter == last):
            continue
        new_sets = []
        for k, states in enumerate(suffix_sets):
            ns = _advance(states, letter)
            if k > 0 and not ns:
                new_sets = None
                break
            new_sets.append(ns)
        if new_sets is None:
            continue
        new_sets.append(_advance({make_state(rank)}, letter))
        yield from _minimal_invalid_words(new_sets, word + (letter,), max_length, rank)


def count_minimal_invalid(rank: int, max_length: int) -> int:
    """
    Count minimal invalid words of given rank with length <= max_length,
    starting with 1 (canonical representatives up to cyclic permutation and reflection).
    """
    if not isinstance(rank, int) or rank < 1:
        raise TypeError(f"rank must be a positive integer, got {rank!r}")
    if not isinstance(max_length, int) or max_length < 1:
        raise TypeError(f"max_length must be a positive integer, got {max_length!r}")
    if max_length == 1:
        return 0
    return sum(1 for _ in _minimal_invalid_words(
        [_advance({make_state(rank)}, 1)], (1,), max_length, rank
    ))


def collect_minimal_invalid(rank: int, max_length: int, filename: str) -> int:
    """
    Write minimal invalid words of given rank with length <= max_length to a CSV file.
    Returns count.
    """
    if not isinstance(rank, int) or rank < 1:
        raise TypeError(f"rank must be a positive integer, got {rank!r}")
    if not isinstance(max_length, int) or max_length < 1:
        raise TypeError(f"max_length must be a positive integer, got {max_length!r}")
    if max_length == 1:
        open(filename, 'w').close()
        return 0
    words = sorted(
        _minimal_invalid_words([_advance({make_state(rank)}, 1)], (1,), max_length, rank),
        key=lambda w: (len(w), w),
    )
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        for word in words:
            writer.writerow(word)
    return len(words)


def load_alicja_sequences(filepath: str) -> list[list[int]]:
    """
    Reads a file formatted like Alicja's, and returns a list in the expected format.
    """
    token_re      = re.compile(r'^([a-e])(\^\(-1\))?$')
    LETTER_TO_NUM = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5}
    seen, results = set(), []
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
                converted.append(-num if m.group(2) else num)
            key = tuple(converted)
            if key not in seen:
                seen.add(key)
                results.append(converted)
    return results


if __name__ == "__main__":
    rank   = 5
    length = 6
    prefix = [-1, 2]

    branch   = 2 * rank - (2 if IGNORE_POWERS else 1)
    expected = branch ** (length - len(prefix))

    print(f"Rank={rank}, Length={length}, Prefix={prefix}")
    print(f"Total reduced words : {expected:,}")
    print()

    t_start    = time.perf_counter()
    true_count = collect_realisable(rank, length, "out.csv", prefix)
    elapsed    = time.perf_counter() - t_start

    print("═" * 60)
    print(f"  Total words     : {expected:,}")
    print(f"  True count      : {true_count:,}")
    print(f"  False count     : {expected - true_count:,}")
    print(f"  Proportion True : 10^{log(true_count / expected):.3f}")
    print(f"  Total time      : {elapsed:.3f}s")
    print("═" * 60)
