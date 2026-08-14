import itertools
from regions import (
    make_state,
    forward,
    seg_possibilities_given_gen
)

# ------------------------------------------------
# Advance a set of states according to next letter
# For doing breadth first search.
# Pruning is automatic
# ------------------------------------------------
def _advance(states: set, letter: int) -> set:
    return {forward(s, seg) for s in states for seg in seg_possibilities_given_gen(s, letter)}

# ------------------------------------------------
# evaluate (signed word)
# ------------------------------------------------
def evaluate(n: int, word: list[int]) -> bool:
    _validate_word(word, n)
    states = {make_state(n)}
    for letter in word:
        states = _advance(states, letter)
        if not states:
            return False
    return True

# ------------------------------------------------
# evaluate_unsigned
# ------------------------------------------------
def valid_assignment_of_signs(n: int, word: list[int]) -> list[int] | None:
    _validate_word(word, n)
    frontier = [({make_state(n)}, [])]
    for letter in word:
        next_frontier = []
        for states, path in frontier:
            for signed_letter in (letter, -letter):
                next_states = _advance(states, signed_letter)
                if next_states:
                    next_frontier.append((next_states, path + [signed_letter]))
        if not next_frontier:
            return None
        frontier = next_frontier
    return frontier[0][1] if frontier else None

# ------------------------------------------------
# evaluate_all_perms_and_signs
# ------------------------------------------------
def valid_permutation_and_assignment_of_signs(n: int, word: list[int]) -> list[int] | None:
    _validate_word(word, n)
    symbols = sorted(set(word))
    for perm in itertools.permutations(symbols):
        mapping = dict(zip(symbols, perm))
        relabelled = [mapping[x] for x in word]
        assignment = valid_assignment_of_signs(n, relabelled)
        if assignment is not None:
            return assignment
    return None

# ------------------------------------------------
# Validate format of word
# ------------------------------------------------
def _validate_word(word: list[int], rank: int, check_for_squares = True) -> None:
    if not isinstance(word, list) or not word:
        raise ValueError("word must be a non-empty list")
    for i, s in enumerate(word):
        if not isinstance(s, int) or s == 0:
            raise TypeError(f"word[{i}] must be a non-zero integer, got {s!r}")
        if abs(s) > rank:
            raise ValueError(f"word[{i}] has abs value {abs(s)} > rank {rank}")
    for i in range(len(word) - 1):
        if word[i] == -word[i + 1]:
            raise ValueError(f"word is not reduced at positions {i}, {i + 1}")
        if check_for_squares and word[i] == word[i + 1]:
            raise ValueError(f"word has repeated letter at positions {i}, {i + 1}")
