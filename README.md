# Subwords of simple loops in the free group

Code for determining which words in the free group can appear as subwords of simple loops
in a punctured disk.

Joint work with:
- [Simi Hellsten](https://sites.google.com/view/simihellsten)
- [Alicja Pietrzak](https://sites.google.com/view/alicja-pietrzak/home)
- [Lorna Richardson](https://sites.google.com/view/lornarichardson/home)
- [Susanna Terron](https://sites.google.com/view/susannaterron)

## Background

Consider a closed unit disk in $\mathbb{C}$ with $n$ punctures on the real axis, with generator
lines drawn from each puncture to a fixed boundary point at $+i$. These generator lines are
labelled $\lbrace 1,\ldots,n \rbrace$ according to this left to right positioning on the real
line. A path traversing a loop in the disk accumulates a word in the free group $F_n$ by
recording which generator lines it crosses and in which direction. The central question is:
which words can arise as subwords of simple loops. We use the term *simple words* to refer to
all words in $F_n$ which correspond to simple loops in this way.

The algorithm answers a necessary condition for membership: it decides whether a word can be
drawn as an embedded (non-self-crossing) arc in the punctured disk. A word that cannot be drawn
cannot be a subword of any simple word. A positive answer means only "not ruled out".

Each end of the arc is either free, at an interior point, or on the boundary of the disk. A `0`
as the first or last letter of a word puts that end on the boundary, so `[0, 1, 2, -1, 0]` asks
for $x_1 x_2 x_1^{-1}$ drawn from the boundary back to it. Simple words are loops based on the
boundary, so `[0, …]` has the shape of a prefix of one, `[…, 0]` of a suffix, and `[0, …, 0]` of
a whole simple word.

- [How the algorithm works](docs/algorithm.md), with diagrams
- [How the code implements it](docs/implementation.md)
- [Testing](test/README.md)

## Requirements

Python 3.10 or later. No third-party dependencies.

## Quick start

```bash
python3 -i main.py
```

This loads everything into one namespace and prints a summary of what is available:

```python
>>> can_exist([1, 2, 1, 3])
True
>>> can_coexist([[1, 2, 1], [2, 3, 2]])
True
>>> can_exist([0, 1, 2, -1, 0])
True
>>> demo()                # narrated walk-through
>>> run_tests()           # all three test suites
```

Words are lists of integers, with $x_j$ written as `j` and its inverse as `-j`, so
$x_1 x_2 x_1^{-1}$ is `[1, 2, -1]`. A `0` may be the first or last letter, or both, and nowhere
else, and a word needs at least one other letter. `demo_regions()`, `demo_searching()` and
`demo_coexistence()` run one part of the walk-through each.

## Interface

Two functions for a single word and two for a family, all with the same signature:

```python
can_exist(word,          n=None, permute=True, respect_signs=False)  -> bool
can_exist_witness(word,  n=None, permute=True, respect_signs=False)  -> dict | None

can_coexist(words,       n=None, permute=True, respect_signs=False)  -> bool
coexist_witness(words,   n=None, permute=True, respect_signs=False)  -> dict | None
```

`can_coexist` asks whether the words can be drawn **at once**, as disjoint arcs in one disk,
as subwords of one simple word must be.

- **`n`**: the number of punctures. Defaults to `max |letter|`; a larger rank never changes the
  answer. Pass it to compare a batch of words at one rank.
- **`permute`**: try every relabelling of the symbols present, reading the input as a shape.
  Costs `(number of symbols)!` sweeps; pass `False` to fix the labelling as given. A family
  shares one relabelling.
- **`respect_signs`**: off by default, so each letter may be drawn as $x_j$ or $x_j^{-1}$. Pass
  `True` to take the signs as written.

Neither flag touches a `0`. A witness is the drawing found, or `None` exactly when the boolean
is `False`:

```python
>>> can_exist([1, 2, 1, 3], permute=False, respect_signs=True)
False
>>> can_exist_witness([1, 2, 1, 3], permute=False)
{'permutation': {1: 1, 2: 2, 3: 3}, 'signs': [1, 2, -1, 3]}
>>> coexist_witness([[1, 2, 1], [2, 3, 2]])
{'permutation': {1: 1, 2: 2, 3: 3}, 'signs': [[1, 2, 1], [2, 3, -2]]}
```

`"signs"` is the input as drawn, relabelled and with a sign on every letter, so it replays with
`permute=False, respect_signs=True`.
