"""
Generate a ground-truth corpus from the braid action.

The orbit Q = B_n . x_1 consists of words that all correspond to simple loops, so every
word in it is drawable by construction.  Running `evaluate` over a generated file is
therefore a regression test with no hand-curation involved: any False is a genuine bug.

Run this file directly to write the orbit of [1] to
test/subwords/braid_orbit_braidlength{k}_rank{n}.txt, one word per line.  Generation is
exponential in the braid length, so the defaults below are already slow (minutes).

The braid group acts on the free group by

    sigma_i(x_i)   = x_i x_{i+1} x_i^-1
    sigma_i(x_{i+1}) = x_i
    sigma_i(x_j)   = x_j                 otherwise

with inverses mapping to inverses.
"""

from pathlib import Path

SUBWORDS = Path(__file__).resolve().parent / "subwords"

RANK = 7
BRAID_LENGTH = 7


# ------------------------------------------------------------------ free group

def reduce(w: list[int]) -> list[int]:
    """
    Freely reduce a word, cancelling adjacent inverse pairs.

    One pass suffices: the output is reduced at every step, since each letter either
    cancels the letter on top of it or is appended to something it cannot cancel.  So a
    cancellation that brings a new pair together is resolved immediately -- [1,2,-2,-1]
    reduces to [], not to [1,-1].
    """
    out = []
    for letter in w:
        if out and out[-1] == -letter:
            out.pop()
        else:
            out.append(letter)
    return out


# ------------------------------------------------------------------ braid action

def sigma(i: int, w: list[int]) -> list[int]:
    """
    Apply the braid generator sigma_i (or its inverse, for i < 0) to the word w.

    The result is freely reduced, so w is assumed reduced on the way in -- which holds
    for every call `apply_braid` makes.
    """
    a = abs(i)
    result = []
    for letter in w:
        if i > 0:
            if letter == a:
                result.extend([a, a + 1, -a])
            elif letter == -a:
                result.extend([a, -(a + 1), -a])
            elif letter == a + 1:
                result.append(a)
            elif letter == -(a + 1):
                result.append(-a)
            else:
                result.append(letter)
        else:
            if letter == a:
                result.append(a + 1)
            elif letter == -a:
                result.append(-(a + 1))
            elif letter == a + 1:
                result.extend([-(a + 1), a, a + 1])
            elif letter == -(a + 1):
                result.extend([-(a + 1), -a, a + 1])
            else:
                result.append(letter)
    return reduce(result)


def apply_braid(braid_word: list[int], w: list[int]) -> list[int]:
    """
    Apply a braid word to w as a left action.

    [b1, ..., bm] acts as sigma(b1, sigma(b2, ..., sigma(bm, w)...)), so the generators
    are applied right to left.
    """
    result = list(w)
    for g in reversed(braid_word):
        result = sigma(g, result)
    return result


def braid_orbit(w: list[int], k: int, n: int) -> list[list[int]]:
    """
    The orbit of w under all reduced braid words of length <= k, in the braid group on
    n strands.  "Reduced" means no immediate cancellation: b_i != -b_{i+1}.

    Duplicates are dropped, so the result is one representative per distinct word.
    """
    generators = list(range(1, n)) + list(range(-(n - 1), 0))

    # Enumerate the reduced braid words of length <= k, level by level.
    braid_words = [[]]
    current_level = [[]]
    for _ in range(k):
        next_level = []
        for bw in current_level:
            last = bw[-1] if bw else None
            for g in generators:
                if last is None or g != -last:
                    new_bw = bw + [g]
                    next_level.append(new_bw)
                    braid_words.append(new_bw)
        current_level = next_level

    seen = set()
    results = []
    for bw in braid_words:
        result = apply_braid(bw, w)
        key = tuple(result)
        if key not in seen:
            seen.add(key)
            results.append(result)
    return results


# ------------------------------------------------------------------ script

def main(rank: int = RANK, braid_length: int = BRAID_LENGTH) -> int:
    """Write the orbit of [1] to test/subwords/, and report where it went."""
    orbit = braid_orbit([1], braid_length, rank)
    path = SUBWORDS / f"braid_orbit_braidlength{braid_length}_rank{rank}.txt"
    with open(path, "w") as f:
        for word in orbit:
            f.write(str(word) + "\n")
    print(f"wrote {len(orbit)} words to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
