from regions import *
from searching import *

print("---------------\n Regions Demo\n--------------")
# We specify the number of punctures in the disk in __init__. Here = 5
s = make_state(5)
print(f"Single region before any intersections:\n>> {s.regions}")

s = forward(s, 2)
print(f"\nSingle region has new segment and is rotated \
after passing through segment 2:\n>> {s.regions}")

s = forward(s, 2)
print(f"\nMultiple regions after passing through segment 2 again:\n\
(Note that 'region containing end' is always at index 0 of self.regions)\n\
>> {s.regions}")

print(f"\nWe see that we cannot next do the letter '-3' using \
'seg_possibilties_given_gen'\n>> {seg_possibilities_given_gen(s,-3)}")
print(f"Or using 'gen_possibilties'\n>> {gen_possibilities(s)}")

print("\n\n---------------\n RegionsManager Demo\n--------------")
# We also specify the number of punctures in the disk in __init__ here
print("There are sometimes multiple segments that we can pass through \
to get the required generator.\n\
So DFS search is used to search through possibilities, \
managed by the 'RegionsManager' class.")

print(f"\nWe can see [1,2,-1] can be drawn:\n>> {evaluate(5,[1,2,-1])}")

print(f"\nWe can see [1,2,-1,-3,2,3] cannot be drawn:\n>> {evaluate(5, [1,2,-1,-3,2,3])}")

print(f"\nIn fact [1,2,1,3,2,3] cannot be drawn with\n\
any +- assignment to these letters:\n>> {not valid_assignment_of_signs(5, [1,2,1,3,2,3]) is None}")
print(f"\n.. and no matter how we permute these letters\n\
>> {not valid_permutation_and_assignment_of_signs(5, [1,2,1,3,2,3]) is None}")

