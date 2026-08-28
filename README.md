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
pairwise disjoint embedded arcs in one disk. If $w_1,\ldots,w_k$ all occur as subwords of a
single simple loop then their arcs are disjoint sub-arcs of one embedded loop, so a negative
answer rules the family out of every element of $Q$ at once.

The words are drawn one after another into the same configuration: once $w_1$ has been drawn
the disk is cut into regions, and $w_2$ starts a fresh arc at a free interior point of any one
of them. Since a crossing is only permitted through a face bounding the current region, arcs
drawn this way are automatically disjoint from everything already drawn. What is handed from
one word to the next is a full set of region configurations, not merely a sign assignment. Any
number of words is supported.

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
