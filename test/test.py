# to be able to access files above the test directory
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import ast
from region_manager import *
from computing_project_v1 import *


def subject_sean(unsigned_word: list[int]) -> bool:
    M = RegionManager(5)
    return M.evaluate_unsigned(unsigned_word)

def subject_simi(unsigned_word: list[int]) -> bool:
    return evaluate_fn_at_all_signs(unsigned_word, lambda w: check_subword(5,w))


def evaluate_fn_at_all_signs(unsigned_word: list[int], eval_fn) -> bool:
        """
        word: list of positive integers (no signs)

        Try all ± assignments. Return True if any succeeds.
        """
        n = len(unsigned_word)

        for signs in itertools.product([1, -1], repeat=n):
            signed_word = [s * w for s, w in zip(signs, unsigned_word)]

            if eval_fn(signed_word):
                return True  # short-circuit immediately

        return False

agree_true = []
agree_false = []
disagree_simi_true_sean_false = []
disagree_simi_false_sean_true = []

with open("mostly_non_occuring_positive_words_formatted.txt") as f:
    for line in f:
        x = ast.literal_eval(line.strip())  # safely parse "[1,3,2,4]"

        s_sean = subject_sean(x)
        s_simi = subject_simi(x)

        if s_sean and s_simi:
            agree_true.append(x)
        elif not s_sean and not s_simi:
            agree_false.append(x)
        elif s_simi and not s_sean:
            disagree_simi_true_sean_false.append(x)
        elif not s_simi and s_sean:
            disagree_simi_false_sean_true.append(x)

# ---- report ----
print("Report")
print("------")
print(f"agree_true: {len(agree_true)}")
print(f"agree_false: {len(agree_false)}")
print(f"disagree_simi_true_sean_false: {len(disagree_simi_true_sean_false)}")
print(f"disagree_simi_false_sean_true: {len(disagree_simi_false_sean_true)}")

total = (len(agree_true) + len(agree_false) +
         len(disagree_simi_true_sean_false) +
         len(disagree_simi_false_sean_true))

print("------")
print(f"total: {total}")
