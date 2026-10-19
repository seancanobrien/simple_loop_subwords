# Testing

Run any suite directly, from the repository root:

```bash
python3 test/test_corpus.py
python3 test/test_coexistence.py
python3 test/test_boundary.py
```

or call `run_tests()` in an interactive session (`python3 -i main.py`) to run all three.

## Corpora

`subwords/` holds words one per line, in Python list notation:

| file | expectation |
|---|---|
| `known_valid.txt` | hand-curated; every word drawable |
| `known_non_valid.txt` | hand-curated; no word drawable |
| `braid_orbit_braidlength{k}_rank{n}.txt` | simple words from the braid orbit of $x_1$, so every word is drawable and any `False` is a bug |
| `mostly_non_valid.txt` | large and mixed, no per-line ground truth; reported as a tally |

## Suites

**`test_corpus.py`** runs `can_exist` over each corpus with `permute=False, respect_signs=True`,
so every word is taken as written, and checks the tallies.

**`test_coexistence.py`** needs no corpus. It checks that:
- one-word families agree with `searching.py` under every combination of the flags (the two
  are independent implementations, so this is the sharpest check);
- a witness exists exactly when the answer is `True`, and replays as drawable;
- the default rank agrees with a larger one;
- co-existence does not depend on the order of the words, and holds for sub-families of a
  co-existing family;
- multi-arc configurations satisfy the [invariants](../docs/implementation.md#invariants);
- `forward_new_arc` reproduces the original first-crossing formulas on the initial state.

**`test_boundary.py`** covers words with a `0` at either end:
- every braid-orbit word `w` is a loop based on the boundary, so `[0] + w + [0]`, and each
  suffix of `w` followed by `0`, must be drawable;
- reversing an arc reverses its word, inverts every letter and swaps its ends, so `[0] + w` must
  agree with its reverse ending in `0`. Starting and ending on the boundary are separate code,
  so this is the sharpest check here;
- freeing an end never makes a word undrawable;
- the `test_coexistence.py` properties hold with boundary words too;
- `0` is accepted only at the ends, and a few discriminating cases are pinned.

## Regenerating the braid-orbit corpus

```bash
python3 test/braid_orbit.py
```

This takes the orbit of $x_1$ under all reduced braid words up to a given length. It is
exponential in that length; the committed file takes minutes.
