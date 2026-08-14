"""
The engine: an embedded arc drawn one crossing at a time in a punctured disk.

The arc drawn so far, together with the n generator lines, cuts the disk into regions,
and each generator line is cut into segments by the places the arc has crossed it.  To
contribute the next letter the arc must cross a segment of the right line in the right
direction, and that segment must bound the region the arc's tip is currently in.
`forward` performs one such crossing.

Faces
-----
A segment has two sides, and both are encoded in one signed integer: the *left* face of
segment k is +k and its *right* face is -k.  Crossing from face +k contributes a
positive generator, crossing from -k contributes an inverse.  Throughout this module
the variable `seg` is a signed **face**, and it is the face the arc crosses *from* --
so `forward(state, 2)` and `forward(state, -2)` are different moves on one segment.

Regions
-------
Each region is a tuple of the signed faces on its boundary, read clockwise.  Only
generator-line faces are listed; the arcs of the outer circle and the pieces of the
drawn path that also bound the region are implicit.  Region tuples are **cyclic**:
(-5, 6) and (6, -5) denote the same region, so they must not be compared with ==.

By convention `regions[0]` is always the region holding the tip of the arc, and the tip
sits at the junction between the last entry and the first entry of that tuple.  Every
branch of `forward` finishes by rotating the new end-region so this holds; it is what
makes the slicing in each branch read as "cut the boundary cycle here, re-anchor it
there", and what lets the search layer deduplicate states.

gen encoding
------------
gen[k]  for k >= 1  stores gen[+k], the generator index carried by face +k.
gen[-k] is always -gen[+k], so negative keys are never stored explicitly.
gen[0]  is unused (segment IDs start at 1); stored as 0 as a placeholder.

Every segment cut off line j inherits gen = j, so both halves of a split segment go on
contributing the same generator.

State
-----
A NamedTuple with five named fields -- behaves like a plain tuple underneath, so
"copying" is just constructing a new instance with _replace().  No deepcopy.  Being
hashable is what lets the search layer keep states in a set and deduplicate for free.

Invariants
----------
These hold for every reachable state, and are the best way to test changes to
`forward`:

1. Each signed face appears exactly once across all regions.
2. Faces come in pairs: +k is present if and only if -k is.
3. One new segment per crossing: after c crossings there are n + c segments.
4. An ordinary crossing adds one region; a crossing that *starts* an arc adds none,
   because a slit does not disconnect.
5. regions[0] is the end-region, anchored as above.
"""

from typing import NamedTuple


# ------------------------------------------------------------------ state

class State(NamedTuple):
    n:                    int                        # number of punctures
    regions:              tuple[tuple[int, ...], ...]
    gen:                  tuple[int, ...]            # gen[0] unused; gen[k] = gen[+k] for k >= 1
    next_seg:             int                        # next fresh positive segment ID
    first_crossing_done:  bool


# ------------------------------------------------------------------ constructor

def make_state(n: int) -> State:
    """Return the initial State for n punctures."""
    if n < 1:
        raise ValueError("Need at least 1 puncture.")

    initial_region = tuple(val for k in range(1, n + 1) for val in (k, -k))

    # gen[k] = k for k = 1..n  (identity: gen[+k] = +k)
    # gen[0] = 0 as an unused placeholder so that segment ID k maps to index k
    gen = (0,) + tuple(range(1, n + 1))

    return State(
        n=n,
        regions=(initial_region,),
        gen=gen,
        next_seg=n + 1,
        first_crossing_done=False,
    )


# ------------------------------------------------------------------ accessors

def _gen(state: State, seg: int) -> int:
    """Return the generator contributed by crossing signed segment seg."""
    return state.gen[abs(seg)] if seg > 0 else -state.gen[abs(seg)]


def _fresh_seg(state: State, old_seg: int) -> tuple[State, int]:
    """
    Allocate a fresh segment ID inheriting gen from old_seg.
    Returns (updated_state, new_seg_id).
    """
    sid = state.next_seg
    inherited = state.gen[abs(old_seg)]   # gen[+sid] inherits from old_seg
    return (
        state._replace(
            next_seg=sid + 1,
            gen=state.gen + (inherited,),  # index sid is appended at the end
        ),
        sid,
    )


# ------------------------------------------------------------------ helpers

def _find_signed(regions: tuple[tuple[int, ...], ...], target: int) -> tuple[int, int]:
    """Return (region_index, position) of signed segment target."""
    for ri, region in enumerate(regions):
        for pos, s in enumerate(region):
            if s == target:
                return ri, pos
    raise RuntimeError(
        f"Signed segment {target} not found.\nRegions: {regions}"
    )


# ------------------------------------------------------------------ public API

def seg_possibilities_given_gen(state: State, generator: int, region_idx: int = 0) -> list[int]:
    """
    Return all signed segments in region_idx whose crossing contributes
    generator to the word.
    """
    return [seg for seg in state.regions[region_idx] if _gen(state, seg) == generator]


def gen_possibilities(state: State, region_idx: int = 0) -> list[int]:
    """Return all signed generators available for crossing in region_idx."""
    possible = set()
    for k in range(1, state.n + 1):
        if seg_possibilities_given_gen(state, -k, region_idx=region_idx):
            possible.add(-k)
        if seg_possibilities_given_gen(state, +k, region_idx=region_idx):
            possible.add(+k)
    return list(possible)


def new_arc_possibilities(state: State, generator: int) -> list[tuple[int, int]]:
    """
    Return every (region_idx, seg) at which a *fresh* arc could start and make its
    first crossing contribute generator.

    A fresh arc may begin at a free interior point of any region, so unlike
    seg_possibilities_given_gen this scans every region, not just the end-region.
    """
    return [
        (ri, seg)
        for ri, region in enumerate(state.regions)
        for seg in region
        if _gen(state, seg) == generator
    ]


def forward_new_arc(state: State, seg: int, region_idx: int = 0) -> State:
    """
    Begin a new arc at a free interior point of regions[region_idx] and cross seg.
    Returns a new State.  Raises ValueError if seg does not bound that region.

    This is the general form of the "first crossing" rule.  Because the arc starts at
    a free interior point, the cut is a *slit* rather than a chord: it does not
    disconnect the starting region, so the region count is unchanged (an ordinary
    crossing raises it by one).  Only the crossed segment is split:

        crossed face  seg  splits clockwise into (seg_sgn * T, seg), slit between them
        partner face -seg  splits clockwise into (-seg, -seg_sgn * T), tip between them

    The region owning the partner face receives the arc tip, so it is rotated to begin
    at -seg_sgn * T and becomes the new end-region.

    On the initial state this reproduces the pristine first-crossing formulas exactly;
    unlike them it also copes with a configuration left behind by an earlier arc, where
    the partner face may sit anywhere -- including in another region.
    """
    region = state.regions[region_idx]

    if seg not in region:
        raise ValueError(f"Segment {seg} does not bound region {region_idx} {list(region)}.")

    seg_sgn = 1 if seg > 0 else -1
    state, T = _fresh_seg(state, seg)
    region = state.regions[region_idx]
    i = region.index(seg)

    # Split the crossed face.  The arc enters through the slit between the two pieces.
    cut = region[:i] + (seg_sgn * T, seg) + region[i + 1:]
    regions = state.regions[:region_idx] + (cut,) + state.regions[region_idx + 1:]

    # Split the partner face.  The arc tip lands between its two pieces.
    pair_ri, pair_pos = _find_signed(regions, -seg)
    partner = regions[pair_ri]
    split = partner[:pair_pos] + (-seg, -seg_sgn * T) + partner[pair_pos + 1:]

    # Anchor the end-region so the tip sits just before index 0.
    anchor = pair_pos + 1                      # index of -seg_sgn * T
    end_region = split[anchor:] + split[:anchor]

    return state._replace(
        regions=(end_region,) + regions[:pair_ri] + regions[pair_ri + 1:],
        first_crossing_done=True,
    )


def forward(state: State, seg: int) -> State:
    """
    Cross the face seg, which must bound the end-region, and return the new State.
    Raises ValueError if seg is not in the end-region.

    The arc runs from the tip to a point q in the interior of the crossed segment and
    passes through.  Two things happen: the segment is split at q, one piece keeping the
    old ID and the other taking a fresh ID T (inheriting its generator); and the region
    is cut along the arc.  In every branch the split follows the same convention,

        crossed face  seg  splits clockwise into ( seg_sgn * T,  seg )
        partner face -seg  splits clockwise into ( -seg, -seg_sgn * T )

    and the region owning the partner face is rotated to begin at -seg_sgn * T, because
    the tip lands exactly at that junction.

    Where the partner face -seg currently lives decides which branch applies:

        the arc is starting here          a slit, not a chord -- see forward_new_arc
        -seg in the end-region, after seg   case A, first sub-case
        -seg in the end-region, before seg  case A, second sub-case
        -seg in some other region           case B

    In case A the arc leaves the region and comes straight back, so the cut is a genuine
    chord and the region splits in two; the tip lands in whichever half holds -seg.  In
    case B the old end-region is cut in two and neither half holds the tip: the region
    owning -seg is not cut at all, only relabelled and re-anchored, and it becomes the
    new end-region.  Both add one region, as the invariants require.
    """
    region = state.regions[0]

    if seg not in region:
        raise ValueError(f"Segment {seg} is not in the end-region {list(region)}.")

    # -- FIRST CROSSING -------------------------------------------------------
    # The arc's start point is free, so this is a slit rather than a chord.
    if not state.first_crossing_done:
        return forward_new_arc(state, seg, region_idx=0)

    seg_sgn = 1 if seg > 0 else -1
    i = region.index(seg)

    # Allocate a fresh segment T before we do anything else
    state, T = _fresh_seg(state, seg)
    region = state.regions[0]   # regions haven't changed yet; re-bind for clarity

    # -- SUBSEQUENT CROSSINGS -------------------------------------------------
    pair_ri, pair_pos = _find_signed(state.regions, -seg)

    if pair_ri == 0:
        # -- Case A: pair is in the same (end) region -------------------------
        if i < pair_pos:
            left  = region[:i] + (seg_sgn * T,)
            right = (-seg_sgn * T,) + region[pair_pos + 1:] + region[i:pair_pos + 1]
            new_regions = (right,) + state.regions[1:] + (left,)
        else:
            left  = (-seg_sgn * T,) + region[pair_pos + 1:i] + (seg_sgn * T,) + region[:pair_pos + 1]
            right = region[i:]
            new_regions = (left,) + state.regions[1:] + (right,)
    else:
        # -- Case B: pair is in a different region r_prime --------------------
        r_prime = state.regions[pair_ri]
        r_left  = region[:i] + (seg_sgn * T,)
        r_right = region[i:]
        r_prime_new = (-seg_sgn * T,) + r_prime[pair_pos + 1:] + r_prime[:pair_pos + 1]
        # r_prime_new becomes the new end-region; old end-region splits into r_left, r_right
        remaining = state.regions[1:pair_ri] + state.regions[pair_ri + 1:]  # drop old r_prime
        new_regions = (r_prime_new,) + remaining + (r_left, r_right)

    return state._replace(regions=new_regions)


# ------------------------------------------------------------------ debug

def state_str(state: State) -> str:
    """Human-readable state dump."""
    lines = ["State("]
    for i, r in enumerate(state.regions):
        marker = "  <- END (path-end is just before index 0)" if i == 0 else ""
        lines.append(f"  [{i}] {list(r)}{marker}")
    lines.append(")")
    gen_display = {seg: _gen(state, seg) for region in state.regions for seg in region}
    lines.append(f"gen                 = {gen_display}")
    lines.append(f"next_seg            = {state.next_seg}")
    lines.append(f"first_crossing_done = {state.first_crossing_done}")
    return "\n".join(lines)
