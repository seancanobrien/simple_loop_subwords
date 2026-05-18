import numpy as np

#Stolen from Simi:
def _validate_word(word: list[int], rank: int) -> None:
    """
    Validates that a word is a valid reduced word of given rank.

    Raises:
            TypeError: If the word contains something other than a non-zero integer
            ValueError: If there is another formatting issue.
    """

    if not isinstance(word, list) or not word:
        raise ValueError("word must be a non-empty list")
    for i, s in enumerate(word):
        if not isinstance(s, int) or s == 0:
            raise TypeError(f"word[{i}] must be a non-zero integer, got {s!r}")
        if abs(s) > rank:
            raise ValueError(f"word[{i}] has abs value {abs(s)} > rank {rank}")
        
#freely reduce words
def reduce(w):
    for i in range(len(w)-1):
        if w[i]==-1*w[i+1]:
            w[i]='n'
            w[i+1]='n'
    return[x for x in w if x != 'n']

'''
Action of the braid group generators
sigma_i(i)=(i)(i+1)(-i)
sigma_i(i+1)=i
sigma_i(j)=j otherwise
(inverses -> inverses)
'''
def sigma(i,w):
    w=reduce(w)
    j=0
    while j<len(w):
        if w[j]==i:
            w.insert(j+1,i+1)
            w.insert(j+2,-i)
            j+=3
        elif w[j]==-i:
            w.insert(j,i)
            w.insert(j+1,-(i+1))
            j+=3
        elif w[j]==i+1:
            w[j]=i
            j+=1
        elif w[j]==-(i+1):
            w[j]=-i
            j+=1
        else:
            j+=1
    return reduce(w)


#Compute all possible words which can be obtained by applying one of the braid generators to a given word w in the free group of rank n
def braids(n,w):
    _validate_word(w,n)
    b=[]
    for i in range(1,n):
        if sigma(i,w) not in b:
            b.append(sigma(i,w))
    return b

#Compute all possible words of length up to a given max which can be obtained by braiding a given word w in the free group of given rank
def all_braids(rank,w,max_length):
    _validate_word(w,rank)
    #more checks
    if len(w)>max_length:
        raise ValueError(f"word has length {len(w)} > max length {max_length}")
    if not isinstance(rank, int) or rank<1:
        raise ValueError("rank must be a positive integer")
    if not isinstance(max_length, int) or rank<1:
        raise ValueError("max_length must be a positive integer")
    b=[w]
    j=0
    while j<len(b):
        for u in braids(rank,b[j]):
            if len(u)<=max_length and u not in b:
                b.append(u)
        j+=1
    return b
print(all_braids(3,[1],32))





    