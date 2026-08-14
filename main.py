"""
Entry point for the simple-loop subwords codebase.

Which words in the free group F_n can be drawn as embedded (non-self-crossing) arcs in
a disk with n punctures?  A word that cannot be drawn cannot be a subword of any simple
loop, which is what makes the question useful: it rules words out of the braid orbit
Q = B_n . x_1.  See README.md for orientation and algorithm_details.md for the details.

Layout
------
    regions.py      the engine -- State, and one crossing at a time
    searching.py    breadth-first search over drawings of a single word
    coexistence.py  can a whole family of words be drawn simultaneously?
    main.py         this file: command line and demos
    test/           corpus tests, a self-checking co-existence suite, corpus generator

Usage
-----
    python3 main.py demo                     narrated walk-through of all three modules
    python3 main.py evaluate 1,2,-1          is this signed word drawable?
    python3 main.py signs 1,2,1,3,2,3        find a sign assignment that works
    python3 main.py coexist 1,2,1 2,3,2      can these words be drawn simultaneously?
    python3 main.py test                     run both test suites

Every command takes -n/--rank to set the number of punctures.  It defaults to the
smallest rank the input admits; raising it changes nothing, because an arc can always
pass beneath an unused puncture without recording a letter.

A word whose first letter is an inverse begins with "-", which the argument parser would
read as an option, so put it after "--":

    python3 main.py evaluate -- -1,2,3
"""

import argparse
import sys
from pathlib import Path

from regions import (
    make_state,
    forward,
    gen_possibilities,
    seg_possibilities_given_gen,
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


# ------------------------------------------------------------------ word parsing

def parse_word(text: str) -> list[int]:
    """
    Parse a word given on the command line into a list of non-zero integers.

    Letters may be separated by commas or spaces, and surrounding brackets are ignored,
    so "1,2,-1", "[1, 2, -1]" and "1 2 -1" all parse alike.
    """
    cleaned = text.strip().strip("[]()").replace(",", " ")
    if not cleaned.split():
        raise argparse.ArgumentTypeError(f"empty word: {text!r}")
    try:
        return [int(tok) for tok in cleaned.split()]
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"cannot parse {text!r} as a word; expected something like 1,2,-1"
        ) from None


def default_rank(words: list[list[int]]) -> int:
    """The smallest rank admitting every letter of every word."""
    return max((abs(x) for word in words for x in word), default=1)


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
    print(f"  no face of line 3 is reachable in the negative direction:")
    print(f"    seg_possibilities_given_gen(state, -3) = {seg_possibilities_given_gen(state, -3)}")
    print(f"  the letters available at all are:")
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
    print(f"\nA word that cannot be drawn alone sinks any family containing it:")
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


def _banner(title: str) -> str:
    """A section heading for the demo output."""
    return f"\n{'=' * 78}\n {title}\n{'=' * 78}"


# ------------------------------------------------------------------ commands

def cmd_demo(args: argparse.Namespace) -> int:
    """Run the narrated walk-throughs."""
    sections = {
        "regions": demo_regions,
        "searching": demo_searching,
        "coexistence": demo_coexistence,
    }
    chosen = sections if args.section == "all" else {args.section: sections[args.section]}
    for run in chosen.values():
        run()
    print()
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    """Report whether one signed word is drawable."""
    rank = default_rank([args.word]) if args.rank is None else args.rank
    result = evaluate(rank, args.word)
    print(f"evaluate({rank}, {args.word}) = {result}")
    return 0 if result else 1


def cmd_signs(args: argparse.Namespace) -> int:
    """Search for a sign assignment, and optionally a relabelling, that works."""
    rank = default_rank([args.word]) if args.rank is None else args.rank
    if args.permute:
        assignment = valid_permutation_and_assignment_of_signs(rank, args.word)
        label = "valid_permutation_and_assignment_of_signs"
    else:
        assignment = valid_assignment_of_signs(rank, args.word)
        label = "valid_assignment_of_signs"
    print(f"{label}({rank}, {args.word}) = {assignment}")
    return 0 if assignment is not None else 1


def cmd_coexist(args: argparse.Namespace) -> int:
    """Report whether a family of words can be drawn simultaneously."""
    rank = default_rank(args.words) if args.rank is None else args.rank
    permute = not args.no_permute
    result = can_coexist(rank, args.words, permute=permute, respect_signs=args.respect_signs)
    print(f"can_coexist({rank}, {args.words}) = {result}")
    if result and args.witness:
        witness = coexist_witness(rank, args.words,
                                  permute=permute, respect_signs=args.respect_signs)
        print(f"  permutation: {witness['permutation']}")
        print(f"  as drawn:    {witness['signs']}")
    return 0 if result else 1


def cmd_test(args: argparse.Namespace) -> int:
    """Run both test suites.  They live in test/, which is not a package."""
    sys.path.insert(0, str(Path(__file__).resolve().parent / "test"))
    import test_corpus
    import test_coexistence

    corpus_failures = test_corpus.main()
    coexistence_failures = test_coexistence.main()
    return corpus_failures or coexistence_failures


# ------------------------------------------------------------------ command line

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for all subcommands."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=__doc__.split("Layout")[0].strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    # A word starting with an inverse letter starts with "-", so argparse would read it
    # as an option; "--" is the way past that.
    dash_note = 'a word starting with an inverse must follow "--", e.g. evaluate -- -1,2,3'

    def add_rank(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("-n", "--rank", type=int, default=None,
                         help="number of punctures (default: the smallest that fits)")

    demo = subparsers.add_parser("demo", help="narrated walk-through of the modules")
    demo.add_argument("section", nargs="?", default="all",
                      choices=["all", "regions", "searching", "coexistence"],
                      help="which walk-through to run (default: all)")
    demo.set_defaults(func=cmd_demo)

    ev = subparsers.add_parser("evaluate", help="is a signed word drawable?",
                               epilog=dash_note)
    ev.add_argument("word", type=parse_word, help="e.g. 1,2,-1")
    add_rank(ev)
    ev.set_defaults(func=cmd_evaluate)

    sg = subparsers.add_parser("signs", help="find a sign assignment making a word drawable",
                               epilog=dash_note)
    sg.add_argument("word", type=parse_word, help="e.g. 1,2,1,3,2,3")
    sg.add_argument("--permute", action="store_true",
                    help="also try every relabelling of the letters")
    add_rank(sg)
    sg.set_defaults(func=cmd_signs)

    co = subparsers.add_parser("coexist", help="can several words be drawn at once?",
                               epilog=dash_note)
    co.add_argument("words", nargs="+", type=parse_word, help="e.g. 1,2,1 2,3,2")
    co.add_argument("--no-permute", action="store_true",
                    help="fix the labelling instead of trying every permutation")
    co.add_argument("--respect-signs", action="store_true",
                    help="take the given signs literally instead of searching over them")
    co.add_argument("--witness", action="store_true",
                    help="also print the permutation and signs that work")
    add_rank(co)
    co.set_defaults(func=cmd_coexist)

    te = subparsers.add_parser("test", help="run both test suites")
    te.set_defaults(func=cmd_test)

    return parser


def main(argv: list[str] | None = None) -> int:
    """
    Run one subcommand.  Returns a shell exit status: 0 for success, 1 for a negative
    answer (not drawable, cannot co-exist, tests failed), 2 for a malformed word.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except (TypeError, ValueError) as exc:
        print(f"main.py: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
