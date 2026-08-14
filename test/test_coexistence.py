"""
Self-checking suite for coexistence.py.  Needs no corpus.

Each property below is checked over a generated pool of short square-free words and a
random sample of pairs drawn from it, and reported as one pass/fail line:

    one-word families reproduce the single-word API in searching.py exactly
    co-existence does not depend on the order the words are drawn in
    every witness replays as a drawable family when taken literally
    sub-families of a co-existing family co-exist
    multi-arc configurations satisfy the regions.py invariants
    forward_new_arc reproduces the first-crossing rule on the initial state
    known discriminating pairs stay non-co-existing

The last of these is what shows the test is not vacuous: [1,2,1] and [3,2,3] are each
drawable alone but never together, under any permutation and any signs.

Run it directly, or as `python3 main.py test` from the repository root.
"""

# Make the modules in the repository root importable from inside test/.
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import itertools
import random

import regions as R
from searching import (
    evaluate,
    valid_assignment_of_signs,
    valid_permutation_and_assignment_of_signs,
)
from coexistence import (
    can_coexist,
    coexist_witness,
    _reachable,
    _sign_spec,
    _validate_family,
)

RANK = 5
SYMBOLS = [1, 2, 3]


def square_free_words(symbols, length, signed=True):
    """Reduced, square-free words of the given length."""
    letters = [s * g for s in symbols for g in ((1, -1) if signed else (1,))]
    def rec(w):
        if len(w) == length:
            yield list(w)
            return
        for l in letters:
            if w and (l == -w[-1] or l == w[-1]):
                continue
            yield from rec(w + [l])
    yield from rec([])


def structurally_sound(state):
    """The regions.py invariants: every face present exactly once, in +/- pairs."""
    faces = [f for region in state.regions for f in region]
    ids = set(abs(f) for f in faces)
    return (len(faces) == len(set(faces))
            and len(faces) == 2 * len(ids)
            and all(k in faces and -k in faces for k in ids))


def report(name, failures, total, detail=""):
    status = "ok" if failures == 0 else "FAIL"
    print(f"  [{status}] {name}: {failures} failures / {total}{detail}")
    return failures


def main():
    random.seed(0)
    pool = [w for L in (2, 3, 4) for w in square_free_words(SYMBOLS, L)]
    pairs = random.sample([(a, b) for a in pool for b in pool], 2000)
    failures = 0

    print("------------------------------")
    print(f"coexistence: {len(pool)} words, {len(pairs)} sampled pairs, rank {RANK}")

    # A one-word family must agree exactly with the single-word API in searching.py.
    bad = 0
    for w in pool:
        bad += can_coexist(RANK, [w], permute=False, respect_signs=True) != evaluate(RANK, w)
        bad += can_coexist(RANK, [w], permute=False) != (
            valid_assignment_of_signs(RANK, w) is not None)
        bad += can_coexist(RANK, [w]) != (
            valid_permutation_and_assignment_of_signs(RANK, w) is not None)
    failures += report("single-word families agree with searching.py", bad, 3 * len(pool))

    # Disjointness is symmetric, so the drawing order must not matter.
    bad = sum(1 for a, b in pairs if can_coexist(RANK, [a, b]) != can_coexist(RANK, [b, a]))
    failures += report("co-existence is order independent", bad, len(pairs))

    # Every witness must replay as a drawable family when taken literally.
    bad = 0
    positives = 0
    for a, b in pairs:
        if not can_coexist(RANK, [a, b]):
            continue
        positives += 1
        w = coexist_witness(RANK, [a, b])
        if w is None or not can_coexist(RANK, w["signs"], permute=False, respect_signs=True):
            bad += 1
    failures += report("witnesses replay as feasible", bad, positives)

    # A family that co-exists cannot contain a sub-family that does not.
    bad = 0
    triples = 0
    for _ in range(300):
        fam = [random.choice(pool) for _ in range(3)]
        if not can_coexist(RANK, fam):
            continue
        triples += 1
        bad += sum(1 for sub in itertools.combinations(fam, 2)
                   if not can_coexist(RANK, list(sub)))
    failures += report("sub-families of a co-existing family co-exist", bad, triples)

    # Multi-arc configurations must satisfy the regions.py invariants.
    bad = 0
    configurations = 0
    for a, b in pairs[:300]:
        fam = _validate_family([a, b], RANK)
        states = _reachable(RANK, fam, _sign_spec(fam, False))
        configurations += len(states)
        bad += sum(1 for s in states if not structurally_sound(s))
    failures += report("multi-arc configurations obey invariants", bad, configurations)

    # forward_new_arc must reproduce the pristine first-crossing rule exactly.
    bad = 0
    checked = 0
    for k in range(1, RANK + 1):
        for seg in (k, -k):
            start = R.make_state(RANK)
            checked += 1
            if R.forward(start, seg) != R.forward_new_arc(start, seg, 0):
                bad += 1
    failures += report("forward_new_arc matches the first-crossing rule", bad, checked)

    # Known discriminating cases: drawable alone, never together.
    known_apart = [([1, 2, 1], [3, 2, 3]), ([1, 2, 1], [2, 3, 2, 3])]
    bad = 0
    for a, b in known_apart:
        bad += not (can_coexist(RANK, [a]) and can_coexist(RANK, [b])
                    and not can_coexist(RANK, [a, b]))
    failures += report("known non-co-existing pairs stay non-co-existing", bad, len(known_apart))

    print("------------------------------")
    print("ALL PASS" if failures == 0 else f"{failures} FAILURES")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
