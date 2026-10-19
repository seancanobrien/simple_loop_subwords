# Algorithm details

An orientation document for anyone picking up this codebase. It explains what the code
computes, how the state encoding works, and — in detail — what `regions.forward` is doing
geometrically, because that function is the whole engine and its index arithmetic is opaque
without the picture behind it.

This document is self-contained: the maths it relies on is stated where it is used, so it
can be read against the source alone. `README.md` covers usage.

There are no third-party dependencies. `main.py` loads everything into one namespace for an
interactive session, run from the repository root:

```bash
python3 -i main.py
```

```python
>>> can_exist([1, 2, 1, 3])
True
>>> demo()          # narrated walk-through of all three modules
>>> run_tests()     # all three test suites
```

If you are reading the code rather than running it, the order that makes sense is
`regions.py` (§3–§5), then `searching.py` (§6), then `coexistence.py` (§7).

---

## 1. The question being answered

Take the closed unit disk `D` with `n` punctures `p_1, …, p_n` on the real axis, and draw a
*generator line* from each `p_j` up to the boundary point `i`. A path through the disk spells a
word in the free group `F_n`: each time it crosses the generator line of `p_j` it records
`x_j` (crossing left-to-right) or `x_j^{-1}` (right-to-left).

The motivating problem is the dual Artin isomorphism problem. The orbit `Q = B_n · x_1` under
the braid group consists of words that all correspond to **simple** (embedded) loops. We want
to rule out words from appearing in `Q`, so we ask:

> **Given a word `w ∈ F_n`, can `w` be drawn as an embedded (non-self-crossing) arc in the
> punctured disk?**

If it cannot, `w` cannot be a subword of any element of `Q`.

Two consequences of asking about **subwords** rather than loops:

- The arc's **starting point is free** — it starts at an arbitrary interior point, not at the
  basepoint `-i`. This matters for the first-crossing case (§5.2).
- The arc's endpoint is likewise free; we simply stop when the word is exhausted.

Either end can instead be **pinned to the boundary**, by a `0` as the first or last letter of
the word. The elements of `Q` are loops based on the boundary, so `[0, …]` is the shape of a
prefix of one, `[…, 0]` of a suffix, and `[0, …, 0]` of a whole element. Pinning an end only
ever constrains, because a free end can always be pulled in off the boundary. §3.6 and
§5.5–§5.6 cover it.

The answer is **necessary but not sufficient** for membership in `Q`: the algorithm says
"drawable as an embedded arc", not "is a subword of a simple loop in the orbit". A `True`
result means "not ruled out".

---

## 2. The idea in one paragraph

Draw the arc one letter at a time. The arc drawn so far, together with the generator lines,
cuts the punctured disk into **regions**. Each generator line is cut into **segments** by the
places where the arc has crossed it. To contribute the next letter `x_j^{±1}`, the arc must
cross a segment of line `j` in the right direction, and that segment must be reachable — i.e.
it must lie on the boundary of the region the arc's tip is currently in. If no such segment is
available, that drawing attempt is dead. If several are available, we branch. The word is
drawable iff some branch survives to the end.

---

## 3. The encoding

### 3.1 Faces are signed integers

A segment has two sides. The **left face** of a segment gets a positive integer, and the
**right face** of the same segment gets its negative. So the signed integer `+s` and `-s` are
the two faces of one physical segment.

Crossing *from* face `+s` (i.e. approaching from the left) contributes a positive generator;
crossing from face `-s` contributes an inverse. Throughout the code, the variable named `seg`
is a **signed face**, and it is the face the arc crosses *from*.

### 3.2 `gen`: which generator a face contributes

`State.gen` is a tuple indexed by **absolute** segment id:

```
gen[0]        0: segment 0 is the boundary, which carries generator 0 (§3.6)
gen[k], k ≥ 1 the generator index carried by face +k
```

and `_gen(state, seg)` returns `gen[|seg|]` for `seg > 0`, `-gen[|seg|]` for `seg < 0`. Negative
keys are never stored, since `gen[-k] = -gen[+k]` always. Initially `gen[k] = k` for
`k = 0 … n`; every segment later cut off line `j` inherits `gen = j` (`_fresh_seg`), and every
piece cut off the boundary inherits `gen = 0`.

Write `S_{x_j}` for the set of faces carrying generator `j`, i.e. `{ s : _gen(s) = j }`.
Then `seg_possibilities_given_gen(state, j)` is the intersection of `S_{x_j}` with the current
region. Splitting a segment adds a face to the set it came from — the `S_x ← S_x ∪ {T}` step
referred to in §5.

### 3.3 Regions are cyclic tuples

`State.regions` is a tuple of regions; each region is a tuple of the faces on its boundary,
**read clockwise**. Generator faces and boundary faces (§3.6) are both listed; only the pieces
of the drawn path that also bound the region are implicit, not stored.

Region tuples are **cyclic**: `(-5, 6)` and `(6, -5)` denote the same region, so a region
written at a different rotation than the code produces is the same region, not a discrepancy.

### 3.4 The end-region convention — the single most important detail

**While an arc is in progress, `regions[0]` is the region containing its tip, and the tip
sits at the junction between the last entry and the first entry of that tuple** (i.e. "just
before index 0", as `state_str` puts it).

Every branch of `forward` that leaves a tip finishes by rotating the new end-region so that
this holds. Once you know this, the otherwise-mysterious slicing-and-concatenation in
`forward` reads directly as "cut the boundary cycle here, and re-anchor it there". The one
branch that leaves no tip is ending on the boundary (§5.6), which finishes the arc; then
`arc_in_progress` is `False` and `regions[0]` is not special.

### 3.5 `State`

```python
class State(NamedTuple):
    n:                   int    # number of punctures
    regions:             tuple[tuple[int, ...], ...]
    gen:                 tuple[int, ...]
    next_seg:            int    # next fresh positive segment id
    arc_in_progress:     bool   # is there a tip in regions[0]?
```

`arc_in_progress` is `False` in the uncut disk and after an arc ends on the boundary; either
kind of start (§5.2, §5.5) sets it `True`. An arc that ends at a free point leaves it `True`:
the search simply stops, or starts the next arc with `forward_new_arc`.

It is a `NamedTuple`, so states are immutable, structurally comparable and **hashable** — which
is what lets the search layer keep a `set` of states and deduplicate for free. Updates go
through `_replace`; there is no deep copying anywhere.

`make_state(n)` gives the uncut disk:

```
regions  = ((0, 1, -1, 2, -2, …, n, -n),)
gen      = (0, 1, 2, …, n)
next_seg = n + 1
```

The single region is the disk cut open along all `n` generator lines: walking clockwise you go
along the edge of the disk (`0`) to the top of line 1, down its left face (`+1`), round `p_1`,
back up its right face (`-1`), across to line 2, and so on, until `-n` brings you back to the
edge.

### 3.6 The boundary is generator 0

All the generator lines meet the edge of the disk at the one point `i`, so the rest of the
edge is a single arc, running clockwise from the top of line `n` round to the top of line `1`.
It is treated as **one more line, carrying generator 0**: it starts as segment `0`, and it is
cut into segments by the arc ends that land on it, each new piece taking a fresh id from
`next_seg` and inheriting `gen = 0`. So the boundary faces are exactly the faces with
`gen 0`, which `_is_boundary` tests.

It differs from a generator line in two ways:

- **One face per segment.** The edge has only one side, the inside of the disk, so a boundary
  segment has a single face, written with its non-negative id: face `0` is `+0 = -0`. There is
  no partner face, and boundary faces never appear negated.
- **Never crossed.** An arc can start on a boundary face (§5.5) or end on one (§5.6), but it
  never passes through: there is nothing on the other side.

Because the letter `0` picks out boundary faces exactly as the letter `j` picks out the faces of
line `j`, the boundary needs no special handling outside `regions.py`:
`seg_possibilities_given_gen(state, 0)` lists the boundary faces where the arc could end, and
`new_arc_possibilities(state, 0)` those where a new arc could start.

---

## 4. Invariants

These hold for every reachable state and are the best way to test changes to `forward`:

1. **Each face appears exactly once** across all regions. A face is one side of one
   sub-segment, so it borders exactly one region-slot.
2. **Generator faces come in pairs**: `+k` present ⟺ `-k` present, for every generator
   segment `k`. Boundary faces are unpaired and never negative (§3.6).
3. **One new segment per crossing, and one per end on the boundary**: after `c` crossings and
   `b` arc ends on the boundary there are `n + c` generator segments, hence `2(n + c)`
   generator faces, and `1 + b` boundary segments. This holds for both kinds of crossing.
4. **Region count**: 1 initially. An ordinary crossing adds `+1`, and so does ending on the
   boundary (§5.6), since both cut a region along a chord. Starting an arc adds `0`, whether at a
   free point, because a slit does not disconnect (§5.2), or on the boundary, because nothing is
   cut (§5.5). Drawing one free arc of length `c` therefore leaves `c` regions; drawing `k` arcs
   making `c` crossings between them, with `b` of their ends on the boundary, leaves
   `c - k + b + 1`.
5. While an arc is in progress, `regions[0]` is the end-region, anchored as in §3.4.

---

## 5. `forward(state, seg)` — the state update

Signature: cross the face `seg`, which must be present in `regions[0]`; return the new `State`
(`ValueError` otherwise). If `seg` is a boundary face, the arc does not cross it but starts
(§5.5) or ends (§5.6) on it.

### 5.1 The common recipe

Let `region = regions[0]`, `i = region.index(seg)`, `seg_sgn = sign(seg)`, and let `T` be a
freshly allocated segment id (`_fresh_seg`, inheriting `gen[|seg|]`).

The arc runs from the tip (just before index 0) to a point `q` in the interior of the segment at
index `i`, and passes through to the other side. Two things happen:

- **The segment is split at `q`.** Its `+` face becomes two faces and its `-` face becomes two
  faces. One piece of each keeps the old id, the other pair gets `±T`. Because
  `gen[T] = gen[|seg|]`, both pieces contribute the same generator as before — this is the
  `S_x ← S_x ∪ {T}` step of §3.2.
- **The region is cut** along the arc, into the part clockwise-before `q` and the part
  clockwise-after `q`.

The arc emerges on the opposite face `-seg`. Where `-seg` currently lives decides everything:

| situation | code branch |
|---|---|
| the arc is *starting* here (`arc_in_progress` is `False`) | new arc, §5.2, or on the boundary, §5.5 |
| `seg` is a boundary face | the arc ends on it, §5.6 |
| `-seg` in the end-region, **after** `seg` (`i < pair_pos`) | Case A, first sub-case (§5.3) |
| `-seg` in the end-region, **before** `seg` (`i > pair_pos`) | Case A, second sub-case (§5.3) |
| `-seg` in some other region | Case B (§5.4) |

The rows are tried in that order, so the partner face is only ever looked up for a generator
face. `_find_signed(regions, -seg)` locates it, returning `(region_index, position)`; it is a
linear scan over every face, so it is `O(n + c)` per step.

The split always uses the same convention, in all four branches that cross a generator line:

```
crossed face  seg   splits clockwise into ( seg_sgn·T,  seg )
partner face -seg   splits clockwise into ( -seg, -seg_sgn·T )
```

and the region owning the partner face is rotated to begin at `-seg_sgn·T`, because the arc tip
lands exactly at that junction.

### 5.2 Starting an arc — why the region does *not* split

`forward_new_arc(state, seg, region_idx)` begins a fresh arc at a free interior point of
`regions[region_idx]` and crosses `seg`. `forward` delegates to it (with `region_idx = 0`)
whenever `arc_in_progress` is `False`. If `seg` is a boundary face, `forward_new_arc` starts the
arc *on* it instead (§5.5); what follows is the free start.

It produces the **same number of regions**, not one more. The reason is the free starting point
(§1): the arc begins at an interior point, so cutting along it is a **slit**, not a chord — you
can walk around its free tip. Cutting a disk along a slit leaves a disk. Only the crossed segment
is split:

```python
cut   = region[:i] + (seg_sgn * T, seg) + region[i + 1:]   # slit between the two pieces
split = partner[:pair_pos] + (-seg, -seg_sgn * T) + partner[pair_pos + 1:]
end   = split[pair_pos + 1:] + split[:pair_pos + 1]        # anchor on -seg_sgn * T
```

The partner face may be in the starting region or in a different one; both work, because
`_find_signed` is applied after the first insertion. The `region_idx` parameter and the
different-region case only matter for co-existence (§7) — for a single word there is one region
and no partner elsewhere.

For `n = 4`, crossing `+1`: `(0,1,-1,2,-2,3,-3,4,-4)` → `(-5, 2,-2,3,-3,4,-4,0, 5, 1, -1)`,
the first step of the worked example in §5.7. Reading it clockwise from the edge of the disk:
`0` brings you to the top of line 1, then `5` is the upper piece of line 1 (from `i` down to
`q`), then the slit, then `1` (from `q` down to `p_1`), round the puncture, back up `-1` to `q`,
then the arc tip, then `-5`.

Applied to the pristine region this is algebraically identical to the older special-cased
formulas it replaced (`(-T,) + region[i+2:] + region[:i] + (T,) + region[i:i+2]` for positive
`seg`, `(T, -T) + region[i:] + region[:i]` for negative), which relied on `-seg` sitting at
`i ± 1`. `test/test_coexistence.py` pins that equivalence.

### 5.3 Case A — the partner face is in the same region

The arc leaves the region and comes straight back into it. The cut is a genuine chord, so the
region splits in two; the tip lands in whichever half contains `-seg`.

**Sub-case `i < pair_pos`** (partner after the crossed face):

```python
left  = region[:i] + (seg_sgn * T,)
right = (-seg_sgn * T,) + region[pair_pos + 1:] + region[i:pair_pos + 1]
new_regions = (right,) + state.regions[1:] + (left,)
```

`left` is the part of the boundary clockwise-before `q`, closed off by the new piece `+T`.
`right` is everything from `seg` onwards, with `-seg` split into `(-seg, -T)`, rotated so it
begins at `-T` — because the tip is exactly at the `-seg | -T` junction. `right` contains
`-seg`, so `right` becomes the new `regions[0]`.

**Sub-case `i > pair_pos`** (partner before the crossed face):

```python
left  = (-seg_sgn * T,) + region[pair_pos + 1:i] + (seg_sgn * T,) + region[:pair_pos + 1]
right = region[i:]
new_regions = (left,) + state.regions[1:] + (right,)
```

Here `-seg` lies in the *before* half, so that half — `left` — becomes the new end-region,
again rotated to start at `-T`. Reading `left` from `+T` instead: `T, region[0..pair_pos], -T,
region[pair_pos+1..i-1]` — so as written it has the shape `(-T, …, T, …, -j)`. `right` is
everything from the crossed face onwards, of shape `(j, …)`; the piece of the split segment that
keeps the id `seg` stays at its head.

### 5.4 Case B — the partner face is in a different region

The arc leaves the current region and lands in a previously cut-off one.

```python
r_left      = region[:i] + (seg_sgn * T,)          # end-region splits …
r_right     = region[i:]                           # … into these two
r_prime_new = (-seg_sgn * T,) + r_prime[pair_pos + 1:] + r_prime[:pair_pos + 1]
new_regions = (r_prime_new,) + remaining + (r_left, r_right)
```

The old end-region is cut in two by the arc (`r_left`, `r_right`); neither contains the tip. The
region `r'` that owns `-seg` is not cut at all — it only has its boundary relabelled, `-seg`
becoming `(-seg, -T)` — and rotated to start at `-T`, so it becomes the new `regions[0]`. Net
region count `+1`, as required by invariant 4.

### 5.5 Starting on the boundary — nothing is crossed

`forward_new_arc(state, b, region_idx)` with `b` a boundary face starts the arc **on** `b`
(`_start_on_boundary`). The arc does not cross anything yet: its start point splits `b`, and
the tip waits there.

```python
split = region[:i + 1] + (T,) + region[i + 1:]      # b splits clockwise into (b, T)
end   = split[i + 1:] + split[:i + 1]               # anchor on T, the tip just before it
```

This is the partner-face rule of §5.1 with the crossing taken away: the tip sits at the
junction of the two pieces, so the region is rotated to begin at the second and becomes the
new `regions[0]`. No region is cut, so the count is unchanged, and `arc_in_progress` becomes
`True`.

The difference from a free start shows up at the next letter. After §5.2 the arc's tail is a
dangling slit, but here it is attached to the edge of the disk, so the first crossing is made
by `forward` as an **ordinary chord** from the tip — Case A or B — and adds a region where a
free start's first crossing does not. That is the precise sense in which pinning an end
constrains: a slit leaves room to walk round the free end, and a chord does not. `[-1, 2]` is
drawable, for instance, because its free start lets the arc wrap round `p_1`; `[0, -1, 2]` is
not.

### 5.6 Ending on the boundary — Case B with nowhere to land

`forward(state, b)` with `b` a boundary face of the end-region, while an arc is in progress,
ends the arc on `b` (`_end_on_boundary`). The arc runs from the tip to a point of `b` and
stops:

```python
left  = region[:i] + (T,)                 # b splits clockwise into (T, b)
right = region[i:]
new_regions = state.regions[1:] + (left, right)
```

The run from the tip to `b` is a chord, so the end-region splits exactly as in Case B — into
`region[:i]` closed off by the new piece, and `region[i:]` from `b` onwards (§9) — but there is
no region beyond the boundary to take the tip. The arc is finished: neither half is an
end-region, both go to the back, and `arc_in_progress` becomes `False`. Net region count `+1`.

Starting and ending on the boundary are written by different code, so they check each other:
running an arc backwards reverses its word, inverts every letter and swaps its ends, so
`[0] + w` must be drawable exactly when `[-x for x in reversed(w)] + [0]` is.
`test/test_boundary.py` checks this.

`n = 2`, the loop `[0, 1, 0]` round `p_1`, based on the boundary:

```
init      ((0, 1, -1, 2, -2),)
start 0   ((3, 1, -1, 2, -2, 0),)                         §5.5, tip between 0 and 3
x1        ((-4, 2, -2, 0, 1, -1), (3, 4))                 Case A, i < pair_pos
end 0     ((3, 4), (-4, 2, -2, 5), (0, 1, -1))            §5.6
```

Three regions: `c - k + b + 1 = 1 - 1 + 2 + 1`. The loop's inside is `(0, 1, -1)`, holding
`p_1` and the lower piece of its line; its outside has been cut in two by the upper piece of
line 1, `(3, 4)` on the left and `(-4, 2, -2, 5)` on the right.

### 5.7 Worked example

`n = 4`, word `x_1 x_2 x_4^{-1}`:

```
init    ((0, 1, -1, 2, -2, 3, -3, 4, -4),)                              gen (0,1,2,3,4)
x1      ((-5, 2, -2, 3, -3, 4, -4, 0, 5, 1, -1),)                       gen (…,5→1)   first crossing
x2      ((-6, 3, -3, 4, -4, 0, 5, 1, -1, 2, -2), (-5, 6))               gen (…,6→2)   Case A, i < pair_pos
x4^-1   ((7, -7, -6, 3, -3, 4), (-5, 6), (-4, 0, 5, 1, -1, 2, -2))      gen (…,7→4)   Case A, i > pair_pos
```

After this, `gen_possibilities(state) == [-4, -3, -2, 3, 4]`: the arc's tip is in the small
region `(7, -7, -6, 3, -3, 4)`, so the only letters it can produce next are `x_3^{±1}`,
`x_4`, `x_2^{-1}` (via face `-6`) and `x_4^{-1}` (via `-7`). Any word demanding, say, `x_1`
at this point is not drawable along this branch. Nor is `0` among them: the boundary is in
another region, so `[1, 2, -4, 0]` is not drawable along this branch either.

---

## 6. Branching, and the search layer (`searching.py`)

A letter `x_j^{±1}` may be produced by crossing several different faces of line `j` that all lie
on the current region's boundary. The choice matters, so the algorithm explores all of them.

The implementation does this as a **breadth-first sweep over a set of states**, one letter at a
time, rather than as a backtracking DFS:

```python
def _advance(states, letter):
    return {forward(s, seg) for s in states for seg in seg_possibilities_given_gen(s, letter)}
```

- The set is the whole frontier of live drawings after reading the prefix so far.
- Dead branches drop out automatically (a state with no admissible face contributes nothing) —
  this is the "pruning is automatic" comment in the source.
- Identical states arising from different choices are merged by the `set`, since `State` is a
  hashable `NamedTuple`.
- An empty frontier means *no* drawing survives ⇒ the word is not drawable.

Note the dedup is **structural, not geometric**: two states describing the same picture but with
different segment ids, or with a non-end region written at a different rotation, will not merge.
Anchoring the end-region (§3.4) is what makes the common case merge.

### 6.1 Public entry points

| function | meaning |
|---|---|
| `can_exist(word, n=None, permute=True, respect_signs=False)` | `True` iff the word is drawable |
| `can_exist_witness(word, n=None, permute=True, respect_signs=False)` | `{"permutation": …, "signs": …}` or `None` |

Deliberately the same shape as the co-existence pair in §7.5 — a one-word family asks exactly
this question, and `test_coexistence.py` checks that the two layers agree under all four flag
combinations.

The flags decide how literally the input is read:

- **`respect_signs=True`** takes the word exactly as written. Under the default `False` only the
  magnitudes matter and every position is free to become `x_j` or `x_j^{-1}`.
- **`permute=True`** (the default) tries every relabelling of the symbols present, so the word is
  read as a shape rather than as a particular labelling; `permute=False` fixes it as given.

Sign choice is **fused into the sweep** rather than enumerated on top of it: at a free position
the frontier advances by both `+l` and `-l` and the two results are merged, so a single sweep
covers every assignment, deduplicated across them. This is the same mechanism as §7.3, and
`_sweep` takes the same `signs` argument in which `0` means "free". `can_exist_witness` recovers
a specific assignment by pinning one sign at a time and re-sweeping — exact, because a merged
sweep is the union over every completion of the pinned prefix, so a sign can be committed to
without looking ahead, and at most `2 × len(word)` sweeps.

The permutation loop sits outside the sweep and permutes `sorted({|x| : x in word} - {0})` —
the **unsigned** symbols — so signed and unsigned input are relabelled alike.

`"signs"` in a witness holds the word **as drawn**: relabelled by the permutation, one sign per
letter, so it can be fed straight back in with `permute=False, respect_signs=True` to replay the
drawing. A witness is `None` exactly when the corresponding boolean is `False`.

**The boundary letter.** A `0` at either end of the word needs no step of its own, because
`regions.py` gives the boundary generator 0 (§3.6). The sweep advances by `0` like any other
letter: a leading `0` reaches `forward_new_arc` through `forward`, which starts the arc on the
boundary, and a trailing `0` reaches `forward` through `seg_possibilities_given_gen(s, 0)`,
which ends it there. Only the flags need to know about it. The boundary has no sign, so `0` is
advanced once rather than as `±0` (the options are a set, and `{0, -0}` is `{0}`), and
`_recover_signs` skips it. It is not a puncture, so it is never relabelled and never appears in
the witness's `"permutation"`.

### 6.2 Word validation

`_validate_word(word, rank=None, check_for_squares=True)` is the one gate on the public entry
points, and `coexistence.py` reuses it per word. It rejects

- anything that is not a non-empty list of integers,
- a `0` anywhere but the first or last position, and a word with no letter but `0` (so `[0]`
  and `[0, 0]` are out),
- letters outside `±1 … ±rank`,
- non-reduced words (`w[i] == -w[i+1]`),
- squares (`w[i] == w[i+1]`), unless `check_for_squares=False`.

`rank=None` checks the shape of the word without imposing an upper bound on its symbols, which
is what lets the rank itself be optional (§6.3).

The square rule is a scope decision rather than a limitation — see §9. Nothing in the
repository passes `check_for_squares=False`; the parameter exists so that a caller studying
powers deliberately can switch the rule off.

### 6.3 The optional rank

`n` is the number of punctures in the disk, and it defaults to `None`. `_resolve_rank` reads
that as *the smallest rank that admits the word*, `max |letter|`:

```python
def _resolve_rank(word, n):
    _validate_word(word, n)
    return max(abs(x) for x in word) if n is None else n
```

Any larger rank gives the same answer (§7.4), so the default is a free choice rather than a
guess. Passing `n` explicitly matters only when a batch of words is to be compared at one fixed
rank, as `test/test_corpus.py` does with `rank=15`. `coexistence.py` has the same default via
`_resolve_family`, which takes the largest `|letter|` across the whole family.

---

## 7. Co-existence of several subwords (`coexistence.py`)

### 7.1 The question

Given a family `w_1, …, w_k`, can they all be drawn **at once**, as pairwise disjoint embedded
arcs in one disk? If they all occur as subwords of a single simple loop, their arcs are disjoint
sub-arcs of one embedded loop — so a `False` here rules the family out of every element of the
orbit `Q`. Like the single-word test it is **necessary, not sufficient**: nothing checks that the
arcs can be joined up into one closed loop.

### 7.2 How it works

Draw the words one after another into the same configuration. Once `w_1` is drawn the disk is cut
into regions; `w_2` then starts a fresh arc at a free interior point of **any one of them**, via
`forward_new_arc(state, seg, region_idx)`, and continues with ordinary crossings. Because a
crossing is only permitted through a face bounding the current region, an arc drawn this way is
automatically disjoint from everything already drawn — the disjointness constraint needs no
separate enforcement.

Two frontier steps, mirroring `searching._advance`:

```python
def _advance(states, letter):          # continue the arc in progress
    return {forward(s, seg) for s in states for seg in seg_possibilities_given_gen(s, letter)}

def _advance_new_arc(states, letter):  # start a fresh arc, in ANY region
    return {forward_new_arc(s, seg, ri) for s in states for ri, seg in new_arc_possibilities(s, letter)}
```

`new_arc_possibilities` scans every region rather than just `regions[0]`, which is the one place
the co-existence search fans out more widely than the single-word search.

Words may start or end on the boundary too, and **any number of them** may. A leading `0` goes
through `_advance_new_arc` like any first letter, and `new_arc_possibilities(s, 0)` offers every
boundary face of every region, so the arc can start on whichever piece of the edge is reachable;
a trailing `0` goes through `_advance`, ending the arc on a boundary face of the end-region.
Nothing else changes. When at most one word starts with `0` and at most one ends with `0` — a
prefix and a suffix of one loop — this agrees with pinning both ends to the basepoint `-i`: the
edge has nothing else on it, so the two ends can always be slid together.

### 7.3 Signs fuse into the sweep

Sign choice does **not** need a separate enumeration layer. At an unsigned letter the frontier
advances by both `+l` and `-l` and the two results are merged, so the frontier is exactly "every
configuration reachable under every valid sign assignment" — deduplicated across assignments
rather than kept as `2^|w|` separate frontiers. `searching._sweep` does the same thing for a
single word (§6.1). This is what makes handing a configuration from
one word to the next cheap, and it is the reason `_reachable` takes a `signs` argument where `0`
means "free":

```python
options = (magnitude, -magnitude) if fixed == 0 else (fixed * magnitude,)
step    = _advance_new_arc if pos == 0 else _advance
states  = set().union(*(step(states, option) for option in options))
```

The cost is that a plain sweep no longer knows *which* signs worked. `_recover_signs` gets a
witness back by pinning one sign at a time and re-sweeping, keeping the family feasible at each
step — exact, because a merged sweep is the union over every completion of the pinned prefix, so
a sign can be committed to without looking ahead — and at most `2 × (total length)` sweeps.

### 7.4 The permutation layer

One permutation is applied to **all** words at once — they share a disk, so their labellings
cannot be chosen independently — and it sits outside everything else.

Permuting only the symbols actually present is complete. Drawability depends solely on the
*relative order* of the punctures used: a generator line runs from a puncture to the boundary, so
it is a slit rather than a separating chord, and an arc can always pass beneath an unused puncture
without recording a letter. Drawability is therefore invariant under every order-preserving
relabelling (`{1,2,3} → {1,3,5}`, `{2,3,7}`, `{1,4,5}`, …), so mapping symbols onto a wider or
gappier subset of `{1..n}` can never reach a configuration a permutation misses.

The same fact is why the answer at rank `max |letter|` and at any `k` above it agree, which is
what makes the rank safe to default (§6.3) and lets `test/test_corpus.py` fix `rank=15` for
every corpus. `test_coexistence.py` checks the two agree directly, for both layers.

### 7.5 API

| function | meaning |
|---|---|
| `can_coexist(words, n=None, permute=True, respect_signs=False)` | `True` iff the family can be drawn simultaneously |
| `coexist_witness(words, n=None, permute=True, respect_signs=False)` | `{"permutation": …, "signs": […]}` or `None` |

Same signature as the single-word pair in §6.1, with a list of words in place of the word: the
rank is optional and defaults to the largest `|letter|` in the family, `permute=False` fixes the
labelling, and `respect_signs=True` takes the given signs literally instead of searching over
them. A one-word family is exactly the single-word question, and `test_coexistence.py` checks
that `can_coexist([w], …)` and `can_exist(w, …)` agree under all four flag combinations, over
504 words. The two are independently written implementations, which is what gives that check its
value.

`"signs"` holds the words **as drawn** — already relabelled by the permutation, one sign per
letter — so it can be fed straight back in with `permute=False, respect_signs=True` to replay
the drawing. Cost in practice is milliseconds for families of a few words of length 4–6.

### 7.6 Properties worth knowing (all verified in `test_coexistence.py`)

- **Order independence.** `can_coexist([w1, w2]) == can_coexist([w2, w1])`. Disjointness is
  symmetric, so the drawing order is an implementation detail. Checked over 2000 pairs.
- **Monotone under sub-families.** If a family co-exists, so does every sub-family.
- **Strictly stronger than drawing words separately.** `[1,2,1]` and `[3,2,3]` are each drawable
  alone, but never together, under any permutation and any signs; so are `[1,2,1]` and
  `[2,3,2,3]`. Both pairs are pinned as regression cases, so the test genuinely discriminates.
- **The boundary bites hardest here** (verified in `test_boundary.py`). A loop based on the
  boundary cuts the disk in two, and every other word must fit on one side of it: `[1]` and
  `[2,1,2]` co-exist, but `[0,1,0]` and `[2,1,2]` do not, since once `[2,1,2]` crosses the
  upper piece of line 1 it is cut off from line 2. Likewise `[1,2,1]` and `[2,1,2]` co-exist,
  but not as a prefix `[0,1,2,1]` and a suffix `[2,1,2,0]`. Order independence and rank
  independence hold with boundary words too.

---

## 8. File map

| path | role |
|---|---|
| `main.py` | the entry point: imports the three modules into one namespace for `python3 -i main.py`, and defines `demo()` and `run_tests()` |
| `regions.py` | the engine: `State`, `make_state`, `forward`, `forward_new_arc`, `seg_possibilities_given_gen`, `gen_possibilities`, `new_arc_possibilities`, `state_str`; the boundary steps `_start_on_boundary` and `_end_on_boundary` (§5.5–§5.6) |
| `searching.py` | frontier search and the single-word API (§6): `can_exist`, `can_exist_witness` |
| `coexistence.py` | multi-word co-existence (§7): `can_coexist`, `coexist_witness` |
| `test/test_corpus.py` | runs `can_exist` over each corpus, each word taken as written, and checks the tally |
| `test/test_coexistence.py` | self-checking suite for §7 — agreement with `searching.py`, witness replay, rank invariance, order independence, invariants |
| `test/test_boundary.py` | self-checking suite for words with a `0` at either end — braid-orbit loops and suffixes as ground truth, start against end under reversal, the §4 counts, and the §7 properties again |
| `test/braid_orbit.py` | generates a ground-truth corpus: the orbit of `[1]` under braid words up to a given length — every word in it *should* come out `True` |
| `test/subwords/*.txt` | corpora, one Python list per line |

The modules import each other by bare name (`from regions import ...`), so they are run from
the repository root. The test files prepend the root to `sys.path` so they also work when
run directly from inside `test/`; `test_boundary.py` also borrows helpers from
`test_coexistence.py`.

`test/subwords/braid_orbit_braidlength7_rank7.txt` (6585 words) is the most useful regression
set: it is derived from the braid action, so every line is drawable by construction, and any
`False` there is a genuine bug. `known_valid.txt` / `known_non_valid.txt` are small
hand-curated sets; `mostly_non_valid.txt` is a large mixed set with no per-line ground truth,
so `test_corpus.py` reports it as a tally only.

### 8.1 What this release dropped

This repository is a trimmed version of a larger working repository. If you are comparing
against that one, the differences are:

- **Enumeration and reporting helpers**, which lived below a "Simi function implementations"
  banner in `searching.py`: `count_realisable`, `collect_realisable`, `count_minimal_invalid`,
  `collect_minimal_invalid`, their recursive workers, and the CSV output they wrote.
- **`gui.py`**, a Tkinter front-end with four tabs and a background worker thread. It had no
  algorithmic content.
- **Four module-level flags** in `searching.py` — `IGNORE_POWERS`, `PRODUCE_OUTPUT`,
  `IGNORE_SIGNS`, `USE_MULTIPROCESSING` — which the GUI overwrote at run time. Only the first
  was ever read; it survives as the `check_for_squares` parameter of `_validate_word` (§6.2),
  with the same default.
- **`demo.py`** and the `__main__` demo block in `coexistence.py`, both folded into the demo
  functions in `main.py`.
- **`tex/`**, a LaTeX write-up of the maths. It contained no code, and it is not maintained
  any more; §3–§5 here are the surviving description of the encoding and the case analysis.

One thing was reshaped rather than dropped. The three single-word entry points `evaluate`,
`valid_assignment_of_signs` and `valid_permutation_and_assignment_of_signs` are gone, replaced
by `can_exist` and `can_exist_witness` (§6.1), which take the same flags as the co-existence
pair so that all four entry points read alike. Each old function is one flag combination of the
new pair:

| old call | new call |
|---|---|
| `evaluate(n, w)` | `can_exist(w, n, permute=False, respect_signs=True)` |
| `valid_assignment_of_signs(n, w)` | `can_exist_witness(w, n, permute=False)` |
| `valid_permutation_and_assignment_of_signs(n, w)` | `can_exist_witness(w, n)` |

The two witness rows return a dict where the old functions returned a bare word; the assignment
is its `"signs"` entry, and the result is `None` in exactly the same cases as before.

The answers are unchanged: the new pair was checked against the old implementation over 2,040
signed and 1,452 unsigned words with no disagreement. Two details did improve. The permutation
now acts on the unsigned symbols, where `valid_permutation_and_assignment_of_signs` permuted
`sorted(set(word))` and so treated `1` and `-1` as unrelated symbols on mixed-sign input; and
signs are now recovered by pinning rather than by keeping `2^len(word)` sign paths distinct. A
returned witness may therefore differ from the old one — any valid assignment is a valid answer.

The engine (`regions.py`), the search itself and the co-existence layer (`coexistence.py`) are
otherwise unchanged, so results from either repository are comparable. The one later addition
is the boundary (§3.6, §5.5–§5.6): every region tuple now carries its boundary faces, and
`first_crossing_done` is now `arc_in_progress`, but every word without a `0` gets exactly the
answer it got before — all four corpora give identical tallies.

---

## 9. Known quirks and traps

**Squares are "drawable", by design.** The algorithm will happily draw `x_j x_j`: you can spiral
an ever-growing arc around a single puncture. Such words do not arise as subwords of reduced
words in the setting of interest, for independent and provable reasons, so they are excluded
rather than handled — that is what the `check_for_squares` default is for, and `_validate_word`
raises on them (§6.2). Do not "fix" a `True` answer on a square.

**The two halves of a cut end-region are `region[:i] + new face` and `region[i:]`.** Both Case A
sub-cases and Case B slice the old end-region at the crossed face `i`; what differs between them
is only which half absorbs the `-T` relabelling and becomes the new `regions[0]`. Ending on the
boundary (§5.6) slices the same way, and neither half becomes `regions[0]`. If you are
modifying `forward`, that symmetry is the sanity check — a half that starts anywhere other than
the crossed face is duplicating or dropping boundary.

**Face `0` has no sign, and `-0 == 0`.** The original boundary face is `0`, so `seg_sgn`,
`_find_signed(-seg)` and every other piece of sign arithmetic would quietly treat it as its own
partner. That is why `forward` and `forward_new_arc` test `_is_boundary` before doing anything
else with a face, and why a boundary face is recognised by `gen == 0` rather than by its sign
or id. The later boundary pieces have positive ids, but are just as unsigned: `-T` is never a
face.

**`seg` is a face, not a segment id.** `forward(state, 2)` and `forward(state, -2)` are different
moves on the same physical segment. `seg_possibilities_given_gen` returns faces.

**Region tuples are cyclic** — never compare them with `==` to decide whether two regions are the
same; only `regions[0]` has a canonical rotation.

**`gen` is indexed by absolute value** and is append-only; `gen[0] = 0` is the boundary, so
segment id `k` lands at index `k`.

**Rank is a property of the disk, not of the word.** `n` is the number of punctures, never a
word length, and it goes in the disk regardless of which generators the word actually uses.
Extra punctures are never a help or a hindrance (§7.4), which is why `n` can default to the
smallest rank admitting the input (§6.3) and why `test/test_corpus.py` can fix `rank=15` across
corpora of different widths. An explicit `n` below `max |letter|` is rejected by
`_validate_word`.

**Performance shape.** Cost per letter is `|frontier| × (choices) × O(total faces)`; the
frontier is the thing that explodes. One sweep is cheap, and searching over signs adds no
sweeps at all, because sign choice is fused into the frontier rather than enumerated on top of
it (§6.1). The expensive flag is the default `permute=True`, which runs the whole search once
per permutation of the symbols present — `k!` of them for `k` distinct symbols. Pass
`permute=False` when the labelling is meant as given: that is what lets `test/test_corpus.py`
sweep all 16,385 corpus words in about two seconds. Recovering a witness costs at most
`2 × len(word)` sweeps per permutation.

**Argument order differs between layers.** The four public entry points take the word or words
first and the optional rank second — `can_exist(word, n)`, `can_coexist(words, n)` — while the
internal sweeps take the rank first, `_sweep(n, word, signs)` and `_reachable(n, words, signs)`,
as the `regions` functions take the state first.
