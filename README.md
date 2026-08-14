# Subwords of simple loops in the free group

Code for determining which words in the free group can appear as subwords of simple loops in a punctured disk.

Joint work with:
- [Simi Hellsten](https://sites.google.com/view/simihellsten)
- [Alicja Pietrzak](https://sites.google.com/view/alicja-pietrzak/home)
- [Lorna Richardson](https://sites.google.com/view/simihellsten)
- [Susanna Terron](https://sites.google.com/view/susannaterron)

## Background

Consider a closed unit disk with $n$ punctures on the real axis, with generator lines drawn from each puncture to a fixed boundary point. A path traversing a loop in the disk accumulates a word in the free group $F_n$ by recording which generator lines it crosses and in which direction. The central question is: which words can arise as subwords of simple loops in the orbit $Q = B_n \cdot x_1$ under the braid group action?

See [`tex/build/main.pdf`](tex/build/main.pdf) for the full mathematical background, and
[`algorithm_details.md`](algorithm_details.md) for a detailed explanation of how the
implementation works — the encoding, the geometry behind each case of the state update, and the
invariants it maintains.

## Code Overview

### State and dynamics (`src/regions.py`)

The core data structure is `State`, a named tuple encoding the current configuration of the disk:

- `n` — number of punctures
- `regions` — tuple of regions, each described by its bounding signed segment IDs
- `gen` — mapping from segment ID to generator
- `next_seg` — next fresh segment ID to allocate
- `first_crossing_done` — whether the first crossing has occurred

The key function is `forward(state, seg)`, which takes a state and a signed segment ID and returns the updated state after crossing that segment. This implements the core dynamics: it handles the two geometric cases (the crossed segment's pair lying in the same region or in different regions) and the special logic for the first crossing. It raises `ValueError` if `seg` is not in the end-region.

`forward_new_arc(state, seg, region_idx)` starts a *fresh* arc at a free interior point of any region and makes its first crossing. Because the arc's start point is free, the cut is a slit rather than a chord and the region is not split in two. `forward` delegates to it for the first crossing of a word; `coexistence.py` uses it to begin each subsequent word. `new_arc_possibilities(state, generator)` lists the `(region_idx, seg)` pairs at which such an arc could start.

### Search (`src/searching.py`)

`searching.py` implements a BFS over sets of states, advancing one letter at a time. Given a generator, there may be multiple valid segments to cross, so the search tracks all reachable states simultaneously. The main entry points are:

- `evaluate(n, word)` — returns `True` if the signed word is realisable
- `valid_assignment_of_signs(n, word)` — finds a valid sign assignment for an unsigned word, or `None`
- `valid_permutation_and_assignment_of_signs(n, word)` — as above, also trying every relabelling of the letters
- `count_realisable(rank, length, prefix)` / `collect_realisable(...)` — count or save realisable words to CSV
- `count_minimal_invalid(rank, max_length)` / `collect_minimal_invalid(...)` — count or save minimal invalid words

### Co-existence of subwords (`src/coexistence.py`)

`coexistence.py` asks whether a whole *family* of words can be drawn **simultaneously**, as pairwise disjoint embedded arcs in one disk. If $w_1,\ldots,w_k$ all occur as subwords of a single simple loop then their arcs are disjoint sub-arcs of one embedded loop, so a negative answer rules the family out of every element of $Q$ at once.

The words are drawn one after another into the same configuration: once $w_1$ has been drawn the disk is cut into regions, and $w_2$ starts a fresh arc at a free interior point of any one of them. Since a crossing is only permitted through a face bounding the current region, arcs drawn this way are automatically disjoint from everything already drawn. What is handed from one word to the next is a full set of region configurations, not merely a sign assignment. Any number of words is supported.

- `can_coexist(n, words)` — `True` if the whole family can be drawn at once
- `coexist_witness(n, words)` — a witness `{"permutation": ..., "signs": [...]}`, or `None`

Both search over all permutations of the symbols shared across the words (one permutation applies to all of them, since they share a disk) and over all assignments of signs. Pass `permute=False` to fix the labelling, or `respect_signs=True` to take the given signs literally.

```python
>>> from src.coexistence import can_coexist, coexist_witness
>>> can_coexist(5, [[1, 2, 1], [2, 3, 2]])
True
>>> coexist_witness(5, [[1, 2, 1], [2, 3, 2]])
{'permutation': {1: 1, 2: 2, 3: 3}, 'signs': [[1, 2, 1], [2, 3, -2]]}
>>> can_coexist(5, [[1, 2, 1], [3, 2, 3]])   # each drawable alone, never together
False
```

The `"signs"` entry holds the words as actually drawn — already relabelled by the permutation, with a sign on every letter — so it can be fed straight back in with `permute=False, respect_signs=True` to replay the drawing. Run `python src/coexistence.py` for a worked demonstration.

Note that, as with the single-word test, co-existence is **necessary but not sufficient**: nothing checks that the disjoint arcs can be joined up into a single closed loop.

### Demo (`src/demo.py`)

`demo.py` demonstrates the main functions in `searching.py` with concrete examples — showing how `evaluate`, `valid_assignment_of_signs`, and `valid_permutation_and_assignment_of_signs` behave on sample words. Run it with:

```bash
python src/demo.py
```

### GUI (`src/gui.py`)

A Tkinter GUI providing interactive access to the search functions:

```bash
python src/gui.py
```

It has four tabs: **Find Realisable**, **Check Subword**, **Check Unsigned Subword**, and **Minimal Invalid**. Long-running operations run in a background thread to keep the interface responsive, and results can optionally be saved to CSV.

### Testing (`src/test/`)

`src/test/subwords/` contains text files of words (one per line, in Python list notation), grouped by expected behaviour:

- `known_valid.txt` — words expected to return `True`
- `known_non_valid.txt` — words expected to return `False`
- `mostly_non_valid.txt` — a mixed set, mostly non-realisable
- `braid_orbit_braidlength{k}_rank{n}.txt` — auto-generated files (see below)

`test.py` runs `evaluate` over each file and prints a true/false tally:

```bash
cd src/test
python test.py
```

`braid_orbit.py` generates a subword file from the braid orbit of the generator $x_1$ under all reduced braid words up to a given length. Since every element of this orbit should be realisable, the generated file serves as a ground-truth test set where every word is expected to return `True`.

`test_coexistence.py` is a self-checking suite for `coexistence.py` — it needs no corpus and prints a pass/fail line per property:

```bash
cd src/test
python test_coexistence.py
```

It checks that one-word families reproduce the single-word functions in `searching.py` exactly, that co-existence does not depend on the order the words are drawn in, that every witness replays as a drawable family, that sub-families of a co-existing family co-exist, that multi-arc configurations satisfy the `regions.py` invariants, and that `forward_new_arc` reproduces the first-crossing rule on the initial state.

## Usage

```bash
# Launch the GUI
python src/gui.py
```

To use the search functions directly in an interactive Python session:

```python
>>> from src.searching import evaluate
>>> evaluate(3, [1, 2, -1])
True
>>> from src.coexistence import can_coexist
>>> can_coexist(3, [[1, 2, 1], [2, 3, 2]])
True
```
