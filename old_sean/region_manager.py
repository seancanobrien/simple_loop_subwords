import itertools
from regions import *

"""
RegionsManager: manages Regions instances to perform depth first search to
evaluate whether the subword can be drawn using a simple path.

evaluate
-----------
Given a signed word, do DFS on that signed word.

evaluate_unsigned
-----------
Given an unsigned word, do DFS on every assignment of signs on that unsigned
word.

evaluate_all_perms_and_signs
-----------
Given an unsigned word, do DFS on every assignment of signs and every
permutation of the letters in that word. E.g. [1,-2,-1] -> [2, -1, -2] is a
permutation.
"""
class RegionsManager:
    def __init__(self, n: int):
        self.n = n

    # ------------------------------------------------
    # evaluate using DFS (depth first search) all possibilities
    def evaluate(self, word: list[int]) -> bool:
        """
        Return True if any valid branch completes the word.
        """
        initial = Regions(self.n)
        return self._dfs(initial, word, 0)

    def _dfs(self, regions: Regions, word: list[int], idx: int) -> bool:
        # If we've consumed the whole word then success
        if idx == len(word):
            return True

        letter = word[idx]
        options = regions.seg_possibilities_given_gen(letter)
        # print(options)

        # Dead branch
        if not options:
            return False

        # Try each branch
        for seg in options:
            new_regions = regions.clone()
            new_regions.forward(seg)

            if self._dfs(new_regions, word, idx + 1):
                return True  # short-circuit on success

        # All branches failed
        return False

    # --------------------------------------------------
    # handles +- choices during DFS
    def evaluate_unsigned(self, word: list[int]) -> bool:
        success, assignment = self._dfs_unsigned(Regions(self.n), word, 0, [])
        
        if success:
            print("Successful signed word:", assignment)
            return True
        return False


    def _dfs_unsigned(self, regions: Regions, word: list[int], idx: int, path: list[int]):
        if idx == len(word):
            return True, path

        letter = word[idx]

        for signed_letter in (letter, -letter):
            options = regions.seg_possibilities_given_gen(signed_letter)

            if not options:
                continue

            for seg in options:
                new_regions = regions.clone()
                new_regions.forward(seg)

                success, result_path = self._dfs_unsigned(
                    new_regions,
                    word,
                    idx + 1,
                    path + [signed_letter]
                )

                if success:
                    return True, result_path

        return False, None

    # --------------------------------------------------
    # permutations + signs
    def evaluate_all_perms_and_signs(self, word: list[int]) -> bool:
        symbols = sorted(set(word))

        for perm in itertools.permutations(symbols):
            mapping = dict(zip(symbols, perm))
            relabelled = [mapping[x] for x in word]

            success, assignment = self._dfs_unsigned(
                Regions(self.n),
                relabelled,
                0,
                []
            )

            if success:
                print("Successful permutation:", mapping)
                print("Relabelled word:", relabelled)
                print("Successful signed word:", assignment)
                return True

        return False
