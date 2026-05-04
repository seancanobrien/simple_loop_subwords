from region_manager import *

print("---------------\n Regions Demo\n--------------")
# We specify the number of punctures in the disk in __init__. Here = 5
R = Regions(5)
print(f"Single region before any intersections:\n>> {R.regions}")

R.forward(2)
print(f"\nSingle region has new segment and is rotated \
after passing through segment 2:\n>> {R.regions}")

R.forward(2)
print(f"\nMultiple regions after passing through segment 2 again:\n\
(Note that 'region containing end' is always at index 0 of self.regions)\n\
>> {R.regions}")

print(f"\nWe see that we cannot next do the letter '-3' using \
'seg_possibilties_given_gen'\n>> {R.seg_possibilities_given_gen(-3)}")
print(f"Or using 'gen_possibilties'\n>> {R.gen_possibilities()}")

print("\n\n---------------\n RegionsManager Demo\n--------------")
# We also specify the number of punctures in the disk in __init__ here
M = RegionsManager(5)
print("There are sometimes multiple segments that we can pass through \
to get the required generator.\n\
So DFS search is used to search through possibilities, \
managed by the 'RegionsManager' class.")

print(f"\nWe can see [1,2,-1] can be drawn:\n>> {M.evaluate([1,2,-1])}")

print(f"\nWe can see [1,2,-1,-3,2,3] cannot be drawn:\n>> {M.evaluate([1,2,-1,-3,2,3])}")

print(f"\nIn fact [1,2,1,3,2,3] cannot be drawn with\n\
any +- assignment to these letters:\n>> {M.evaluate_unsigned([1,2,1,3,2,3])}")
print(f"\n.. and no matter how we permute these letters\n\
>> {M.evaluate_all_perms_and_signs([1,2,1,3,2,3])}")

