"""
Co-existence of several subwords in one punctured disk.

The question
-----------
`searching.evaluate` asks whether a single word can be drawn as an embedded arc.  This
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
    """Start a fresh arc -- in any region -- whose first crossing gives letter."""
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
    case both signs are explored and their configurations merged.  Returns the empty
    set as soon as the family becomes undrawable.
    """
    states = {make_state(n)}
    for word, word_signs in zip(words, signs):
        for pos, letter in enumerate(word):
            magnitude = abs(letter)
            fixed = word_signs[pos]
            options = (magnitude, -magnitude) if fixed == 0 else (fixed * magnitude,)
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
    Costs at most 2 * (total word length) sweeps.
    """
    signs = [[0] * len(w) for w in words]
    for k, word in enumerate(words):
        for j in range(len(word)):
            for sign in (1, -1):
                signs[k][j] = sign
                if _reachable(n, words, signs):
                    break
                signs[k][j] = 0
            else:
                return None
    return signs


# ------------------------------------------------------------------ helpers

def _validate_family(words: list[list[int]], rank: int) -> list[list[int]]:
    """Validate each word with searching._validate_word; return them as fresh lists."""
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


def _relabellings(words: list[list[int]], permute: bool):
    """Yield (mapping, relabelled_words) for each permutation of the shared symbols."""
    symbols = sorted({abs(x) for word in words for x in word})
    perms = itertools.permutations(symbols) if permute else (tuple(symbols),)
    for perm in perms:
        mapping = dict(zip(symbols, perm))
        yield mapping, [
            [mapping[abs(x)] * (1 if x > 0 else -1) for x in word] for word in words
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

def can_coexist(n: int, words: list[list[int]],
                permute: bool = True, respect_signs: bool = False) -> bool:
    """
    True if every word in words can be drawn simultaneously, as pairwise disjoint
    embedded arcs in a disk with n punctures.

    permute        try every permutation of the symbols shared across all words
    respect_signs  take the given signs literally instead of searching over signs

    >>> can_coexist(5, [[1, 2, 1], [2, 3, 2]])
    True
    """
    words = _validate_family(words, n)
    for _, relabelled in _relabellings(words, permute):
        if _reachable(n, relabelled, _sign_spec(relabelled, respect_signs)):
            return True
    return False


def coexist_witness(n: int, words: list[list[int]],
                    permute: bool = True, respect_signs: bool = False) -> dict | None:
    """
    A witness that words can co-exist, or None if they cannot.

    Returns {"permutation": {old_symbol: new_symbol, ...},
             "signs":       [signed_word, ...]}

    where "signs" holds the words as actually drawn -- already relabelled by the
    permutation, with a sign chosen for every letter.

    >>> coexist_witness(5, [[1, 2, 1], [2, 3, 2]])
    {'permutation': {1: 1, 2: 2, 3: 3}, 'signs': [[1, 2, 1], [2, 3, -2]]}
    """
    words = _validate_family(words, n)
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
