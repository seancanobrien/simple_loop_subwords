import copy

"""
Regions: tracks the regions of a punctured disk as a path is drawn.

Conventions
-----------
- n punctures, each connected to the disk boundary by a radial line.
- A *segment* is an oriented side of a line (radial or newly drawn).
  Segments are identified by nonzero integers:
    +s  = left side  of segment |s|   -> crossing it gives gen[+s] to the word
    -s  = right side of segment |s|   -> crossing it gives gen[-s] = -gen[+s]
- Every signed segment appears in exactly one region.
  The pair of signed segment s is -s.
- Each region is a Python list of signed segment integers in a fixed linear
  order.  The "end" of the drawn path sits just before index 0 self.regions[0]

Initial state (n punctures)
----------------------------
One region: [+1, -1, +2, -2, ..., +n, -n]
gen[+k] = +k,  gen[-k] = -k   for k = 1..n

First crossing (of seg in end-region)
---------------------------------------
No new segment is created. New +- segments are added to region and order
is cycled accordingly. 

Subsequent crossings
--------------------
TODO
"""
class Regions:
    def __init__(self, n: int):
        """
        Initialise with n punctures.
        Creates one region [+1, -1, +2, -2, ..., +n, -n].
        """
        if n < 1:
            raise ValueError("Need at least 1 puncture.")
        self.n = n
        self._next_seg = n + 1       # next fresh positive segment ID

        initial = []
        for k in range(1, n + 1):
            initial.append(+k)
            initial.append(-k)
        self.regions: list = [initial]

        # gen[signed_seg] -> signed generator contributed by crossing that side
        self.gen: dict = {}
        for k in range(1, n + 1):
            self.gen[+k] = +k
            self.gen[-k] = -k

        self._first_crossing_done: bool = False

    # ------------------------------------------------------------------ helpers

    def _find_signed(self, target: int):
        """Return (region_index, position) of signed segment `target`."""
        for ri, region in enumerate(self.regions):
            for pos, s in enumerate(region):
                if s == target:
                    return ri, pos
        raise RuntimeError(
            f"Signed segment {target} not found -- internal inconsistency.\n"
            f"Regions: {self.regions}"
        )

    def _fresh_seg(self, old_seg_being_split) -> int:
        sid = self._next_seg
        self._next_seg += 1
        self.gen[sid] = self.gen[abs(old_seg_being_split)]
        self.gen[-sid] = self.gen[-abs(old_seg_being_split)]
        return sid

    # ------------------------------------------------------------------ public

    def clone(self):
        return copy.deepcopy(self)

    def seg_possibilities_given_gen(self, generator: int, region_idx=0) -> list:
        """
        Return all signed segments in region 0 (by default) whose crossing
        would contribute `generator` to the word.

        Returns [] if the word cannot be extended.
        """
        region = self.regions[region_idx]
        return [seg for seg in region if self.gen[seg] == generator]
    
    def gen_possibilities(self, region_idx=0) -> list:
        """
        Return all signed generators available for
        crossing in region 0 (by default).
        """
        possible_gens = []
        for k in range(1, self.n + 1):
            if self.seg_possibilities_given_gen(-k, region_idx=region_idx):
                possible_gens.append(-k)
            if self.seg_possibilities_given_gen(k, region_idx=region_idx):
                possible_gens.append(k)

        # only unique values
        return list(set(possible_gens))

    def forward(self, seg: int):
        """
        Cross segment `seg` (a signed integer present in the end-region).

        Updates regions, gen in place.
        Raises ValueError if `seg` is not in the end-region.
        """
        region = list(self.regions[0])   # work on a copy
        seg_sgn = 1 - 2 * (seg < 0) # sign function (>=0 => +1, <0 => -1)

        if seg not in region:
            raise ValueError(
                f"Segment {seg} is not in the end-region {region}."
            )
        
        i = region.index(seg)

        # -- FIRST CROSSING: rotate so seg is at index 0, no split ----------
        if not self._first_crossing_done:
            # Mint fresh seg which splits the seg we are about to cross
            T = self._fresh_seg(seg)

            if seg_sgn == 1:
                self.regions[0] = [-T] + region[i + 2:] + region[:i] + [T] + region[i:i+2]
            else:
                self.regions[0] = [T,-T] + region[i:] + region[:i]
            self._first_crossing_done = True
            return

        # -- SUBSEQUENT CROSSINGS -------------------------------------------
        # Mint fresh seg which splits the seg we are about to cross
        T = self._fresh_seg(seg)

        # Find pair (-seg)
        pair = -seg
        pair_ri, pair_pos = self._find_signed(pair)
        # print(pair_ri, pair_pos)

        if pair_ri == 0:
            # -- Case A: pair in same region ----------------------------------
            if i < pair_pos:
                left = region[:i] + [seg_sgn * T]
                right = [-seg_sgn * T] + region[pair_pos + 1:] + region[i:pair_pos + 1]
                # region containing end
                self.regions[0] = right
                self.regions.append(left)
            else:
                left = [-seg_sgn * T] + region[pair_pos + 1: i] + [seg_sgn*T] + region[:pair_pos + 1]
                right = region[pair_pos + 1:]
                # region containing end
                self.regions[0] = left
                self.regions.append(right)

        else:
            # -- Case B: pair in different region r' --------------------------
            r_prime = list(self.regions[pair_ri])

            # current region splits
            r_left  = region[:i] + [seg_sgn * T]
            r_right = region[i:]

            # new region r' gets new segment and is cycled
            r_prime_new = [-seg_sgn * T] + r_prime[pair_pos + 1:] + r_prime[:pair_pos + 1]

            # New region containing end is new r_prine
            self.regions[0] = r_prime_new
            # Get rid of old r_prime
            self.regions.pop(pair_ri)
            self.regions.extend([r_left,r_right])

    # ------------------------------------------------------------------ debug

    def state(self) -> str:
        lines = ["Regions("]
        for i, r in enumerate(self.regions):
            marker = "  <- END (path-end is just before index 0)" \
                     if i == 0 else ""
            lines.append(f"  [{i}] {r}{marker}")
        lines.append(")")
        lines.append(f"gen = {self.gen}")
        return "\n".join(lines)


# R = Regions(3)
# R.forward(2)
# R.forward(3)
# R.forward(3)
# R.forward(-6)
# R.forward(-2)
# print(R.regions)
