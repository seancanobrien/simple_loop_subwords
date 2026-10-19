"""
Co-existence of several subwords in one punctured disk.

The question
-----------
`searching.can_exist` asks whether a single word can be drawn as an embedded arc.  This
module asks whether a *family* of words can be drawn simultaneously, as pairwise
disjoint embedded arcs in one disk.

If w_1, ..., w_k all occur as subwords of a single simple loop, then their drawn arcs
are disjoint sub-arcs of one embedded loop.  So "cannot co-exist" rules out the family
from appearing together in any element of the orbit Q, which is the point of the
exercise.  The converse does not hold: this test says nothing about whether the arcs
can be joined up into a single closed loop, so co-existence is necessary but not
sufficient.

How it works
------------
Draw the words one after another into the same configuration.  After w_1 is drawn, the
disk has been cut into regions; w_2 then starts a *fresh* arc at a free interior point
of any one of them and proceeds normally.  Because the region machinery only permits
crossings through faces bounding the current region, an arc drawn this way is
automatically disjoint from everything already drawn.

Starting a fresh arc is `regions.forward_new_arc`: the arc's start point is free, so the
first cut is a slit and does not disconnect its region.  Every region is a candidate
starting region, so that step branches over all of them.

A word may also start or end with 0, putting that end of its arc on the boundary of the
disk.  The boundary is generator 0 to `regions.py`, so this needs no special step: a
leading 0 starts the arc on any boundary face of any region, and a trailing 0 ends it on
a boundary face of the end-region.  Any number of words may touch the boundary.

Signs and permutations
----------------------
Sign choice is fused into the same breadth-first sweep as the choice of crossing: at
each unsigned letter the frontier advances by both +l and -l and the results are merged.
That gives exactly "all configurations reachable under all valid sign assignments" while
deduplicating across assignments, which is what makes passing region configurations from
one word to the next cheap.

The permutation loop sits outside everything, and one permutation is applied to all
words at once -- they share a disk, so their labellings cannot be chosen independently.
Permuting the symbols actually present is complete: drawability depends only on the
relative order of the punctures used, so relabelling onto a wider or gappier subset of
{1..n} never reaches a configuration a permutation misses.
"""

import itertools

from regions import (
    make_state,
    forward,
    forward_new_arc,
    new_arc_possibilities,
    seg_possibilities_given_gen,
)
from searching import _validate_word


# ------------------------------------------------------------------ frontier steps

def _advance(states: set, letter: int) -> set:
    """Continue the arc in progress by one signed letter."""
    return {forward(s, seg) for s in states for seg in seg_possibilities_given_gen(s, letter)}


def _advance_new_arc(states: set, letter: int) -> set:
    """Start a fresh arc -- in any region -- whose first crossing gives letter, or which
    starts on the boundary if letter is 0."""
    return {
        forward_new_arc(s, seg, ri)
        for s in states
        for ri, seg in new_arc_possibilities(s, letter)
    }


# ------------------------------------------------------------------ core sweep

def _reachable(n: int, words: list[list[int]], signs: list[list[int]]) -> set:
    """
    Every configuration reachable by drawing each word as a separate arc, in order.

    signs[k][j] pins the sign of words[k][j] to +1 or -1; 0 leaves it free, in which
    case both signs are explored and their configurations merged.  A 0 letter has no
    sign, so its entry is ignored.  Returns the empty set as soon as the family becomes
    undrawable.
    """
    states = {make_state(n)}
    for word, word_signs in zip(words, signs):
        for pos, letter in enumerate(word):
            magnitude = abs(letter)
            fixed = word_signs[pos]
            # A set, so that the boundary's {0, -0} is the single option it should be.
            options = {magnitude, -magnitude} if fixed == 0 else {fixed * magnitude}
            step = _advance_new_arc if pos == 0 else _advance
            states = set().union(*(step(states, option) for option in options))
            if not states:
                return set()
    return states


def _recover_signs(n: int, words: list[list[int]]) -> list[list[int]] | None:
    """
    Pin one sign at a time, keeping the whole family drawable.  Returns None if the
    family cannot be drawn at all.

    Greedy pinning is exact here because drawability of a partially pinned family is
    monotone: if a partial assignment is still feasible, some completion of it is too.
    Costs at most 2 * (total word length) sweeps.  A 0 letter has no sign, so it is
    skipped.
    """
    signs = [[0] * len(w) for w in words]
    for k, word in enumerate(words):
        for j in range(len(word)):
            if word[j] == 0:
                continue
            for sign in (1, -1):
                signs[k][j] = sign
                if _reachable(n, words, signs):
                    break
                signs[k][j] = 0
            else:
                return None
    return signs


# ------------------------------------------------------------------ helpers

def _validate_family(words: list[list[int]], rank: int | None = None) -> list[list[int]]:
    """
    Validate each word with searching._validate_word; return them as fresh lists.

    rank=None checks the shape of each word without imposing an upper bound on its
    symbols.
    """
    if not isinstance(words, (list, tuple)) or not words:
        raise ValueError("words must be a non-empty list of words")
    checked = []
    for k, word in enumerate(words):
        if isinstance(word, int):
            raise TypeError(f"words[{k}] must be a word (list of ints), got {word!r}")
        try:
            _validate_word(list(word), rank)
        except (TypeError, ValueError) as exc:
            raise type(exc)(f"words[{k}]: {exc}") from None
        checked.append(list(word))
    return checked


def _resolve_family(words: list[list[int]], n: int | None) -> tuple[list[list[int]], int]:
    """
    Validate the family and settle the rank of the disk to draw it in.

    n=None asks for the smallest rank admitting every word, the largest |letter| in the
    family.  Any larger rank gives the same answer, for the reason given in
    `searching._resolve_rank`, so the default is a free choice rather than a guess.
    """
    words = _validate_family(words, n)
    if n is None:
        n = max(abs(x) for word in words for x in word)
    return words, n


def _relabellings(words: list[list[int]], permute: bool):
    """
    Yield (mapping, relabelled_words) for each permutation of the shared symbols.

    The boundary, 0, is not a puncture: it is never relabelled and is left out of mapping.
    """
    symbols = sorted({abs(x) for word in words for x in word} - {0})
    perms = itertools.permutations(symbols) if permute else (tuple(symbols),)
    for perm in perms:
        mapping = dict(zip(symbols, perm))
        relabel = {0: 0, **mapping}
        yield mapping, [
            [relabel[abs(x)] * (1 if x > 0 else -1) for x in word] for word in words
        ]


def _sign_spec(words: list[list[int]], respect_signs: bool) -> list[list[int]]:
    """
    Build the `signs` argument of `_reachable` for a family of words.

    With respect_signs the given signs are pinned; otherwise every position is left
    free (0) for the sweep to explore.
    """
    if respect_signs:
        return [[1 if x > 0 else -1 for x in word] for word in words]
    return [[0] * len(word) for word in words]


# ------------------------------------------------------------------ public API

def can_coexist(words: list[list[int]], n: int | None = None,
                permute: bool = True, respect_signs: bool = False) -> bool:
    """
    True if every word in words can be drawn simultaneously, as pairwise disjoint
    embedded arcs in a disk with n punctures.

    n              punctures in the disk; None takes the smallest rank admitting them all
    permute        try every permutation of the symbols shared across all words
    respect_signs  take the given signs literally instead of searching over signs

    One permutation applies to every word at once -- they share a disk, so their
    labellings cannot be chosen independently.  It costs (number of symbols)! sweeps, so
    pass permute=False when the labelling is meant as given.

    A 0 as the first or last letter of a word puts that end of its arc on the boundary.

    >>> can_coexist([[1, 2, 1], [2, 3, 2]])
    True
    >>> can_coexist([[1, 2, 1], [3, 2, 3]])   # each drawable alone, never together
    False
    """
    words, n = _resolve_family(words, n)
    for _, relabelled in _relabellings(words, permute):
        if _reachable(n, relabelled, _sign_spec(relabelled, respect_signs)):
            return True
    return False


def coexist_witness(words: list[list[int]], n: int | None = None,
                    permute: bool = True, respect_signs: bool = False) -> dict | None:
    """
    A witness that words can co-exist, or None if they cannot.  Flags are as
    `can_coexist`.

    Returns {"permutation": {old_symbol: new_symbol, ...},
             "signs":       [signed_word, ...]}

    where "signs" holds the words as actually drawn -- already relabelled by the
    permutation, with a sign chosen for every letter -- so it can be fed straight back in
    with permute=False, respect_signs=True to replay the drawing.

    >>> coexist_witness([[1, 2, 1], [2, 3, 2]])
    {'permutation': {1: 1, 2: 2, 3: 3}, 'signs': [[1, 2, 1], [2, 3, -2]]}
    """
    words, n = _resolve_family(words, n)
    for mapping, relabelled in _relabellings(words, permute):
        if respect_signs:
            signs = _sign_spec(relabelled, True)
            if not _reachable(n, relabelled, signs):
                continue
        else:
            signs = _recover_signs(n, relabelled)
            if signs is None:
                continue
        return {
            "permutation": mapping,
            "signs": [
                [sign * abs(x) for sign, x in zip(word_signs, word)]
                for word_signs, word in zip(signs, relabelled)
            ],
        }
    return None
