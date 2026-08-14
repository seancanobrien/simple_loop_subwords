# Freely reduce words
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
def sigma(i, w):
    w = reduce(w)
    a = abs(i)
    result = []
    for letter in w:
        if i > 0:
            if letter == a:
                result.extend([a, a+1, -a])
            elif letter == -a:
                result.extend([a, -(a+1), -a])
            elif letter == a+1:
                result.append(a)
            elif letter == -(a+1):
                result.append(-a)
            else:
                result.append(letter)
        else:
            if letter == a:
                result.append(a+1)
            elif letter == -a:
                result.append(-(a+1))
            elif letter == a+1:
                result.extend([-(a+1), a, a+1])
            elif letter == -(a+1):
                result.extend([-(a+1), -a, a+1])
            else:
                result.append(letter)
    return reduce(result)

# Apply a braid (list of braid generators) to w as a left action
def apply_braid(braid_word, w):
    result = list(w)
    for g in reversed(braid_word):
        result = sigma(g, result)
    return result

# Returns the orbit of w under all reduced braid words of length <= k with rank n.
# A braid word [b1, b2, ..., bm] acts as sigma_new(b1, sigma_new(b2, ..., sigma_new(bm, w)...)).
# "Reduced" means no consecutive cancellation: b_i != -b_{i+1}.
def braid_orbit(w, k, n):
    generators = list(range(1, n)) + list(range(-(n-1), 0))

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

#Compute all possible words which can be obtained by applying one of the braid generators to a given word w in the free group of rank n
def braids(n,w):
    _validate_word(w,n)
    b=[w]
    for i in range(1,n):
        new_word = sigma(i,w)
        if not new_word in b:
            b.append(new_word)
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

# print(all_braids(3,[1],32))

rank = 7
braid_length = 7
orbit = braid_orbit([1], braid_length, rank)
with open(f"subwords/braid_orbit_braidlength{braid_length}_rank{rank}.txt", 'w') as f:
    for word in orbit:
        f.write(str(word) + '\n')
