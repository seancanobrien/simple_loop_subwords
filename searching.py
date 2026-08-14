"""
Breadth-first search over the drawings of a single word.

`regions.py` supplies the state and the one-crossing update; this module wraps them in
a search.  A letter x_j^{+/-1} can usually be contributed by crossing any one of several
faces of generator line j, so a drawing attempt is not a single path but a tree.

The frontier
------------
Rather than backtrack through that tree, the search carries the whole frontier of live
drawings and advances it one letter at a time:

    states  ->  { forward(s, seg) : s in states, seg admissible for the letter }

Pruning is automatic.  A state with no admissible face contributes nothing to the next
frontier, so dead drawings drop out on their own; an empty frontier means no drawing
survives, and the word is not drawable.  Because State is a hashable NamedTuple, the
set also merges drawings that reach identical configurations by different choices.

That merge is *structural*, not geometric: two states describing the same picture with
different segment IDs, or with a non-end region written at a different rotation, will
not merge.  Anchoring the end-region (see `regions.py`) is what makes the common case
merge.

Scope
-----
The answer is necessary but not sufficient for membership in the orbit Q = B_n . x_1:
`evaluate` reports "drawable as an embedded arc", not "is a subword of a simple loop".
A True result means "not ruled out".
"""

import itertools

from regions import (
    make_state,
    forward,
    seg_possibilities_given_gen,
)


# ------------------------------------------------------------------ frontier step

def _advance(states: set, letter: int) -> set:
    """
    Advance a frontier of states by one signed letter.

    Every state branches over every face of the relevant generator line that bounds its
    end-region.  States with no such face contribute nothing, so pruning is automatic.
    """
    return {forward(s, seg) for s in states for seg in seg_possibilities_given_gen(s, letter)}


# ------------------------------------------------------------------ validation

def _validate_word(word: list[int], rank: int, check_for_squares: bool = True) -> None:
    """
    Check that word is a reduced word over the generators x_1 ... x_rank.

    Letters are non-zero integers, x_j written as j and its inverse as -j.

    Squares are rejected by default.  The algorithm will happily draw x_j x_j -- an
    ever-growing spiral around a single puncture -- but such words do not arise as
    subwords of the reduced words of interest, so they are excluded rather than handled.
    Pass check_for_squares=False to admit them anyway.

    Raises:
        TypeError:  a letter is not a non-zero integer.
        ValueError: the word is empty, has a letter outside +/-1 ... +/-rank, is not
                    reduced, or (unless allowed) contains a square.
    """
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
        if check_for_squares and word[i] == word[i + 1]:
            raise ValueError(f"word has repeated letter at positions {i}, {i + 1}")


# ------------------------------------------------------------------ public API

def evaluate(n: int, word: list[int]) -> bool:
    """
    True if word can be drawn as an embedded arc in a disk with n punctures.

    n must be at least max |letter|, but may be larger: extra punctures are neither a
    help nor a hindrance, since an arc can always pass beneath an unused puncture
    without recording a letter.

    >>> evaluate(5, [1, 2, -1])
    True
    >>> evaluate(5, [1, 2, -1, -3, 2, 3])
    False
    """
    _validate_word(word, n)
    states = {make_state(n)}
    for letter in word:
        states = _advance(states, letter)
        if not states:
            return False
    return True


def valid_assignment_of_signs(n: int, word: list[int]) -> list[int] | None:
    """
    A choice of sign per letter making word drawable, or None if there is none.

    The input is read as an unsigned word: only the magnitudes matter, and each position
    is free to become x_j or x_j^-1.

    Unlike `evaluate`, the frontier here keeps one entry per sign path rather than
    merging across them, because the answer has to name the assignment it found.  That
    makes it far more expensive -- the frontier can grow like 2^len(word).

    >>> evaluate(5, [1, 2, 1, 3])              # as given, all positive
    False
    >>> valid_assignment_of_signs(5, [1, 2, 1, 3])
    [1, 2, -1, 3]
    >>> valid_assignment_of_signs(5, [1, 2, 1, 3, 2, 3]) is None
    True
    """
    _validate_word(word, n)
    frontier = [({make_state(n)}, [])]
    for letter in word:
        next_frontier = []
        for states, path in frontier:
            for signed_letter in (letter, -letter):
                next_states = _advance(states, signed_letter)
                if next_states:
                    next_frontier.append((next_states, path + [signed_letter]))
        if not next_frontier:
            return None
        frontier = next_frontier
    return frontier[0][1] if frontier else None


def valid_permutation_and_assignment_of_signs(n: int, word: list[int]) -> list[int] | None:
    """
    As `valid_assignment_of_signs`, but also trying every relabelling of the symbols.

    Permuting only the symbols actually present is complete: drawability depends solely
    on the relative order of the punctures used, so relabelling onto a wider or gappier
    subset of {1..n} can never reach a configuration a permutation misses.

    The permutation is applied to `sorted(set(word))`, a set of *signed* letters, so this
    is intended for unsigned (all-positive) input; on a mixed-sign word, 1 and -1 would
    be permuted as if they were unrelated symbols.

    >>> valid_permutation_and_assignment_of_signs(5, [1, 2, 1, 3, 2, 3]) is None
    True
    """
    _validate_word(word, n)
    symbols = sorted(set(word))
    for perm in itertools.permutations(symbols):
        mapping = dict(zip(symbols, perm))
        relabelled = [mapping[x] for x in word]
        assignment = valid_assignment_of_signs(n, relabelled)
        if assignment is not None:
            return assignment
    return None
