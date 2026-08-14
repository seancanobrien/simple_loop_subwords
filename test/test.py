# to be able to access files above the test directory
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import ast
from searching import *

def evaluate_from_file(filename, rank=15):
    true_count = 0
    false_count = 0
    with open(filename) as f:
        for line in f:
            w = ast.literal_eval(line.strip())
            if evaluate(rank, w):
                true_count += 1
            else:
                false_count += 1
    return true_count, false_count

def report(filename):
    true_count, false_count = evaluate_from_file(filename)
    total = true_count + false_count
    print("------------------------------")
    print(f"File: {filename}")
    print(f"  True:  {true_count}/{total}")
    print(f"  False: {false_count}/{total}")

report("subwords/mostly_non_valid.txt")
report("subwords/known_valid.txt")
report("subwords/known_non_valid.txt")
report("subwords/braid_orbit_braidlength7_rank7.txt")
