"""
Interactive entry point.  Start a session with everything loaded:

    python3 -i main.py

That imports the engine (`regions.py`), the single-word search (`searching.py`) and the
co-existence test (`coexistence.py`) into one namespace, defines the demos below, and
prints a summary of what is available.

Which words in the free group F_n can be drawn as embedded (non-self-crossing) arcs in a
disk with n punctures?  A word that cannot be drawn cannot be a subword of any simple
word, which is what makes the question useful.  See docs/algorithm.md for how the
algorithm works and docs/implementation.md for how the code implements it.

Words are lists of integers, with x_j written as j and its inverse as -j, so
x_1 x_2 x_1^-1 is [1, 2, -1].  A 0 at either end puts that end of the arc on the boundary
of the disk, so [0, 1, 2, -1, 0] is [1, 2, -1] drawn from the boundary back to it.  The
rank is optional throughout: it defaults to the smallest disk that admits the word,
max |letter|, and a larger one changes nothing, because an arc can always pass beneath
an unused puncture without recording a letter.
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
    can_exist,
    can_exist_witness,
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
    print("  Reading it clockwise: along the boundary of the disk (0), down the left face")
    print("  of line 1 (+1), round the puncture, back up its right face (-1), across to")
    print("  line 2, and so on.")

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

    print("\nAn end of the arc can also lie on the boundary.  The boundary is one more line,")
    print("generator 0, with a single face: an arc can start or end on it, never cross it.")
    print("Drawing [0, 1, 0], a loop round puncture 1, in a disk with 1 puncture:")
    state = make_state(1)
    print(f"  {'before':17} {state.regions}")
    for seg, step in ((0, "start on face 0"), (1, "cross face 1"), (0, "end on face 0")):
        state = forward(state, seg)
        print(f"  {step:17} {state.regions}")
    print("  Starting on the boundary splits face 0 but cuts nothing.  The crossing after")
    print("  it is then an ordinary chord, not a slit, and ending on the boundary is a")
    print("  chord too: each of those two steps adds a region.")


def demo_searching() -> None:
    """Walk through the single-word search in searching.py."""
    print(_banner("searching.py -- is a single word drawable?"))

    print("A letter can often be produced by crossing any one of several faces, so the")
    print("search carries the whole frontier of live drawings and advances it one letter")
    print("at a time.  Dead branches drop out on their own.\n")

    print("With respect_signs=True and permute=False the word is taken exactly as written:")
    for word in ([1, 2, -1], [1, 2, -1, -3, 2, 3]):
        call = f"can_exist({word}, permute=False, respect_signs=True)"
        print(f"  {call:66} = {can_exist(word, permute=False, respect_signs=True)}")

    print("\nBy default the signs are free instead.  [1, 2, 1, 3] is not drawable as")
    print("written, but one choice of signs does make it so:")
    print(f"  can_exist([1, 2, 1, 3], permute=False, respect_signs=True) = "
          f"{can_exist([1, 2, 1, 3], permute=False, respect_signs=True)}")
    print(f"  can_exist([1, 2, 1, 3], permute=False)                     = "
          f"{can_exist([1, 2, 1, 3], permute=False)}")
    print(f"  can_exist_witness([1, 2, 1, 3], permute=False)             = "
          f"{can_exist_witness([1, 2, 1, 3], permute=False)}")
    print("  The witness holds the word as actually drawn, so it can be fed back in with")
    print("  permute=False, respect_signs=True to replay the drawing.")

    hard = [1, 2, 1, 3, 2, 3]
    print(f"\n{hard} survives no assignment of signs ...")
    print(f"  can_exist({hard}, permute=False) = {can_exist(hard, permute=False)}")
    print("... nor any relabelling of its letters, which is what the default permute=True")
    print("adds on top:")
    print(f"  can_exist({hard})               = {can_exist(hard)}")

    print("\nA 0 at either end of a word puts that end of the arc on the boundary.  A free")
    print("end can wander anywhere -- here it lets [-1, 2] wrap round puncture 1 -- so")
    print("pinning it to the boundary can only rule words out:")
    for word in ([-1, 2], [0, -1, 2]):
        call = f"can_exist({word}, permute=False, respect_signs=True)"
        print(f"  {call:66} = {can_exist(word, permute=False, respect_signs=True)}")
    print("Simple words are loops based on the boundary, so both ends can go there:")
    print(f"  can_exist_witness([0, 1, 2, 1, 0]) = {can_exist_witness([0, 1, 2, 1, 0])}")
    print("while [1, 2, 1, 2] is drawable, but never as a loop based on the boundary:")
    for word in ([1, 2, 1, 2], [0, 1, 2, 1, 2, 0]):
        print(f"  {f'can_exist({word})':33} = {can_exist(word)}")

    print("\nThe rank is optional, and defaults to the smallest disk admitting the word.")
    print("Punctures the word never mentions are neither a help nor a hindrance:")
    print(f"  {'can_exist([1, 2, 1, 3], permute=False)':41} = "
          f"{can_exist([1, 2, 1, 3], permute=False)}   (rank 3, the default)")
    print(f"  {'can_exist([1, 2, 1, 3], 9, permute=False)':41} = "
          f"{can_exist([1, 2, 1, 3], 9, permute=False)}   (rank 9)")


def demo_coexistence() -> None:
    """Walk through the multi-word co-existence test in coexistence.py."""
    print(_banner("coexistence.py -- can a family of words be drawn at once?"))

    print("The words are drawn one after another into the same disk.  A crossing is only")
    print("permitted through a face bounding the current region, so arcs drawn this way")
    print("are automatically disjoint -- disjointness needs no separate enforcement.\n")

    pair = [[1, 2, 1], [2, 3, 2]]
    print(f"  {f'can_coexist({pair})':39} = {can_coexist(pair)}")
    print(f"  {'coexist_witness(...)':39} = {coexist_witness(pair)}")
    print("  Same interface as the single-word test: an optional rank, and the same two")
    print("  flags, except that one permutation has to serve every word at once.")

    solo = [1, 2, 1, 3, 2, 3]
    print("\nA word that cannot be drawn alone sinks any family containing it:")
    print(f"  can_coexist([{solo}]) = {can_coexist([solo])}")

    family = [[1, 2, 1]] * 3
    print("\nThree disjoint copies of [1, 2, 1] fit in the same disk:")
    print(f"  can_coexist({family}) = {can_coexist(family)}")

    print("\nThe interesting case -- each drawable alone, but never together, no matter")
    print("how the letters are permuted or signed:")
    for a, b in ([[1, 2, 1], [3, 2, 3]], [[1, 2, 1], [2, 3, 2, 3]]):
        alone = can_coexist([a]) and can_coexist([b])
        print(f"  {str(a):12} & {str(b):15} each alone = {alone}, "
              f"together = {can_coexist([a, b])}")

    print("\nAny number of words is allowed; they are drawn one after another:")
    grow = [[1, 2, 1], [2, 3, 2], [1, 3, 1], [2, 1, 2]]
    for k in range(1, len(grow) + 1):
        print(f"  first {k} of {grow}: {can_coexist(grow[:k])}")

    print("\nWords may touch the boundary too, and any number of them may.  A loop round")
    print("puncture 1 cuts the disk in two, and [2, 1, 2] fits on neither side of it:")
    for pair in ([[1], [2, 1, 2]], [[0, 1, 0], [2, 1, 2]]):
        print(f"  {f'can_coexist({pair})':39} = {can_coexist(pair)}")

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
    Run all three test suites and return the number that reported failures.

    They live in test/, which is not a package, so it goes on the path first.
    """
    sys.path.insert(0, str(_REPO_ROOT / "test"))
    import test_corpus
    import test_coexistence
    import test_boundary

    return test_corpus.main() + test_coexistence.main() + test_boundary.main()


# ------------------------------------------------------------------ session banner

OVERVIEW = """\
Simple-loop subwords.  Words are lists of ints, so x_1 x_2 x_1^-1 is [1, 2, -1], and a 0
at either end puts that end of the arc on the boundary, as in [0, 1, 2, -1, 0].

  searching.py
    can_exist(word)                     drawable as an embedded arc?
    can_exist_witness(word)             ... with the signs and labelling it used

  coexistence.py
    can_coexist(words)                  drawable all at once, as disjoint arcs?
    coexist_witness(words)              ... with the signs and labelling they used

  All four take the rank as an optional second argument, defaulting to the smallest
  disk that admits the input, and the flags permute=True and respect_signs=False,
  which say whether the labelling and the signs of the input are meant literally.

  regions.py
    make_state(n), forward(state, seg), forward_new_arc(state, seg, region_idx),
    seg_possibilities_given_gen(state, gen), gen_possibilities(state),
    new_arc_possibilities(state, gen), state_str(state)

  main.py
    demo()          narrated walk-through of all three modules
                    (or demo_regions() / demo_searching() / demo_coexistence())
    run_tests()     all three test suites

Try:  can_exist([1, 2, 1, 3])      or      demo()"""


if __name__ == "__main__":
    print(OVERVIEW)
