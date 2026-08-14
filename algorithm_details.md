# Algorithm details

An orientation document for anyone (human or AI agent) picking up this codebase. It explains
what the code computes, how the state encoding works, and — in detail — what `regions.forward`
is doing geometrically, because that function is the whole engine and its index arithmetic is
opaque without the picture behind it.

Companion material: `tex/main.tex` (the written maths, with figures) and `README.md` (usage).
This document is the bridge between them and the source.

---

## 1. The question being answered

Take the closed unit disk `D` with `n` punctures `p_1, …, p_n` on the real axis, and draw a
*generator line* from each `p_j` up to the boundary point `i`. A path through the disk spells a
word in the free group `F_n`: each time it crosses the generator line of `p_j` it records
`x_j` (crossing left-to-right) or `x_j^{-1}` (right-to-left).

The motivating problem (see `tex/main.tex` §Setup) is the dual Artin isomorphism problem. The
orbit `Q = B_n · x_1` under the braid group consists of words that all correspond to **simple**
(embedded) loops. We want to rule out words from appearing in `Q`, so we ask:

> **Given a word `w ∈ F_n`, can `w` be drawn as an embedded (non-self-crossing) arc in the
> punctured disk?**

If it cannot, `w` cannot be a subword of any element of `Q`.

Two consequences of asking about **subwords** rather than loops:

- The arc's **starting point is free** — it starts at an arbitrary interior point, not at the
  basepoint `-i`. This matters for the first-crossing case (§5.2).
- The arc's endpoint is likewise free; we simply stop when the word is exhausted.

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

A segment has two sides. Following `tex/main.tex`, the **left face** of a segment gets a
positive integer, and the **right face** of the same segment gets its negative. So the signed
integer `+s` and `-s` are the two faces of one physical segment.

Crossing *from* face `+s` (i.e. approaching from the left) contributes a positive generator;
crossing from face `-s` contributes an inverse. Throughout the code, the variable named `seg`
is a **signed face**, and it is the face the arc crosses *from*.

### 3.2 `gen`: which generator a face contributes

`State.gen` is a tuple indexed by **absolute** segment id:

```
gen[0]        unused placeholder (segment ids start at 1)
gen[k], k ≥ 1 the generator index carried by face +k
```

and `_gen(state, seg)` returns `gen[|seg|]` for `seg > 0`, `-gen[|seg|]` for `seg < 0`. Negative
keys are never stored, since `gen[-k] = -gen[+k]` always. Initially `gen[k] = k` for
`k = 1 … n`; every segment later cut off line `j` inherits `gen = j` (`_fresh_seg`).

This is the code's version of the sets `S_x` in the LaTeX: `S_{x_j}` is
`{ s : _gen(s) = j }`, and `seg_possibilities_given_gen(state, j)` is the intersection of that
set with the current region.

### 3.3 Regions are cyclic tuples

`State.regions` is a tuple of regions; each region is a tuple of the signed faces on its
boundary, **read clockwise**. Only generator-line faces are listed — the arcs of the outer
circle and the pieces of the drawn path that also bound the region are implicit, not stored.

Region tuples are **cyclic**: `(-5, 6)` and `(6, -5)` denote the same region. (The LaTeX
example writes `(6, -5)` where the code produces `(-5, 6)`; they agree.)

### 3.4 The end-region convention — the single most important detail

**`regions[0]` is always the region containing the tip of the arc, and the tip sits at the
junction between the last entry and the first entry of that tuple** (i.e. "just before index
0", as `state_str` puts it).

Every branch of `forward` finishes by rotating the new end-region so that this holds. Once you
know this, the otherwise-mysterious slicing-and-concatenation in `forward` reads directly as
"cut the boundary cycle here, and re-anchor it there".

### 3.5 `State`

```python
class State(NamedTuple):
    n:                   int    # number of punctures
    regions:             tuple[tuple[int, ...], ...]
    gen:                 tuple[int, ...]
    next_seg:            int    # next fresh positive segment id
    first_crossing_done: bool
```

It is a `NamedTuple`, so states are immutable, structurally comparable and **hashable** — which
is what lets the search layer keep a `set` of states and deduplicate for free. Updates go
through `_replace`; there is no deep copying anywhere.

`make_state(n)` gives the uncut disk:

```
regions  = ((1, -1, 2, -2, …, n, -n),)
gen      = (0, 1, 2, …, n)
next_seg = n + 1
```

The single region is the disk cut open along all `n` generator lines: walking clockwise you go
down the left face of line 1 (`+1`), round `p_1`, back up its right face (`-1`), across to line
2, and so on; the outer circle is the implicit arc between `-n` and `+1`.

---

## 4. Invariants

These hold for every reachable state and are the best way to test changes to `forward`:

1. **Each signed face appears exactly once** across all regions. A face is one side of one
   sub-segment, so it borders exactly one region-slot.
2. **Faces come in pairs**: `+k` present ⟺ `-k` present, for every allocated `k`.
3. **One new segment per crossing**: after `c` crossings there are `n + c` segments, hence
   `2(n + c)` faces. This holds for both kinds of crossing.
4. **Region count**: 1 initially; an ordinary crossing adds `+1`; a crossing that *starts* an arc
   adds `0`, because a slit does not disconnect (§5.2). Drawing one arc of length `c` therefore
   leaves `c` regions; drawing `k` arcs of total length `c` leaves `c - k + 1`.
5. `regions[0]` is the end-region, anchored as in §3.4.

---

## 5. `forward(state, seg)` — the state update

Signature: cross the face `seg`, which must be present in `regions[0]`; return the new `State`
(`ValueError` otherwise).

### 5.1 The common recipe

Let `region = regions[0]`, `i = region.index(seg)`, `seg_sgn = sign(seg)`, and let `T` be a
freshly allocated segment id (`_fresh_seg`, inheriting `gen[|seg|]`).

The arc runs from the tip (just before index 0) to a point `q` in the interior of the segment at
index `i`, and passes through to the other side. Two things happen:

- **The segment is split at `q`.** Its `+` face becomes two faces and its `-` face becomes two
  faces. One piece of each keeps the old id, the other pair gets `±T`. Because
  `gen[T] = gen[|seg|]`, both pieces contribute the same generator as before — this is the
  `S_x ← S_x ∪ {T}` step of the LaTeX.
- **The region is cut** along the arc, into the part clockwise-before `q` and the part
  clockwise-after `q`.

The arc emerges on the opposite face `-seg`. Where `-seg` currently lives decides everything:

| situation | code branch |
|---|---|
| the arc is *starting* here (`first_crossing_done` is `False`) | new arc, §5.2 |
| `-seg` in the end-region, **after** `seg` (`i < pair_pos`) | Case A, first sub-case (LaTeX case 1b) |
| `-seg` in the end-region, **before** `seg` (`i > pair_pos`) | Case A, second sub-case (LaTeX case 1a) |
| `-seg` in some other region | Case B (LaTeX case 2) |

`_find_signed(regions, -seg)` locates it, returning `(region_index, position)`; it is a linear
scan over every face, so it is `O(n + c)` per step.

The split always uses the same convention, in all four branches:

```
crossed face  seg   splits clockwise into ( seg_sgn·T,  seg )
partner face -seg   splits clockwise into ( -seg, -seg_sgn·T )
```

and the region owning the partner face is rotated to begin at `-seg_sgn·T`, because the arc tip
lands exactly at that junction. Since `gen[T] = gen[|seg|]`, both halves of the split segment
still contribute the same generator — this is the `S_x ← S_x ∪ {T}` step of the LaTeX.

### 5.2 Starting an arc — why the region does *not* split

`forward_new_arc(state, seg, region_idx)` begins a fresh arc at a free interior point of
`regions[region_idx]` and crosses `seg`. `forward` delegates to it (with `region_idx = 0`)
whenever `first_crossing_done` is `False`.

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

For `n = 4`, crossing `+1`: `(1,-1,2,-2,3,-3,4,-4)` → `(-5, 2,-2,3,-3,4,-4, 5, 1, -1)`, matching
STEP 1 of the LaTeX example. Reading it clockwise: `5` is the upper piece of line 1 (from `i`
down to `q`), then the slit, then `1` (from `q` down to `p_1`), round the puncture, back up `-1`
to `q`, then the arc tip, then `-5`.

Applied to the pristine region this is algebraically identical to the older special-cased
formulas it replaced (`(-T,) + region[i+2:] + region[:i] + (T,) + region[i:i+2]` for positive
`seg`, `(T, -T) + region[i:] + region[:i]` for negative), which relied on `-seg` sitting at
`i ± 1`. `src/test/test_coexistence.py` pins that equivalence.

### 5.3 Case A — the partner face is in the same region

The arc leaves the region and comes straight back into it. The cut is a genuine chord, so the
region splits in two; the tip lands in whichever half contains `-seg`.

**Sub-case `i < pair_pos`** (partner after the crossed face, LaTeX case 1b):

```python
left  = region[:i] + (seg_sgn * T,)
right = (-seg_sgn * T,) + region[pair_pos + 1:] + region[i:pair_pos + 1]
new_regions = (right,) + state.regions[1:] + (left,)
```

`left` is the part of the boundary clockwise-before `q`, closed off by the new piece `+T`.
`right` is everything from `seg` onwards, with `-seg` split into `(-seg, -T)`, rotated so it
begins at `-T` — because the tip is exactly at the `-seg | -T` junction. `right` contains
`-seg`, so `right` becomes the new `regions[0]`.

**Sub-case `i > pair_pos`** (partner before the crossed face, LaTeX case 1a):

```python
left  = (-seg_sgn * T,) + region[pair_pos + 1:i] + (seg_sgn * T,) + region[:pair_pos + 1]
right = region[i:]
new_regions = (left,) + state.regions[1:] + (right,)
```

Here `-seg` lies in the *before* half, so that half — `left` — becomes the new end-region,
again rotated to start at `-T`. Reading `left` from `+T` instead: `T, region[0..pair_pos], -T,
region[pair_pos+1..i-1]`, which is the LaTeX's `(-T, …, T, …, -j)`. `right` is everything from
the crossed face onwards, the LaTeX's `(j, …)`; the piece of the split segment that keeps the id
`seg` stays at its head.

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

### 5.5 Worked example (matches `tex/main.tex`)

`n = 4`, word `x_1 x_2 x_4^{-1}`:

```
init    ((1, -1, 2, -2, 3, -3, 4, -4),)                              gen (0,1,2,3,4)
x1      ((-5, 2, -2, 3, -3, 4, -4, 5, 1, -1),)                       gen (…,5→1)   first crossing
x2      ((-6, 3, -3, 4, -4, 5, 1, -1, 2, -2), (-5, 6))               gen (…,6→2)   Case A, i < pair_pos
x4^-1   ((7, -7, -6, 3, -3, 4), (-5, 6), (-4, 5, 1, -1, 2, -2))      gen (…,7→4)   Case A, i > pair_pos
```

After this, `gen_possibilities(state) == [-4, -3, -2, 3, 4]`: the arc's tip is in the small
region `(7, -7, -6, 3, -3, 4)`, so the only letters it can produce next are `x_3^{±1}`,
`x_4`, `x_2^{-1}` (via face `-6`) and `x_4^{-1}` (via `-7`). Any word demanding, say, `x_1`
at this point is not drawable along this branch.

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
| `evaluate(n, word)` | `True` iff the signed word is drawable |
| `valid_assignment_of_signs(n, word)` | a choice of `±` per position making it drawable, else `None` |
| `valid_permutation_and_assignment_of_signs(n, word)` | as above, also trying every relabelling of the symbols present |
| `count_realisable(rank, length, prefix)` | `(drawable_count, total_count)` over reduced words extending `prefix` |
| `collect_realisable(rank, length, filename, prefix)` | same, writing the words to CSV |
| `count_minimal_invalid(rank, max_length)` | count of minimally-non-drawable words |
| `collect_minimal_invalid(rank, max_length, filename)` | same, writing to CSV |

`valid_assignment_of_signs` carries a frontier of `(state_set, sign_path)` pairs so it can
report the assignment it found; because the paths are kept distinct, that frontier can grow
like `2^len(word)` in the worst case — it is much more expensive than `evaluate`.

`valid_permutation_and_assignment_of_signs` permutes `sorted(set(word))`. That is a set of
**signed** letters, so it is really intended for unsigned (all-positive) input, as in `demo.py`;
on a mixed-sign word, `1` and `-1` would be permuted as if they were unrelated symbols.

### 6.2 Module flags

Set at the top of `searching.py` and read by the helpers:

- `IGNORE_POWERS = True` — treat words containing `x_j^{±2}` as out of scope. `_validate_word`
  **raises** on a repeated letter, the enumerators skip those branches, and the `branch` count
  drops to `2·rank - 2`. See §9. The GUI overwrites this module global at run time from a
  checkbox (`gui.py:317` and friends), so it is not a compile-time constant in practice.
- `PRODUCE_OUTPUT` is set by the GUI but never read inside `searching.py`; `IGNORE_SIGNS` and
  `USE_MULTIPROCESSING` are read nowhere at all. Treat all three as vestigial.

`_validate_word` also rejects non-reduced words (`w[i] == -w[i+1]`) and letters outside
`±1 … ±rank`.

### 6.3 Enumeration helpers

`count_realisable` / `collect_realisable` walk the tree of reduced words of a given length
extending a prefix (default `[1]`), advancing the frontier one letter at a time and cutting off
whole subtrees the moment the frontier empties. `total` is computed combinatorially as
`branch ** (length - len(prefix))` with `branch = 2·rank - 2` (or `2·rank - 1` if
`IGNORE_POWERS` is off) — it is not a count of anything enumerated.

`_minimal_invalid_words` finds words that are non-drawable but *minimally* so. It carries
`suffix_sets[k] = frontier after reading word[k:]`, and only extends a word when every proper
suffix stays alive; it emits the word when `suffix_sets[0]` finally empties. Since every proper
subword of `w` is a suffix of some prefix of `w`, and prefixes are only extended while alive,
the emitted words have **all** proper subwords drawable. Enumeration is rooted at the single
letter `1`; the docstring notes these are canonical representatives up to cyclic permutation and
reflection.

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

### 7.3 Signs fuse into the sweep

Sign choice does **not** need a separate enumeration layer. At an unsigned letter the frontier
advances by both `+l` and `-l` and the two results are merged, so the frontier is exactly "every
configuration reachable under every valid sign assignment" — deduplicated across assignments
rather than kept as `2^|w|` separate frontiers. This is what makes handing a configuration from
one word to the next cheap, and it is the reason `_reachable` takes a `signs` argument where `0`
means "free":

```python
options = (magnitude, -magnitude) if fixed == 0 else (fixed * magnitude,)
step    = _advance_new_arc if pos == 0 else _advance
states  = set().union(*(step(states, option) for option in options))
```

The cost is that a plain sweep no longer knows *which* signs worked. `_recover_signs` gets a
witness back by pinning one sign at a time and re-sweeping, keeping the family feasible at each
step — exact, because feasibility of a partially pinned family is monotone, and at most
`2 × (total length)` sweeps.

### 7.4 The permutation layer

One permutation is applied to **all** words at once — they share a disk, so their labellings
cannot be chosen independently — and it sits outside everything else.

Permuting only the symbols actually present is complete. Drawability depends solely on the
*relative order* of the punctures used: a generator line runs from a puncture to the boundary, so
it is a slit rather than a separating chord, and an arc can always pass beneath an unused puncture
without recording a letter. Verified over 32,640 words: `evaluate` is invariant under every
order-preserving relabelling (`{1,2,3} → {1,3,5}`, `{2,3,7}`, `{1,4,5}`, …). So mapping symbols
onto a wider or gappier subset of `{1..n}` can never reach a configuration a permutation misses.
The same fact is why `evaluate(15, w)` and `evaluate(k, w)` agree for any `k ≥ max |letter|`,
which is what lets `test.py` pass `rank=15` for everything.

### 7.5 API

| function | meaning |
|---|---|
| `can_coexist(n, words, permute=True, respect_signs=False)` | `True` iff the family can be drawn simultaneously |
| `coexist_witness(n, words, permute=True, respect_signs=False)` | `{"permutation": …, "signs": […]}` or `None` |

`permute=False` fixes the labelling; `respect_signs=True` takes the given signs literally instead
of searching over them. With both set, a one-word family reduces exactly to `evaluate`; with
neither, to `valid_permutation_and_assignment_of_signs`. `test_coexistence.py` checks that
correspondence over 504 words.

`"signs"` holds the words **as drawn** — already relabelled by the permutation, one sign per
letter — so it can be fed straight back in with `permute=False, respect_signs=True` to replay
the drawing. Cost in practice is milliseconds for families of a few words of length 4–6.

### 7.6 Properties worth knowing (all verified in `test_coexistence.py`)

- **Order independence.** `can_coexist(n, [w1, w2]) == can_coexist(n, [w2, w1])`. Disjointness is
  symmetric, so the drawing order is an implementation detail. Checked over 2000 pairs.
- **Monotone under sub-families.** If a family co-exists, so does every sub-family.
- **Strictly stronger than drawing words separately.** `[1,2,1]` and `[3,2,3]` are each drawable
  alone, but never together, under any permutation and any signs. Roughly 15% of sampled pairs of
  individually-drawable words behave this way, so the test genuinely discriminates.

---

## 8. File map

| path | role |
|---|---|
| `src/regions.py` | the engine: `State`, `make_state`, `forward`, `forward_new_arc`, `seg_possibilities_given_gen`, `gen_possibilities`, `new_arc_possibilities`, `state_str` |
| `src/searching.py` | frontier search and the public API; everything below the "Simi function implementations" banner is enumeration/reporting |
| `src/coexistence.py` | multi-word co-existence (§7): `can_coexist`, `coexist_witness` |
| `src/demo.py` | short narrated walk-through of `regions.py` and `searching.py`; `coexistence.py` has its own `__main__` demo |
| `src/gui.py` | Tkinter front-end (four tabs, background thread, optional CSV); no algorithmic content |
| `src/test/test.py` | runs `evaluate` over each corpus and prints a true/false tally |
| `src/test/test_coexistence.py` | self-checking suite for §7 — agreement with `searching.py`, order independence, witness replay, invariants |
| `src/test/braid_orbit.py` | generates a ground-truth corpus: the orbit of `[1]` under braid words up to a given length — every word in it *should* evaluate `True` |
| `src/test/subwords/*.txt` | corpora, one Python list per line |
| `tex/main.tex` | the maths, with the figures the case analysis refers to |

`src/test/subwords/braid_orbit_braidlength7_rank7.txt` (6585 words) is the most useful
regression set: it is derived from the braid action, so every line is drawable by construction,
and any `False` there is a genuine bug. `known_valid.txt` / `known_non_valid.txt` are small
hand-curated sets; `mostly_non_valid.txt` is a large mixed set with no per-line ground truth.

---

## 9. Known quirks and traps

**Squares are "drawable", by design.** The algorithm will happily draw `x_j x_j`: you can spiral
an ever-growing arc around a single puncture. Such words do not arise as subwords of reduced
words in the setting of interest, for independent and provable reasons, so they are excluded
rather than handled — that is what `IGNORE_POWERS = True` is for, and `_validate_word` raises on
them. Do not "fix" a `True` answer on a square.

**The two halves of a cut end-region are `region[:i] + new face` and `region[i:]`.** Both Case A
sub-cases and Case B slice the old end-region at the crossed face `i`; what differs between them
is only which half absorbs the `-T` relabelling and becomes the new `regions[0]`. If you are
modifying `forward`, that symmetry is the sanity check — a half that starts anywhere other than
the crossed face is duplicating or dropping boundary.

**`seg` is a face, not a segment id.** `forward(state, 2)` and `forward(state, -2)` are different
moves on the same physical segment. `seg_possibilities_given_gen` returns faces.

**Region tuples are cyclic** — never compare them with `==` to decide whether two regions are the
same; only `regions[0]` has a canonical rotation.

**`gen` is indexed by absolute value** and is append-only; `gen[0]` is a placeholder so that
segment id `k` lands at index `k`.

**Rank vs. word content.** `evaluate(n, word)` puts `n` punctures in the disk regardless of which
generators the word uses. Extra punctures are never a help or a hindrance, so `test.py` just
passes `rank=15`. But `n` must be at least `max |letter|` or `_validate_word` rejects the word.

**Performance shape.** Cost per letter is `|frontier| × (choices) × O(total faces)`; the frontier
is the thing that explodes. `evaluate` on a single word is cheap; the enumerators are exponential
in `length` and are the reason for the prefix argument.
