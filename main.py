"""
Interactive entry point.  Start a session with everything loaded:

    python3 -i main.py

That imports the engine (`regions.py`), the single-word search (`searching.py`) and the
co-existence test (`coexistence.py`) into one namespace, defines the demos below, and
prints a summary of what is available.

Which words in the free group F_n can be drawn as embedded (non-self-crossing) arcs in a
disk with n punctures?  A word that cannot be drawn cannot be a subword of any simple
loop, which is what makes the question useful: it rules words out of the braid orbit
Q = B_n . x_1.  See README.md for orientation and algorithm_details.md for the details.

Words are lists of non-zero integers, with x_j written as j and its inverse as -j, so
x_1 x_2 x_1^-1 is [1, 2, -1].  The rank n must be at least max |letter|; making it larger
changes nothing, because an arc can always pass beneath an unused puncture without
recording a letter.
"""

import sys
from pathlib import Path

from regions import (
    State,
    make_state,
    forward,
    forward_new_arc,
    gen_possibilities,
    seg_possibilities_given_gen,
    new_arc_possibilities,
    state_str,
)
from searching import (
    evaluate,
    valid_assignment_of_signs,
    valid_permutation_and_assignment_of_signs,
)
from coexistence import (
    can_coexist,
    coexist_witness,
)

# Captured at import: `python3 -i` deletes __file__ before handing over the prompt, so it
# cannot be read from inside a function called interactively.
_REPO_ROOT = Path(__file__).resolve().parent


# ------------------------------------------------------------------ demos

def demo_regions() -> None:
    """Walk through the state and the crossing update in regions.py."""
    print(_banner("regions.py -- drawing an arc one crossing at a time"))

    state = make_state(5)
    print("A disk with 5 punctures, before anything is drawn, is a single region:")
    print(f"  {state.regions}")
    print("  Reading it clockwise: down the left face of line 1 (+1), round the")
    print("  puncture, back up its right face (-1), across to line 2, and so on.")

    state = forward(state, 2)
    print("\nCrossing face 2 starts the arc.  Its start point is free, so the cut is a")
    print("slit rather than a chord: the segment splits, but the region does not.")
    print(f"  {state.regions}")

    state = forward(state, 2)
    print("\nCrossing face 2 again is an ordinary crossing, so now the region does split.")
    print("regions[0] is always the region holding the tip of the arc:")
    print(f"  {state.regions}")

    print("\nWhat the arc can do next is limited by the region its tip sits in.")
    print("  no face of line 3 is reachable in the negative direction:")
    print(f"    seg_possibilities_given_gen(state, -3) = {seg_possibilities_given_gen(state, -3)}")
    print("  the letters available at all are:")
    print(f"    gen_possibilities(state)               = {sorted(gen_possibilities(state))}")

    print("\nThe full state:")
    for line in state_str(state).splitlines():
        print(f"  {line}")


def demo_searching() -> None:
    """Walk through the single-word search in searching.py."""
    print(_banner("searching.py -- is a single word drawable?"))

    print("A letter can often be produced by crossing any one of several faces, so the")
    print("search carries the whole frontier of live drawings and advances it one letter")
    print("at a time.  Dead branches drop out on their own.\n")

    for word in ([1, 2, -1], [1, 2, -1, -3, 2, 3]):
        print(f"  evaluate(5, {word}) = {evaluate(5, word)}")

    print("\nRead as an unsigned word, [1, 2, 1, 3] is free to choose its signs, and one")
    print("choice does make it drawable even though the all-positive reading is not:")
    print(f"  evaluate(5, [1, 2, 1, 3])                  = {evaluate(5, [1, 2, 1, 3])}")
    print(f"  valid_assignment_of_signs(5, [1, 2, 1, 3]) = "
          f"{valid_assignment_of_signs(5, [1, 2, 1, 3])}")

    hard = [1, 2, 1, 3, 2, 3]
    print(f"\n{hard} is drawable under no assignment of signs ...")
    print(f"  valid_assignment_of_signs(5, {hard}) = {valid_assignment_of_signs(5, hard)}")
    print("... and under no relabelling of its letters either:")
    print(f"  valid_permutation_and_assignment_of_signs(5, {hard}) = "
          f"{valid_permutation_and_assignment_of_signs(5, hard)}")


def demo_coexistence() -> None:
    """Walk through the multi-word co-existence test in coexistence.py."""
    print(_banner("coexistence.py -- can a family of words be drawn at once?"))

    rank = 5
    print("The words are drawn one after another into the same disk.  A crossing is only")
    print("permitted through a face bounding the current region, so arcs drawn this way")
    print("are automatically disjoint -- disjointness needs no separate enforcement.\n")

    pair = [[1, 2, 1], [2, 3, 2]]
    print(f"  can_coexist({rank}, {pair}) = {can_coexist(rank, pair)}")
    print(f"  coexist_witness(...)                       = {coexist_witness(rank, pair)}")
    print("  The witness holds the words as actually drawn, so it can be fed back in")
    print("  with permute=False, respect_signs=True to replay the drawing.")

    solo = [1, 2, 1, 3, 2, 3]
    print("\nA word that cannot be drawn alone sinks any family containing it:")
    print(f"  can_coexist({rank}, [{solo}]) = {can_coexist(rank, [solo])}")

    family = [[1, 2, 1]] * 3
    print(f"\nThree disjoint copies of [1, 2, 1] fit in a disk with {rank} punctures:")
    print(f"  can_coexist({rank}, {family}) = {can_coexist(rank, family)}")

    print("\nThe interesting case -- each drawable alone, but never together, no matter")
    print("how the letters are permuted or signed:")
    for a, b in ([[1, 2, 1], [3, 2, 3]], [[1, 2, 1], [2, 3, 2, 3]]):
        alone = can_coexist(rank, [a]) and can_coexist(rank, [b])
        print(f"  {str(a):12} & {str(b):15} each alone = {alone}, "
              f"together = {can_coexist(rank, [a, b])}")

    print("\nAny number of words is allowed; they are drawn one after another:")
    grow = [[1, 2, 1], [2, 3, 2], [1, 3, 1], [2, 1, 2]]
    for k in range(1, len(grow) + 1):
        print(f"  first {k} of {grow}: {can_coexist(rank, grow[:k])}")

    print("\nCo-existence is necessary but not sufficient, as with the single-word test:")
    print("nothing here checks that the disjoint arcs can be joined into one closed loop.")


def demo() -> None:
    """Run all three narrated walk-throughs."""
    demo_regions()
    demo_searching()
    demo_coexistence()
    print()


def _banner(title: str) -> str:
    """A section heading for the demo output."""
    return f"\n{'=' * 78}\n {title}\n{'=' * 78}"


# ------------------------------------------------------------------ tests

def run_tests() -> int:
    """
    Run both test suites and return the number that reported failures.

    They live in test/, which is not a package, so it goes on the path first.
    """
    sys.path.insert(0, str(_REPO_ROOT / "test"))
    import test_corpus
    import test_coexistence

    return test_corpus.main() + test_coexistence.main()


# ------------------------------------------------------------------ session banner

OVERVIEW = """\
Simple-loop subwords.  Words are lists of non-zero ints, so x_1 x_2 x_1^-1 is [1, 2, -1].

  searching.py
    evaluate(n, word)                                   is a signed word drawable?
    valid_assignment_of_signs(n, word)                  signs that make it drawable
    valid_permutation_and_assignment_of_signs(n, word)  ... also relabelling letters

  coexistence.py
    can_coexist(n, words)                               drawable all at once?
    coexist_witness(n, words)                           ... with permutation and signs

  regions.py
    make_state(n), forward(state, seg), forward_new_arc(state, seg, region_idx),
    seg_possibilities_given_gen(state, gen), gen_possibilities(state),
    new_arc_possibilities(state, gen), state_str(state)

  main.py
    demo()          narrated walk-through of all three modules
                    (or demo_regions() / demo_searching() / demo_coexistence())
    run_tests()     both test suites

Try:  evaluate(5, [1, 2, -1])      or      demo()"""


if __name__ == "__main__":
    print(OVERVIEW)
