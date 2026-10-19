# Implementation

How the code implements [the algorithm](algorithm.md). Read `regions.py`, then `searching.py`,
then `coexistence.py`. The modules import each other by bare name, so run them from the
repository root.

## Files

| path | role |
|---|---|
| `main.py` | entry point for `python3 -i main.py`: imports the three modules, defines `demo()` and `run_tests()` |
| `regions.py` | the engine: `State`, `make_state`, `forward`, `forward_new_arc`, `seg_possibilities_given_gen`, `gen_possibilities`, `new_arc_possibilities`, `state_str` |
| `searching.py` | the single-word search and API: `can_exist`, `can_exist_witness` |
| `coexistence.py` | the co-existence search and API: `can_coexist`, `coexist_witness` |
| `test/` | test suites and word corpora; see [test/README.md](../test/README.md) |

## State (`regions.py`)

```python
class State(NamedTuple):
    n:               int                          # number of punctures
    regions:         tuple[tuple[int, ...], ...]  # region tuples; regions[0] holds the tip
    gen:             tuple[int, ...]              # the dictionary, indexed by |face|
    next_seg:        int                          # the next free label T
    arc_in_progress: bool                         # is there a tip in regions[0]?
```

`make_state(n)` gives `regions = ((0, 1, -1, …, n, -n),)`, `gen = (0, 1, …, n)` and
`next_seg = n + 1`.

- **Faces** are signed ints; `seg` always names the face the arc crosses *from*, so
  `forward(state, 2)` and `forward(state, -2)` are different moves.
- **`gen`** is indexed by `|seg|` and only ever appended to. `_gen(state, seg)` returns
  `±gen[|seg|]`; `_fresh_seg` allocates `T = next_seg` with the generator of the segment it was
  cut from.
- **The boundary** is generator 0: `gen[0] = 0`, and every piece cut off it also gets 0.
  `_is_boundary` tests `gen == 0`, never the sign, because `-0 == 0`.
- **The tip.** While `arc_in_progress`, the tip sits just before `regions[0][0]`. It is `False`
  in the uncut disk and after an arc ends on the boundary. An arc that ends at a free point
  leaves it `True`; the search just stops, or starts the next arc with `forward_new_arc`.
- `State` is a `NamedTuple`: immutable and hashable, so the search keeps states in a `set`.
  Updates go through `_replace`.

## Region updates

Each case of [Region updates](algorithm.md#region-updates) is one branch. `i` is 0-indexed,
`pair_pos` is the position of `-seg`, and `s = seg_sgn`.

| case | code | new regions |
|---|---|---|
| starting a new arc | `forward_new_arc` | `region[:i] + (s*T, seg) + region[i+1:]`; then the partner's region, split and rotated to start at `-s*T` |
| ρ = τ, i < j | `forward`, case A | `(-s*T,) + region[pair_pos+1:] + region[i:pair_pos+1]` and `region[:i] + (s*T,)` |
| ρ = τ, j < i | `forward`, case A | `(-s*T,) + region[pair_pos+1:i] + (s*T,) + region[:pair_pos+1]` and `region[i:]` |
| ρ ≠ τ | `forward`, case B | `(-s*T,) + r_prime[pair_pos+1:] + r_prime[:pair_pos+1]`, `region[:i] + (s*T,)`, `region[i:]` |
| starting on the boundary | `forward_new_arc` → `_start_on_boundary` | `(T,) + region[i+1:] + region[:i+1]` |
| ending on the boundary | `forward` → `_end_on_boundary` | `region[:i] + (T,)` and `region[i:]` |

`forward` delegates to `forward_new_arc` (with `region_idx = 0`) whenever no arc is in progress,
and checks `_is_boundary` before doing any sign arithmetic. The new tip region goes first; other
new regions go to the back. `_find_signed` locates `-seg` by a linear scan, `O(n + c)` per step.

The sanity check when editing `forward`: whenever the old end-region is cut, the two halves are
`region[:i]` plus a new face and `region[i:]`. Only which half (if any) takes the tip differs.

## Invariants

These hold for every reachable state; `test/` checks them.

1. Each face appears exactly once across all regions.
2. Generator faces come in pairs, `+k` with `-k`. Boundary faces are unpaired and never negative.
3. After `c` crossings and `b` arc ends on the boundary there are `n + c` generator segments
   and `1 + b` boundary segments.
4. `k` arcs leave `c - k + b + 1` regions: starting an arc adds none, every other step adds one.
5. While an arc is in progress, `regions[0]` holds its tip, anchored as above.

## Search (`searching.py`)

A breadth-first sweep over a set of states, one letter at a time:

```python
def _advance(states, letter):
    return {forward(s, seg) for s in states for seg in seg_possibilities_given_gen(s, letter)}
```

Dead branches contribute nothing; an empty frontier means the word is not drawable. The `set`
merges identical states. Dedup is structural, not geometric: the same picture with different
labels, or a non-tip region at a different rotation, does not merge.

- **Signs** are fused into the sweep. `_sweep(n, word, signs)` takes a sign per letter, `0`
  meaning free; at a free letter the frontier advances by both `+l` and `-l` and the results are
  merged, so one sweep covers every assignment.
- **Witnesses.** `_recover_signs` pins one sign at a time and re-sweeps, at most
  `2 × len(word)` sweeps. This is exact because a merged sweep is the union over every completion
  of the pinned prefix.
- **Permutations** sit outside the sweep and permute the unsigned symbols present,
  `sorted({|x| : x in word} - {0})`: `k!` sweeps for `k` symbols, the dominant cost.
- **The boundary letter** needs no special step. A leading `0` reaches `forward_new_arc` through
  `forward`; a trailing `0` reaches `_end_on_boundary` through
  `seg_possibilities_given_gen(s, 0)`. It is advanced once, not as `±0`, and is never relabelled.
- **Validation.** `_validate_word(word, rank=None, check_for_squares=True)` rejects non-lists,
  a `0` anywhere but the ends, a word of only `0`s, letters outside `±1 … ±rank`, non-reduced
  words, and squares. `rank=None` imposes no upper bound, which lets `_resolve_rank` default the
  rank to `max |letter|`.

## Co-existence (`coexistence.py`)

`_reachable(n, words, signs)` runs the same sweep across the words in turn, with one extra step
at the first letter of each word:

```python
def _advance_new_arc(states, letter):  # start a fresh arc, in ANY region
    return {forward_new_arc(s, seg, ri) for s in states for ri, seg in new_arc_possibilities(s, letter)}
```

`new_arc_possibilities` scans every region, where `seg_possibilities_given_gen` scans only the
tip's; this is the only place the co-existence search fans out wider. Signs, witnesses
(`_recover_signs`, at most `2 × (total length)` sweeps) and permutations work as in
`searching.py`, with one permutation for the whole family. `_resolve_family` defaults the rank
to the largest `|letter|` in the family.

## Quirks

- **Squares are "drawable".** The algorithm happily draws $x_j x_j$, as a spiral round one
  puncture. Such words do not occur as subwords of the reduced words of interest, so
  `_validate_word` rejects them; `check_for_squares=False` switches this off. Do not "fix" a
  `True` on a square.
- **Region tuples are cyclic.** Never compare them with `==`; only `regions[0]` has a canonical
  rotation.
- **Rank belongs to the disk, not the word.** An explicit `n` below `max |letter|` is rejected;
  a larger one changes nothing, which is why `test/test_corpus.py` can fix `rank=15`.
- **Argument order differs between layers.** Public functions take the word first,
  `can_exist(word, n)`; internal sweeps take the rank first, `_sweep(n, word, signs)`, as the
  `regions` functions take the state first.
- **Performance.** Cost per letter is `|frontier| × choices × O(faces)`, and the frontier is what
  grows. Pass `permute=False` when the labelling is meant as given: `test/test_corpus.py` sweeps
  all 16,385 corpus words that way in about two seconds.
