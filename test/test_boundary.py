"""
Self-checking suite for arcs with an end on the boundary of the disk.

A 0 as the first or last letter of a word puts that end of the arc on the boundary:
[0, 1, 2, -1, 0] is [1, 2, -1] drawn from the boundary back to the boundary.  Each
property below is checked over generated words, or over the braid orbit corpus, and
reported as one pass/fail line:

    every loop in the braid orbit is drawable from the boundary back to it, and so is
        every suffix of it ending there
    starting on the boundary and ending on it agree when the arc is reversed
    an end on the boundary only constrains: freeing it never loses a drawing
    one-word families reproduce the single-word API in searching.py
    co-existence with boundary words is order independent
    the default rank agrees with a larger one
    witnesses replay as feasible, with every 0 left where it was
    configurations satisfy the regions.py invariants and the counts they predict
    validation admits 0 at either end of a word and nowhere else
    known discriminating cases stay discriminating

The braid orbit is the ground truth: its words are simple loops based on the boundary,
so any failure there is a genuine bug.  The reversal check is the sharpest of the rest,
because regions.py starts and ends an arc on the boundary by different code.

Run it directly, or via `run_tests()` in a `python3 -i main.py` session.
"""

# Make the modules in the repository root importable from inside test/.
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import ast
import random

from searching import (
    can_exist,
    can_exist_witness,
    _sweep,
)
from coexistence import (
    can_coexist,
    coexist_witness,
    _reachable,
    _sign_spec,
    _validate_family,
)
from test_coexistence import (
    report,
    square_free_words,
    structurally_sound,
)

RANK = 5
SYMBOLS = [1, 2, 3]

ORBIT = Path(__file__).resolve().parent / "subwords" / "braid_orbit_braidlength7_rank7.txt"
ORBIT_RANK = 7


def boundary_variants(w):
    """w with neither end, the start, the end, and both ends on the boundary."""
    return [w, [0] + w, w + [0], [0] + w + [0]]


def reverse_arc(w):
    """The word spelt by the same arc run backwards: reversed, every letter inverted."""
    return [-x for x in reversed(w)]


def exactly(w, n=RANK):
    """can_exist with the word taken exactly as written."""
    return can_exist(w, n, permute=False, respect_signs=True)


def counts_match(state, words):
    """
    The counts the regions.py invariants predict once every word is drawn: n + c
    generator segments, 1 + b boundary segments and 1 + sum(c_k - 1 + b_k) regions, where
    arc k makes c_k crossings and has b_k of its ends on the boundary.
    """
    crossings = [sum(1 for x in w if x) for w in words]
    ends = [(w[0] == 0) + (w[-1] == 0) for w in words]
    faces = [f for region in state.regions for f in region]
    boundary = sum(1 for f in faces if state.gen[abs(f)] == 0)
    return (len(faces) - boundary == 2 * (state.n + sum(crossings))
            and boundary == 1 + sum(ends)
            and len(state.regions) == 1 + sum(c - 1 + b for c, b in zip(crossings, ends)))


def zeros_kept(words, drawn):
    """True if every 0 in words is still a 0 in drawn, and nothing else became one."""
    return all((x == 0) == (y == 0)
               for word, drawn_word in zip(words, drawn)
               for x, y in zip(word, drawn_word))


def main():
    random.seed(0)
    base = [w for L in (1, 2, 3, 4) for w in square_free_words(SYMBOLS, L)]
    pool = [v for w in base for v in boundary_variants(w)]
    pairs = random.sample([(a, b) for a in pool for b in pool], 2000)
    failures = 0

    print("------------------------------")
    print(f"boundary: {len(pool)} words, {len(pairs)} sampled pairs, rank {RANK}")

    # Every word in the braid orbit is a simple loop based on the boundary, so it can be
    # drawn from the boundary back to it, and every prefix and suffix of it can be drawn
    # with its one end there.  The prefixes need no sweep of their own: the sweep of the
    # loop passes through each of them, so it already fails if one is undrawable.
    with open(ORBIT) as f:
        orbit = [ast.literal_eval(line) for line in f]
    loops = [[0] + w + [0] for w in orbit]
    suffixes = sorted({tuple(w[k:]) + (0,) for w in orbit for k in range(1, len(w))})
    cases = loops + [list(s) for s in suffixes]
    bad = sum(1 for case in cases if not exactly(case, ORBIT_RANK))
    failures += report("braid orbit loops and their suffixes reach the boundary",
                       bad, len(cases))

    # Running the arc backwards reverses the word, inverts every letter and swaps its
    # ends.  regions.py starts and ends an arc on the boundary by different code, so this
    # checks the one against the other.
    long_pool = [w for L in range(1, 7) for w in square_free_words(SYMBOLS, L)]
    bad = sum(exactly([0] + w) != exactly(reverse_arc(w) + [0]) for w in long_pool)
    bad += sum(exactly([0] + w + [0]) != exactly([0] + reverse_arc(w) + [0]) for w in long_pool)
    failures += report("starting and ending on the boundary agree under reversal",
                       bad, 2 * len(long_pool))

    # An end on the boundary can always be pulled in off it, so it only ever constrains:
    # freeing an end never makes a drawable word undrawable.
    bad = 0
    for w in long_pool:
        free, start, end, both = (exactly(v) for v in boundary_variants(w))
        bad += (both and not (start and end)) or ((start or end) and not free)
    failures += report("freeing an end never loses a drawing", bad, len(long_pool))

    # A one-word family must agree exactly with the single-word API in searching.py,
    # under every combination of the flags, boundary letters included.
    flags = [(permute, respect) for permute in (False, True) for respect in (False, True)]
    bad = 0
    for w in pool:
        for permute, respect_signs in flags:
            bad += (can_coexist([w], RANK, permute=permute, respect_signs=respect_signs)
                    != can_exist(w, RANK, permute=permute, respect_signs=respect_signs))
    failures += report("single-word families agree with searching.py",
                       bad, len(flags) * len(pool))

    # Disjointness is symmetric, so the drawing order must not matter -- including the
    # order in which arcs claim pieces of the boundary.
    bad = sum(1 for a, b in pairs if can_coexist([a, b], RANK) != can_coexist([b, a], RANK))
    failures += report("co-existence is order independent", bad, len(pairs))

    # Extra punctures are neither a help nor a hindrance, with or without the boundary.
    bad = sum(can_exist(w) != can_exist(w, RANK) for w in pool)
    bad += sum(can_coexist([a, b]) != can_coexist([a, b], RANK) for a, b in pairs[:300])
    failures += report("the default rank agrees with a larger one", bad, len(pool) + 300)

    # A witness must replay when taken literally, keep every 0 where it was, and leave the
    # boundary out of the permutation; and it must be present exactly when the boolean is.
    bad = 0
    for w in pool:
        witness = can_exist_witness(w, RANK)
        if not can_exist(w, RANK):
            bad += witness is not None
        elif (witness is None or 0 in witness["permutation"]
              or not zeros_kept([w], [witness["signs"]])
              or not exactly(witness["signs"])):
            bad += 1
    positives = 0
    for a, b in pairs:
        if not can_coexist([a, b], RANK):
            continue
        positives += 1
        witness = coexist_witness([a, b], RANK)
        bad += (witness is None or 0 in witness["permutation"]
                or not zeros_kept([a, b], witness["signs"])
                or not can_coexist(witness["signs"], RANK, permute=False, respect_signs=True))
    failures += report("witnesses replay as feasible, boundary kept", bad, len(pool) + positives)

    # Every configuration reached must satisfy the regions.py invariants, and have the
    # region and segment counts they predict.
    bad = 0
    configurations = 0
    for w in pool:
        states = _sweep(RANK, w, [0] * len(w))
        configurations += len(states)
        bad += sum(1 for s in states if not (structurally_sound(s) and counts_match(s, [w])))
    for a, b in pairs[:300]:
        fam = _validate_family([a, b], RANK)
        states = _reachable(RANK, fam, _sign_spec(fam, False))
        configurations += len(states)
        bad += sum(1 for s in states if not (structurally_sound(s) and counts_match(s, fam)))
    failures += report("configurations obey invariants and counts", bad, configurations)

    # 0 is admitted at either end of a word, and nowhere else.
    accepted = [[0, 1], [1, 0], [0, 1, 0], [0, 1, 2, -1, 0]]
    rejected = [[0], [0, 0], [1, 0, 2], [0, 0, 1], [1, 0, 0]]
    bad = 0
    for w in accepted:
        try:
            can_exist(w)
            can_coexist([w, [2]])
        except (TypeError, ValueError):
            bad += 1
    for w in rejected:
        for family in ([w], [[2], w]):
            try:
                can_coexist(family) if len(family) > 1 else can_exist(w)
            except ValueError:
                continue
            bad += 1
    failures += report("validation admits 0 at the ends and nowhere else",
                       bad, len(accepted) + 2 * len(rejected))

    # Known discriminating cases, which show the boundary genuinely constrains.  [-1, 2]
    # can be drawn from a free start, which lets the arc wrap round p_1, but not from the
    # boundary.  [1, 2, 1, 2] can have either end on the boundary, but not both.  A loop
    # round p_1 cuts the disk in two, and [2, 1, 2] fits on neither side of it.  And
    # [1, 2, 1], [2, 1, 2] co-exist, but not as a prefix and a suffix.
    known = [
        exactly([-1, 2]) and not exactly([0, -1, 2]),
        (exactly([0, 1, 2, 1, 2]) and exactly([1, 2, 1, 2, 0])
         and not exactly([0, 1, 2, 1, 2, 0])),
        can_coexist([[1], [2, 1, 2]]) and not can_coexist([[0, 1, 0], [2, 1, 2]]),
        can_coexist([[1, 2, 1], [2, 1, 2]]) and not can_coexist([[0, 1, 2, 1], [2, 1, 2, 0]]),
    ]
    failures += report("known discriminating cases stay discriminating",
                       known.count(False), len(known))

    print("------------------------------")
    print("ALL PASS" if failures == 0 else f"{failures} FAILURES")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
