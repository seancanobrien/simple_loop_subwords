"""
Parity tests: run both the original class-based Regions and the new
functional implementation through the same sequences of forward() calls,
then compare regions and gen at each step.
"""
import sys, os, copy

# ---------------------------------------------------------------------------
# Paths — adjust if your originals live elsewhere
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "original"))

# We inline a minimal copy of the original class here so the test is
# self-contained.  Replace with `from regions import Regions` if preferred.
# ---------------------------------------------------------------------------

import copy as _copy

class Regions:
    def __init__(self, n):
        if n < 1:
            raise ValueError("Need at least 1 puncture.")
        self.n = n
        self._next_seg = n + 1
        initial = []
        for k in range(1, n + 1):
            initial.append(+k)
            initial.append(-k)
        self.regions = [initial]
        self.gen = {}
        for k in range(1, n + 1):
            self.gen[+k] = +k
            self.gen[-k] = -k
        self._first_crossing_done = False

    def _find_signed(self, target):
        for ri, region in enumerate(self.regions):
            for pos, s in enumerate(region):
                if s == target:
                    return ri, pos
        raise RuntimeError(f"Signed segment {target} not found.\nRegions: {self.regions}")

    def _fresh_seg(self, old_seg):
        sid = self._next_seg
        self._next_seg += 1
        self.gen[sid]  = self.gen[abs(old_seg)]
        self.gen[-sid] = self.gen[-abs(old_seg)]
        return sid

    def clone(self):
        return _copy.deepcopy(self)

    def forward(self, seg):
        region = list(self.regions[0])
        seg_sgn = 1 - 2 * (seg < 0)
        if seg not in region:
            raise ValueError(f"Segment {seg} is not in the end-region {region}.")
        i = region.index(seg)
        if not self._first_crossing_done:
            T = self._fresh_seg(seg)
            if seg_sgn == 1:
                self.regions[0] = [-T] + region[i+2:] + region[:i] + [T] + region[i:i+2]
            else:
                self.regions[0] = [T,-T] + region[i:] + region[:i]
            self._first_crossing_done = True
            return
        T = self._fresh_seg(seg)
        pair = -seg
        pair_ri, pair_pos = self._find_signed(pair)
        if pair_ri == 0:
            if i < pair_pos:
                left  = region[:i] + [seg_sgn*T]
                right = [-seg_sgn*T] + region[pair_pos+1:] + region[i:pair_pos+1]
                self.regions[0] = right
                self.regions.append(left)
            else:
                left  = [-seg_sgn*T] + region[pair_pos+1:i] + [seg_sgn*T] + region[:pair_pos+1]
                right = region[pair_pos+1:]
                self.regions[0] = left
                self.regions.append(right)
        else:
            r_prime = list(self.regions[pair_ri])
            r_left  = region[:i] + [seg_sgn*T]
            r_right = region[i:]
            r_prime_new = [-seg_sgn*T] + r_prime[pair_pos+1:] + r_prime[:pair_pos+1]
            self.regions[0] = r_prime_new
            self.regions.pop(pair_ri)
            self.regions.extend([r_left, r_right])

# ---------------------------------------------------------------------------
from regions import (
    make_state, forward as fwd,
    seg_possibilities_given_gen, _gen, State
)

# ---------------------------------------------------------------------------

def regions_to_frozensets(regions_list):
    """Order-insensitive comparison of region sets."""
    return frozenset(frozenset(r) for r in regions_list)

def state_regions_as_frozensets(state):
    return frozenset(frozenset(r) for r in state[1])

def gen_dict_from_state(state):
    """Reconstruct the full gen dict from a state for all segs seen in regions."""
    result = {}
    for r in state[1]:
        for s in r:
            result[s] = _gen(state, s)
    return result


def compare(n, moves, label=""):
    """Run both implementations through `moves`, compare at end."""
    # --- class-based ---
    R = Regions(n)
    for seg in moves:
        R.forward(seg)

    # --- functional ---
    S = make_state(n)
    for seg in moves:
        S = fwd(S, seg)

    # Compare regions (as frozensets, order-insensitive)
    class_fs  = regions_to_frozensets(R.regions)
    func_fs   = state_regions_as_frozensets(S)
    regions_ok = class_fs == func_fs

    # Compare gen for all signed segs present in regions
    class_gen = {s: R.gen[s] for r in R.regions for s in r}
    func_gen  = gen_dict_from_state(S)
    gen_ok = class_gen == func_gen

    # next_seg and first_crossing_done
    next_seg_f, fcd_f = S.next_seg, S.first_crossing_done
    meta_ok = (next_seg_f == R._next_seg) and (fcd_f == R._first_crossing_done)

    ok = regions_ok and gen_ok and meta_ok
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {label or moves}")
    if not ok:
        if not regions_ok:
            print(f"  class  regions: {sorted(R.regions)}")
            print(f"  func   regions: {sorted(list(r) for r in S[1])}")
        if not gen_ok:
            print(f"  class  gen: {class_gen}")
            print(f"  func   gen: {func_gen}")
        if not meta_ok:
            print(f"  class  next_seg={R._next_seg} fcd={R._first_crossing_done}")
            print(f"  func   next_seg={next_seg_f}  fcd={fcd_f}")
    return ok


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

all_pass = True

def t(n, moves, label=""):
    global all_pass
    if not compare(n, moves, label):
        all_pass = False

# Basic first-crossing (positive seg)
t(3, [2],          "n=3 first crossing +2")
t(3, [-2],         "n=3 first crossing -2")
t(3, [1],          "n=3 first crossing +1")

# First + one subsequent
t(3, [2, 3],       "n=3 two crossings")
t(3, [2, -3],      "n=3 two crossings neg second")

# The example from the original docstring
t(3, [2, 3, 3, -6, -2], "n=3 docstring example")

# Longer chains
t(4, [1, 2, 3, 4],        "n=4 sequential")
t(4, [3, -3, 2, -2],      "n=4 alternating signs")
t(2, [1, -1, 1, -1],      "n=2 repeated")
t(5, [3, 4, -7],           "n=5 mixed (valid segs)")

# Edge: n=1
t(1, [1],          "n=1 single crossing")
t(1, [1, -1],      "n=1 two crossings")  # -1 seg gets created after first cross

print()
print("All tests passed!" if all_pass else "SOME TESTS FAILED.")
