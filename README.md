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

See [`algorithm_details.md`](algorithm_details.md) for the full treatment — the encoding, the
index arithmetic behind each case, and the invariants it maintains. The two sections below are
the summary.

## How a drawing is built

Three things need naming before the cases below make sense.

**Faces.** Each generator line is cut into *segments* by the places the arc has already
crossed it. A segment has two sides, and both are encoded in one signed integer: the left
face of segment `k` is `+k`, the right face is `-k`. Crossing from `+k` contributes $x_j$ and
crossing from `-k` contributes $x_j^{-1}$, where $j$ is the generator the segment belongs to.
So `+k` and `-k` are the two sides of one physical segment, and the `seg` argument to
`forward` is always the face the arc crosses *from* — `forward(state, 2)` and
`forward(state, -2)` are different moves.

**Regions.** The arc drawn so far, together with the generator lines, cuts the disk into
regions. Each is written as the tuple of signed faces on its boundary, read clockwise; the
outer circle and the drawn arc bound it too, but are implicit and not stored. The tuples are
cyclic, so `(-5, 6)` and `(6, -5)` denote the same region.

**The end-region.** `regions[0]` always holds the tip of the arc, and the tip sits at the
junction between the last entry and the first. Every case below finishes by rotating the new
end-region so this stays true.

One crossing does two things. It **splits the crossed segment** at the crossing point — one
half keeps the old ID, the other takes a fresh ID `T` carrying the same generator, so both
halves go on contributing the same letter — and it **cuts the region** the arc passed
through. Which case applies depends entirely on where the partner face `-seg` lives at that
moment.

### The cases

`forward_new_arc` handles the two cases that start an arc, `forward` the three that continue
one. `forward` delegates to `forward_new_arc` for a word's first crossing, so between them
these five are exhaustive.

**1. Starting an arc, partner in the same region** — `forward_new_arc`

The arc begins at a *free interior point*, so cutting along it is a slit, not a chord: you
can walk around its free tip, and a disk cut along a slit is still a disk. The region is
**not** split, and only the crossed segment is.

```
n = 2, cross +1
before  [1, -1, 2, -2]                                        1 region
after   [-3, 2, -2, 3, 1, -1]                                 1 region   (unchanged)
```

**2. Starting an arc, partner in a different region** — `forward_new_arc`

Same slit, but the partner face has been carried off into another region by an earlier arc.
That region takes the tip and becomes the new end-region; still nothing is split in two.
Only co-existence reaches this case, since a single word starts in a pristine disk.

```
n = 2, after [1, 2] has been drawn; new arc starts in region 0 and crosses +3,
whose partner -3 sits in region 1
before  [-4, 3, 1, -1, 2, -2]   [-3, 4]                       2 regions
after   [-5, 4, -3]   [-4, 5, 3, 1, -1, 2, -2]                2 regions  (unchanged)
```

**3. Continuing: partner in the end-region, after the crossed face** (`i < pair_pos`) — Case A

The arc leaves the region and comes straight back into it, so the cut is a genuine chord and
the region splits in two. The tip lands in whichever half holds `-seg` — here the half from
the crossed face onwards, which becomes the new `regions[0]`.

```
n = 2, cross +2
before  [-3, 2, -2, 3, 1, -1]                                 1 region
after   [-4, 3, 1, -1, 2, -2]   [-3, 4]                       2 regions  (+1)
```

**4. Continuing: partner in the end-region, before the crossed face** (`i > pair_pos`) — Case A

The same chord, but `-seg` lies in the *before* half, so that half takes the tip instead.

```
n = 3, after [1, 2] has been drawn; cross -1
before  [-5, 3, -3, 4, 1, -1, 2, -2]   [-4, 5]                2 regions
after   [6, -6, -5, 3, -3, 4, 1]   [-4, 5]   [-1, 2, -2]      3 regions  (+1)
```

**5. Continuing: partner in a different region** — Case B

The arc leaves the end-region and lands in one that was cut off earlier. The old end-region
splits in two and **neither half holds the tip**; the region owning `-seg` is not cut at all,
only relabelled and re-anchored, and it becomes the new `regions[0]`.

```
n = 2, after [1, 2] has been drawn; cross +3
before  [-4, 3, 1, -1, 2, -2]   [-3, 4]                       2 regions
after   [-5, 4, -3]   [-4, 5]   [3, 1, -1, 2, -2]             3 regions  (+1)
```

Cases 1, 3 and 5 are consecutive steps of one drawing — the word $x_1 x_2 x_1$ at $n = 2$.

The region count is the quickest check that a change to `forward` is sound: starting an arc
leaves it alone, every other crossing adds exactly one. So $k$ arcs of total length $c$ leave
$c - k + 1$ regions, and after $c$ crossings there are $n + c$ segments. `forward` raises
`ValueError` if `seg` does not bound the end-region, which is what makes an unreachable letter
a dead branch rather than a wrong answer.

## How co-existence works

Given a family $w_1, \ldots, w_k$, can they be drawn **at once**, as pairwise disjoint
embedded arcs in one disk? If they all occur as subwords of a single simple loop, their arcs
are disjoint sub-arcs of that one embedded loop — so a negative answer rules the family out of
every element of $Q$ at once, which is strictly more than testing the words one at a time.

The words are drawn one after another into the same configuration. Once $w_1$ is drawn the
disk is cut into regions; $w_2$ then starts a fresh arc at a free interior point of **any one
of them** (case 1 or 2 above) and continues with ordinary crossings (cases 3–5). What is
handed from one word to the next is a full set of region configurations, not merely a sign
assignment, and any number of words is supported.

**Disjointness needs no enforcement.** A crossing is only permitted through a face bounding
the current region, so an arc can never reach across something already drawn — the region
machinery rules it out before it is proposed. The one place the co-existence search fans out
more widely than the single-word search is the start of each arc:
`new_arc_possibilities(state, generator)` scans *every* region, where
`seg_possibilities_given_gen` scans only the end-region.

Drawing `[[1, 2, 1], [2, 3, 2]]` at $n = 3$, one surviving branch of the search:

```
init                            [1, -1, 2, -2, 3, -3]                        1 region

word 1 = [1, 2, 1] drawn as [1, 2, 1]
  new arc in region 0, cross +1 [-4, 2, -2, 3, -3, 4, 1, -1]                 1 region
  cross +2                      [-5, 3, -3, 4, 1, -1, 2, -2]  [-4, 5]        2 regions
  cross +4                      [-6, 5, -4]  [-5, 3, -3, 6]  [4, 1, -1, 2, -2]
                                                                             3 regions

word 2 = [2, 3, 2] drawn as [2, 3, -2]
  new arc in region 0, cross +5 [-7, 3, -3, 6, -5]  [-6, 7, 5, -4]  [4, 1, -1, 2, -2]
                                                                             3 regions
  cross +3                      … splits off [-7, 8]                         4 regions
  cross -5                      … splits off [-5, 3, -3]                     5 regions
```

Five regions at the end, as $c - k + 1 = 6 - 2 + 1$ predicts. Note the second arc is drawn as
`[2, 3, -2]`: with `respect_signs` off the sweep is free to flip that last letter, and it must
here — which is exactly the assignment `coexist_witness` reports for this family.

Sign choice is fused into the same breadth-first sweep as the choice of which face to cross:
at a free position the frontier advances by both $x_j$ and $x_j^{-1}$ and the results are
merged, so one sweep covers every assignment. The permutation loop sits outside everything,
and one permutation applies to all the words at once — they share a disk, so their labellings
cannot be chosen independently.

## Requirements

Python 3.10 or later. No third-party dependencies.

## Layout

| path | role |
|---|---|
| `main.py` | entry point: loads everything for an interactive session, and holds the demos |
| `regions.py` | the engine — `State`, and one crossing at a time |
| `searching.py` | breadth-first search over the drawings of a single word |
| `coexistence.py` | can a whole family of words be drawn simultaneously? |
| `test/test_corpus.py` | runs `can_exist` over the word corpora |
| `test/test_coexistence.py` | self-checking suite for `coexistence.py` |
| `test/braid_orbit.py` | generates a ground-truth corpus from the braid action |
| `test/subwords/*.txt` | corpora, one word per line in Python list notation |

## Quick start

Start an interactive session with everything loaded:

```bash
python3 -i main.py
```

This imports all three modules into one namespace and prints a summary of what is available:

```python
>>> can_exist([1, 2, 1, 3])
True
>>> can_coexist([[1, 2, 1], [2, 3, 2]])
True
>>> demo()                # narrated walk-through of all three modules
>>> run_tests()           # both test suites
```

Words are lists of non-zero integers, with $x_j$ written as `j` and its inverse as `-j`, so
$x_1 x_2 x_1^{-1}$ is `[1, 2, -1]`.

Besides `demo()`, `main.py` defines `demo_regions()`, `demo_searching()` and
`demo_coexistence()` to run a single walk-through, and `run_tests()`. Everything else in the
namespace comes from the three modules below.

## The interface

Four entry points, two for a single word and two for a family, all with the same signature:

```python
can_exist(word,          n=None, permute=True, respect_signs=False)  -> bool
can_exist_witness(word,  n=None, permute=True, respect_signs=False)  -> dict | None

can_coexist(words,       n=None, permute=True, respect_signs=False)  -> bool
coexist_witness(words,   n=None, permute=True, respect_signs=False)  -> dict | None
```

- **`n`** — punctures in the disk. Optional: it defaults to the smallest rank that admits the
  input, `max |letter|`. A larger rank never changes the answer, because an arc can always pass
  beneath an unused puncture without recording a letter, so the default is a free choice rather
  than a guess. Pass it explicitly to keep a batch of words comparable at one rank.
- **`permute`** — try every relabelling of the symbols present. On by default, so the input is
  read as a shape rather than as a particular labelling. It costs `(number of symbols)!` sweeps,
  so pass `permute=False` when the labelling is meant as given. For a family, one permutation
  applies to every word at once — they share a disk, so their labellings cannot be chosen
  independently.
- **`respect_signs`** — off by default, so only the magnitudes of the input matter and each
  position is free to become $x_j$ or $x_j^{-1}$. Pass `respect_signs=True` to take the word
  exactly as written.

The two `*_witness` functions answer the same question but return the drawing they found:

```python
{"permutation": {old_symbol: new_symbol, ...}, "signs": <the input as actually drawn>}
```

`"signs"` holds the word (or list of words) already relabelled by the permutation and with a
sign on every letter, so it can be fed straight back in with `permute=False,
respect_signs=True` to replay the drawing. A witness is `None` exactly when the corresponding
boolean is `False`.

## Code overview

### State and dynamics (`regions.py`)

The core data structure is `State`, a named tuple encoding the current configuration of the
disk:

- `n` — number of punctures
- `regions` — tuple of regions, each described by its bounding signed segment IDs
- `gen` — mapping from segment ID to generator
- `next_seg` — next fresh segment ID to allocate
- `first_crossing_done` — whether the first crossing has occurred

`forward(state, seg)` performs one crossing and returns the updated state;
`forward_new_arc(state, seg, region_idx)` starts a fresh arc in a given region and performs
its first. The five cases they cover are summarised above, under
[The cases](#the-cases). `seg_possibilities_given_gen(state, generator)` lists the faces of
the end-region that would contribute a given letter, and `new_arc_possibilities(state,
generator)` does the same across every region, for the start of an arc.

Because `State` is an immutable, hashable `NamedTuple`, states can be kept in a set and
deduplicated for free — which is what the search layer relies on.

### Search (`searching.py`)

`searching.py` implements a breadth-first search over sets of states, advancing one letter at
a time. Given a generator, there may be several valid segments to cross, so the search tracks
all reachable states simultaneously; dead branches contribute nothing to the next frontier, so
pruning is automatic.

Sign choice is folded into that same sweep: at a free position the frontier advances by both
$x_j$ and $x_j^{-1}$ and the two results are merged, which explores every assignment for the
price of one sweep. `can_exist_witness` then recovers a specific assignment by pinning one
letter at a time, which is exact because a merged sweep is the union over every completion of
the pinned prefix. The permutation loop sits outside the sweep.

```python
>>> from searching import can_exist, can_exist_witness
>>> can_exist([1, 2, -1], permute=False, respect_signs=True)     # exactly as written
True
>>> can_exist([1, 2, 1, 3], permute=False, respect_signs=True)
False
>>> can_exist([1, 2, 1, 3], permute=False)                       # signs free
True
>>> can_exist_witness([1, 2, 1, 3], permute=False)
{'permutation': {1: 1, 2: 2, 3: 3}, 'signs': [1, 2, -1, 3]}
>>> can_exist([1, 2, 1, 3, 2, 3])                                # signs and labels free
False
```

Words are validated as reduced words over $x_1 \ldots x_n$, and squares are rejected: the
algorithm will happily draw $x_j x_j$ as an ever-growing spiral around one puncture, but such
words do not arise as subwords of the reduced words of interest, so they are excluded rather
than handled.

### Co-existence of subwords (`coexistence.py`)

`coexistence.py` asks whether a whole *family* of words can be drawn **simultaneously**, as
pairwise disjoint embedded arcs in one disk. [How co-existence works](#how-co-existence-works)
above describes the mechanism and works an example through.

`can_coexist(words)` and `coexist_witness(words)` take the same optional rank and the same two
flags as their single-word counterparts. A one-word family is exactly the single-word question,
and `test_coexistence.py` checks that the two agree under every combination of the flags.

```python
>>> from coexistence import can_coexist, coexist_witness
>>> can_coexist([[1, 2, 1], [2, 3, 2]])
True
>>> coexist_witness([[1, 2, 1], [2, 3, 2]])
{'permutation': {1: 1, 2: 2, 3: 3}, 'signs': [[1, 2, 1], [2, 3, -2]]}
>>> can_coexist([[1, 2, 1], [3, 2, 3]])   # each drawable alone, never together
False
```

As with the single-word test, co-existence is **necessary but not sufficient**: nothing checks
that the disjoint arcs can be joined up into a single closed loop.

## Testing

```bash
python3 test/test_corpus.py       # either suite, directly
python3 test/test_coexistence.py
```

or `run_tests()` from an interactive session to run both.

`test/subwords/` contains text files of words, one per line in Python list notation, grouped
by expected behaviour:

- `known_valid.txt` — hand-curated; every word must come out `True`
- `known_non_valid.txt` — hand-curated; every word must come out `False`
- `braid_orbit_braidlength{k}_rank{n}.txt` — generated from the braid action, so every word is
  drawable by construction and any `False` is a genuine bug
- `mostly_non_valid.txt` — a large mixed set with no per-line ground truth, reported as a
  tally only

`test_corpus.py` runs `can_exist` over each corpus — with `permute=False, respect_signs=True`,
so every word is taken exactly as written — and checks the tally against those expectations.

`test_coexistence.py` needs no corpus. It checks that one-word families reproduce the
single-word API in `searching.py` under every combination of the flags (the two are independent
implementations of the same question, which makes this the sharpest check in the suite), that
a witness replays as drawable and appears exactly when the boolean is `True`, that the default
rank agrees with a larger one, that co-existence does not depend on the order the words are
drawn in, that sub-families of a co-existing family co-exist, that multi-arc configurations
satisfy the `regions.py` invariants, and that `forward_new_arc` reproduces the first-crossing
rule on the initial state.

`braid_orbit.py` regenerates the ground-truth corpus from the orbit of $x_1$ under all reduced
braid words up to a given length. Generation is exponential in the braid length, so the
committed file takes minutes to reproduce:

```bash
python3 test/braid_orbit.py
```
