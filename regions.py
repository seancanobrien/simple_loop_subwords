"""
Functional implementation of Regions using an immutable NamedTuple state.

State
-----
A NamedTuple with four named fields — behaves like a plain tuple underneath,
so "copying" is just constructing a new instance with _replace().  No deepcopy.

gen encoding
------------
gen[k]  for k >= 1  stores gen[+k].
gen[-k] is always -gen[+k], so negative keys are never stored explicitly.
gen[0]  is unused (seg IDs start at 1); stored as 0 as a placeholder.
"""

from typing import NamedTuple


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
    Cross segment seg (present in the end-region).
    Returns a new State.  Raises ValueError if seg is not in the end-region.
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
    lines.append(f"gen               = {gen_display}")
    lines.append(f"next_seg          = {state.next_seg}")
    lines.append(f"first_crossing_done = {state.first_crossing_done}")
    return "\n".join(lines)
