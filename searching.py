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

Signs and permutations
----------------------
By default neither the signs of the input nor its labelling are taken literally.  Sign
choice is fused into the same sweep as the choice of crossing: at an unpinned letter the
frontier advances by both +l and -l and the two results are merged, which gives exactly
"every configuration reachable under every sign assignment" for the price of one sweep.
`can_exist_witness` then recovers an assignment by pinning one letter at a time.

The permutation loop sits outside the sweep.  Permuting only the symbols actually
present is complete: drawability depends solely on the relative order of the punctures
used, so relabelling onto a wider or gappier subset of {1..n} can never reach a
configuration a permutation misses.

Scope
-----
The answer is necessary but not sufficient for membership in the orbit Q = B_n . x_1:
`can_exist` reports "drawable as an embedded arc", not "is a subword of a simple loop".
A True result means "not ruled out".
"""

import itertools

from regions import (
    make_state,
    forward,
    seg_possibilities_given_gen,
)


# ------------------------------------------------------------------ frontier steps

def _advance(states: set, letter: int) -> set:
    """
    Advance a frontier of states by one signed letter.

    Every state branches over every face of the relevant generator line that bounds its
    end-region.  States with no such face contribute nothing, so pruning is automatic.
    """
    return {forward(s, seg) for s in states for seg in seg_possibilities_given_gen(s, letter)}


def _sweep(n: int, word: list[int], signs: list[int]) -> set:
    """
    Every configuration reachable by drawing word in a disk with n punctures.

    signs[j] pins the sign of word[j] to +1 or -1; 0 leaves it free, in which case both
    signs are explored and their configurations merged.  Returns the empty set as soon
    as the word becomes undrawable.
    """
    states = {make_state(n)}
    for letter, pinned in zip(word, signs):
        magnitude = abs(letter)
        options = (magnitude, -magnitude) if pinned == 0 else (pinned * magnitude,)
        states = set().union(*(_advance(states, option) for option in options))
        if not states:
            return set()
    return states


def _recover_signs(n: int, word: list[int]) -> list[int] | None:
    """
    Pin one sign at a time, keeping the word drawable.  Returns None if no assignment
    makes it drawable.

    Greedy pinning is exact because a merged sweep is the union over every completion of
    the pinned prefix: if it leaves a live frontier then some completion of that prefix
    is drawable, so a sign can always be committed to without looking ahead.  Costs at
    most 2 * len(word) sweeps, against the 2^len(word) of enumerating sign paths.
    """
    signs = [0] * len(word)
    for j in range(len(word)):
        for sign in (1, -1):
            signs[j] = sign
            if _sweep(n, word, signs):
                break
            signs[j] = 0
        else:
            return None
    return signs


# ------------------------------------------------------------------ validation

def _validate_word(word: list[int], rank: int | None = None,
                   check_for_squares: bool = True) -> None:
    """
    Check that word is a reduced word over the generators x_1 ... x_rank.

    Letters are non-zero integers, x_j written as j and its inverse as -j.  rank=None
    checks the shape of the word without imposing an upper bound on its symbols.

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
        if rank is not None and abs(s) > rank:
            raise ValueError(f"word[{i}] has abs value {abs(s)} > rank {rank}")
    for i in range(len(word) - 1):
        if word[i] == -word[i + 1]:
            raise ValueError(f"word is not reduced at positions {i}, {i + 1}")
        if check_for_squares and word[i] == word[i + 1]:
            raise ValueError(f"word has repeated letter at positions {i}, {i + 1}")


def _resolve_rank(word: list[int], n: int | None) -> int:
    """
    Validate word and settle the rank of the disk to draw it in.

    n=None asks for the smallest rank that admits the word, max |letter|.  Any larger
    rank gives the same answer -- extra punctures are neither a help nor a hindrance,
    since an arc can always pass beneath an unused puncture without recording a letter
    -- so the default is a free choice, not a guess.
    """
    _validate_word(word, n)
    return max(abs(x) for x in word) if n is None else n


# ------------------------------------------------------------------ signs and symbols

def _sign_spec(word: list[int], respect_signs: bool) -> list[int]:
    """
    Build the `signs` argument of `_sweep` for a word.

    With respect_signs the given signs are pinned; otherwise every position is left
    free (0) for the sweep to explore.
    """
    if respect_signs:
        return [1 if x > 0 else -1 for x in word]
    return [0] * len(word)


def _relabellings(word: list[int], permute: bool):
    """Yield (mapping, relabelled_word) for each permutation of the symbols present."""
    symbols = sorted({abs(x) for x in word})
    perms = itertools.permutations(symbols) if permute else (tuple(symbols),)
    for perm in perms:
        mapping = dict(zip(symbols, perm))
        yield mapping, [mapping[abs(x)] * (1 if x > 0 else -1) for x in word]


# ------------------------------------------------------------------ public API

def can_exist(word: list[int], n: int | None = None,
              permute: bool = True, respect_signs: bool = False) -> bool:
    """
    True if word can be drawn as an embedded arc in a disk with n punctures.

    n              punctures in the disk; None takes the smallest rank admitting word
    permute        try every permutation of the symbols present
    respect_signs  take the given signs literally instead of searching over signs

    Under the defaults the input is read as an unsigned word over unlabelled punctures:
    only the magnitudes matter, and both the sign of each letter and the labelling are
    free.  Permuting costs (number of symbols)! sweeps, so pass permute=False when the
    labelling is meant as given.

    >>> can_exist([1, 2, 1, 3], permute=False, respect_signs=True)   # exactly as written
    False
    >>> can_exist([1, 2, 1, 3], permute=False)                       # signs free
    True
    >>> can_exist([1, 2, 1, 3, 2, 3])                                # signs and labels free
    False
    """
    n = _resolve_rank(word, n)
    for _, relabelled in _relabellings(word, permute):
        if _sweep(n, relabelled, _sign_spec(relabelled, respect_signs)):
            return True
    return False


def can_exist_witness(word: list[int], n: int | None = None,
                      permute: bool = True, respect_signs: bool = False) -> dict | None:
    """
    A witness that word can be drawn, or None if it cannot.  Flags are as `can_exist`.

    Returns {"permutation": {old_symbol: new_symbol, ...},
             "signs":       signed_word}

    where "signs" holds the word as actually drawn -- already relabelled by the
    permutation, with a sign on every letter -- so it can be fed straight back in with
    permute=False, respect_signs=True to replay the drawing.

    >>> can_exist_witness([1, 2, 1, 3], permute=False)
    {'permutation': {1: 1, 2: 2, 3: 3}, 'signs': [1, 2, -1, 3]}
    """
    n = _resolve_rank(word, n)
    for mapping, relabelled in _relabellings(word, permute):
        if respect_signs:
            signs = _sign_spec(relabelled, True)
            if not _sweep(n, relabelled, signs):
                continue
        else:
            signs = _recover_signs(n, relabelled)
            if signs is None:
                continue
        return {
            "permutation": mapping,
            "signs": [sign * abs(x) for sign, x in zip(signs, relabelled)],
        }
    return None
