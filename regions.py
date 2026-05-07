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


def forward(state: State, seg: int) -> State:
    """
    Cross segment seg (present in the end-region).
    Returns a new State.  Raises ValueError if seg is not in the end-region.
    """
    region = state.regions[0]

    if seg not in region:
        raise ValueError(f"Segment {seg} is not in the end-region {list(region)}.")

    seg_sgn = 1 if seg > 0 else -1
    i = region.index(seg)

    # Allocate a fresh segment T before we do anything else
    state, T = _fresh_seg(state, seg)
    region = state.regions[0]   # regions haven't changed yet; re-bind for clarity

    # -- FIRST CROSSING -------------------------------------------------------
    if not state.first_crossing_done:
        if seg_sgn == 1:
            new_region = (-T,) + region[i + 2:] + region[:i] + (T,) + region[i:i + 2]
        else:
            new_region = (T, -T) + region[i:] + region[:i]
        return state._replace(
            regions=(new_region,) + state.regions[1:],
            first_crossing_done=True,
        )

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
            right = region[pair_pos + 1:]
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
