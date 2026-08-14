# Subwords of simple loops in the free group

Code for determining which words in the free group can appear as subwords of simple loops
in a punctured disk.

Joint work with:
- [Simi Hellsten](https://sites.google.com/view/simihellsten)
- [Alicja Pietrzak](https://sites.google.com/view/alicja-pietrzak/home)
- [Lorna Richardson](https://sites.google.com/view/simihellsten)
- [Susanna Terron](https://sites.google.com/view/susannaterron)

## Background

Consider a closed unit disk with $n$ punctures on the real axis, with generator lines drawn
from each puncture to a fixed boundary point. A path traversing a loop in the disk
accumulates a word in the free group $F_n$ by recording which generator lines it crosses and
in which direction. The central question is: which words can arise as subwords of simple
loops in the orbit $Q = B_n \cdot x_1$ under the braid group action?

The algorithm answers a necessary condition for membership: it decides whether a word can be
drawn as an embedded (non-self-crossing) arc in the punctured disk. A word that cannot be
drawn cannot be a subword of any element of $Q$. A positive answer means only "not ruled
out" — nothing here checks that the arc extends to a simple loop in the orbit.

See the accompanying paper for the mathematical background, and
[`algorithm_details.md`](algorithm_details.md) for a detailed explanation of how the
implementation works — the encoding, the geometry behind each case of the state update, and
the invariants it maintains.

## Requirements

Python 3.10 or later. No third-party dependencies.

## Layout

| path | role |
|---|---|
| `main.py` | entry point: command line and demos |
| `regions.py` | the engine — `State`, and one crossing at a time |
| `searching.py` | breadth-first search over the drawings of a single word |
| `coexistence.py` | can a whole family of words be drawn simultaneously? |
| `test/test_corpus.py` | runs `evaluate` over the word corpora |
| `test/test_coexistence.py` | self-checking suite for `coexistence.py` |
| `test/braid_orbit.py` | generates a ground-truth corpus from the braid action |
| `test/subwords/*.txt` | corpora, one word per line in Python list notation |

## Quick start

```bash
python3 main.py demo                     # narrated walk-through of all three modules
python3 main.py evaluate 1,2,-1          # is this signed word drawable?
python3 main.py signs 1,2,1,3            # find a sign assignment that works
python3 main.py coexist 1,2,1 2,3,2      # can these words be drawn simultaneously?
python3 main.py test                     # run both test suites
```

Every command takes `-n/--rank` to set the number of punctures. It defaults to the smallest
rank the input admits; raising it changes nothing, because an arc can always pass beneath an
unused puncture without recording a letter.

A word whose first letter is an inverse begins with `-`, which the argument parser would read
as an option, so put it after `--`:

```bash
python3 main.py evaluate -- -1,2,3
```

Commands exit `0` for a positive answer, `1` for a negative one, and `2` for a malformed
word, so they compose in shell scripts.

`python3 main.py demo` takes an optional section — `regions`, `searching` or `coexistence` —
to run just one walk-through.

## Code overview

### State and dynamics (`regions.py`)

The core data structure is `State`, a named tuple encoding the current configuration of the
disk:

- `n` — number of punctures
- `regions` — tuple of regions, each described by its bounding signed segment IDs
- `gen` — mapping from segment ID to generator
- `next_seg` — next fresh segment ID to allocate
- `first_crossing_done` — whether the first crossing has occurred

The key function is `forward(state, seg)`, which takes a state and a signed segment ID and
returns the updated state after crossing that segment. This implements the core dynamics: it
handles the two geometric cases (the crossed segment's pair lying in the same region or in a
different one) and the special logic for the first crossing. It raises `ValueError` if `seg`
is not in the end-region.

`forward_new_arc(state, seg, region_idx)` starts a *fresh* arc at a free interior point of any
region and makes its first crossing. Because the arc's start point is free, the cut is a slit
rather than a chord and the region is not split in two. `forward` delegates to it for the
first crossing of a word; `coexistence.py` uses it to begin each subsequent word.
`new_arc_possibilities(state, generator)` lists the `(region_idx, seg)` pairs at which such an
arc could start.

Because `State` is an immutable, hashable `NamedTuple`, states can be kept in a set and
deduplicated for free — which is what the search layer relies on.

### Search (`searching.py`)

`searching.py` implements a breadth-first search over sets of states, advancing one letter at
a time. Given a generator, there may be several valid segments to cross, so the search tracks
all reachable states simultaneously; dead branches contribute nothing to the next frontier, so
pruning is automatic. The entry points are:

- `evaluate(n, word)` — `True` if the signed word is drawable
- `valid_assignment_of_signs(n, word)` — a sign assignment making an unsigned word drawable, or `None`
- `valid_permutation_and_assignment_of_signs(n, word)` — as above, also trying every relabelling of the letters

```python
>>> from searching import evaluate, valid_assignment_of_signs
>>> evaluate(3, [1, 2, -1])
True
>>> evaluate(5, [1, 2, -1, -3, 2, 3])
False
>>> valid_assignment_of_signs(5, [1, 2, 1, 3])
[1, 2, -1, 3]
```

Words are validated as reduced words over $x_1 \ldots x_n$, and squares are rejected: the
algorithm will happily draw $x_j x_j$ as an ever-growing spiral around one puncture, but such
words do not arise as subwords of the reduced words of interest, so they are excluded rather
than handled.

### Co-existence of subwords (`coexistence.py`)

`coexistence.py` asks whether a whole *family* of words can be drawn **simultaneously**, as
pairwise disjoint embedded arcs in one disk. If $w_1,\ldots,w_k$ all occur as subwords of a
single simple loop then their arcs are disjoint sub-arcs of one embedded loop, so a negative
answer rules the family out of every element of $Q$ at once.

The words are drawn one after another into the same configuration: once $w_1$ has been drawn
the disk is cut into regions, and $w_2$ starts a fresh arc at a free interior point of any one
of them. Since a crossing is only permitted through a face bounding the current region, arcs
drawn this way are automatically disjoint from everything already drawn. What is handed from
one word to the next is a full set of region configurations, not merely a sign assignment. Any
number of words is supported.

- `can_coexist(n, words)` — `True` if the whole family can be drawn at once
- `coexist_witness(n, words)` — a witness `{"permutation": ..., "signs": [...]}`, or `None`

Both search over all permutations of the symbols shared across the words (one permutation
applies to all of them, since they share a disk) and over all assignments of signs. Pass
`permute=False` to fix the labelling, or `respect_signs=True` to take the given signs
literally.

```python
>>> from coexistence import can_coexist, coexist_witness
>>> can_coexist(5, [[1, 2, 1], [2, 3, 2]])
True
>>> coexist_witness(5, [[1, 2, 1], [2, 3, 2]])
{'permutation': {1: 1, 2: 2, 3: 3}, 'signs': [[1, 2, 1], [2, 3, -2]]}
>>> can_coexist(5, [[1, 2, 1], [3, 2, 3]])   # each drawable alone, never together
False
```

The `"signs"` entry holds the words as actually drawn — already relabelled by the permutation,
with a sign on every letter — so it can be fed straight back in with `permute=False,
respect_signs=True` to replay the drawing.

As with the single-word test, co-existence is **necessary but not sufficient**: nothing checks
that the disjoint arcs can be joined up into a single closed loop.

## Testing

```bash
python3 main.py test          # both suites
python3 test/test_corpus.py   # or run either one directly
python3 test/test_coexistence.py
```

`test/subwords/` contains text files of words, one per line in Python list notation, grouped
by expected behaviour:

- `known_valid.txt` — hand-curated; every word must evaluate `True`
- `known_non_valid.txt` — hand-curated; every word must evaluate `False`
- `braid_orbit_braidlength{k}_rank{n}.txt` — generated from the braid action, so every word is
  drawable by construction and any `False` is a genuine bug
- `mostly_non_valid.txt` — a large mixed set with no per-line ground truth, reported as a
  tally only

`test_corpus.py` evaluates each corpus and checks it against those expectations.
`test_coexistence.py` needs no corpus: it checks that one-word families reproduce the
single-word functions in `searching.py` exactly, that co-existence does not depend on the order
the words are drawn in, that every witness replays as a drawable family, that sub-families of
a co-existing family co-exist, that multi-arc configurations satisfy the `regions.py`
invariants, and that `forward_new_arc` reproduces the first-crossing rule on the initial state.

`braid_orbit.py` regenerates the ground-truth corpus from the orbit of $x_1$ under all reduced
braid words up to a given length. Generation is exponential in the braid length, so the
committed file takes minutes to reproduce:

```bash
python3 test/braid_orbit.py
```
