import copy
import time


class Arrangement:
    """
    The class used to represent an arrangement, i.e. an embedded path through the n-punctured disc, with fixed arcs from
    each puncture to the boundary.
    Possibly having this be a class is massive overkill, and probably slows performance.
    But I am an object-oriented man in an object-oriented body, and also this was the first thing I thought of.

    Attributes:
        puncture_count: Number of punctures.
        edge_count:     Current number of edges; starts at puncture_count + 1.
        regions:        List of lists whose flattened form is
                        [-edge_count, ..., -1, 1, ..., edge_count].
                        Each list represents a region by giving the boundary word.
                        The first region is the one with the current head of the path.
        assignment:     Dict mapping each edge integer in [1, ..., edge_count]
                        to a puncture in [1, ..., puncture_count], i.e. which letter does each edge correspond to.
    """

    def __init__(self, puncture_count: int, start_letter: int) -> None:
        """
        Initialise an Arrangement for n punctures starting with letter k.

        Args:
            puncture_count: Number of punctures. Must be >= 1.
            start_letter: First letter. Must satisfy -n <= k <= n, k != 0.

        Raises:
            TypeError:  If n or k are not integers.
            ValueError: If n < 1, or k is out of range or zero.
        """

        # Type check the input
        if not isinstance(puncture_count, int) or not isinstance(start_letter, int):
            raise TypeError(f"n and k must be integers, got {type(puncture_count).__name__} and {type(start_letter).__name__}")
        if puncture_count < 1:
            raise ValueError(f"n must be at least 1, got {puncture_count}")
        if start_letter == 0:
            raise ValueError("k must be non-zero")
        if abs(start_letter) > puncture_count:
            raise ValueError(f"abs(k) must be <= n, got k={start_letter}, n={puncture_count}")

        # Initialise values
        self.puncture_count: int = puncture_count
        self.edge_count: int = puncture_count + 1
        self.regions: list[list[int]] = self._generate_start_region(puncture_count, start_letter)
        self.assignment: dict[int, int] = {i: i for i in range(1, puncture_count + 1)}
        self.assignment[puncture_count + 1] = abs(start_letter)


    @staticmethod
    def _generate_start_region(n: int, k: int) -> list[list[int]]:
        """
        Generate the starting region for given n = puncture_count and k = starting letter.
        Not entirely sure why I wanted this as a separate method but it's probably good practice.

        Args:
            n: Number of punctures. Must be >= 1.
            k: Starting letter of word. Must satisfy -n <= k <= n, k != 0.

        Returns:
                The starting region as a list of lists of length 1.
        """
        if k > 0:
            arrangement = [-(n + 1)]
            for i in range(k + 1, n + 1):
                arrangement += [i, -i]
            for i in range(1, k):
                arrangement += [i, -i]
            arrangement.append(n + 1)
            arrangement += [k, -k]
        else:
            arrangement = [n + 1, -(n + 1), k]
            for i in range(-k + 1, n + 1):
                arrangement += [i, -i]
            for i in range(1, -k):
                arrangement += [i, -i]
            arrangement.append(-k)

        return [arrangement]


    def update_window(self, window: int) -> None:
        """
        Update the arrangement when passing through a window.

        Args:
            window: A valid window: a non-zero integer present in the first
                    sublist whose negation is NOT also in the first sublist.

        Raises:
            ValueError: If window is not in the first sublist, if -window is
                        also in the first sublist, or if -window is not found
                        anywhere.
        """

        first = self.regions[0]
        next_edge = self.edge_count + 1

        # Some data validation, no longer necessary, but good to keep
        if window not in first:
            raise ValueError(f"{window} is not in the first sublist: {first}")
        if -window in first:
            raise ValueError(f"Both {window} and {-window} appear in the first sublist: {first}")

        # Located which region we're going into, and finds index of edge
        neg_window_sublist_idx = None
        for i, sub in enumerate(self.regions):
            if -window in sub:
                neg_window_sublist_idx = i
                break
        if neg_window_sublist_idx is None:
            raise ValueError(f"{-window} not found in any sublist")

        sign = 1 if window > 0 else -1
        signed_next_edge = sign * next_edge

        # Split the previous "first" region
        # [{sublist a}, window, {sublist b}]
        #   -> [{sublist a}, signed_next_edge]  and  [window, {sublist b}]
        w_idx = first.index(window)
        new_first   = first[:w_idx] + [signed_next_edge]
        new_after_w = [window] + first[w_idx + 1:]

        # Update new region
        # [{sublist c}, -window, {sublist d}]
        #   -> [-signed_next_edge, {sublist d}, {sublist c}, -window]
        neg_w_sub = self.regions[neg_window_sublist_idx]
        neg_w_idx = neg_w_sub.index(-window)
        new_front = (
            [-signed_next_edge]
            + neg_w_sub[neg_w_idx + 1:]
            + neg_w_sub[:neg_w_idx]
            + [-window]
        )

        # Move the new "first" region to the front
        result = [new_front, new_first, new_after_w]
        for i, sub in enumerate(self.regions[1:], start=1):
            if i != neg_window_sublist_idx:
                result.append(sub)

        # Update attributes
        self.regions = result
        self.edge_count = next_edge
        self.assignment[next_edge] = self.assignment[abs(window)]


    def update_endpoint(self, endpoint: int) -> None:
        """
        Update the arrangement when passing through an endpoint.

        Args:
            endpoint: A valid endpoint: non-zero integer such that abs(endpoint) and -abs(endpoint)
                      appear as a consecutive pair in the first sublist.

        Raises:
            ValueError: If [abs(endpoint), -abs(endpoint)] is not a
                        consecutive pair in the first sublist.
        """

        next_edge = self.edge_count + 1
        pos_endpoint = abs(endpoint)
        first = self.regions[0]

        # Finds index of edge, with some bonus unnecessary validation
        n_idx = None
        for i in range(len(first) - 1):
            if first[i] == pos_endpoint and first[i + 1] == -pos_endpoint:
                n_idx = i
                break
        if n_idx is None:
            raise ValueError(
                f"[{pos_endpoint}, {-pos_endpoint}] is not a consecutive pair "
                f"in the first sublist: {first}"
            )

        # Splits the region
        a = first[:n_idx]
        b = first[n_idx + 2:]

        if endpoint > 0:
            new_front = [-next_edge] + b + [pos_endpoint, -pos_endpoint]
            new_first = a + [next_edge]
        else:
            new_front = [next_edge, -next_edge] + a + [pos_endpoint]
            new_first = [-pos_endpoint] + b

        # Updates the attributes
        self.regions = [new_front, new_first] + self.regions[1:]
        self.edge_count = next_edge
        self.assignment[next_edge] = self.assignment[abs(endpoint)]


    def update_mirror(self, mirror: int) -> None:
        """
        Updates the arrangement when passing through a mirror.
        mirror and -mirror must both appear in the first region, but NOT as a
        consecutive pair.

        Args:
            mirror: A non-zero integer. Both mirror and -mirror must appear in
                    the first region, but not as a consecutive pair.

        Raises:
            ValueError: If mirror or -mirror is absent from the first region,
                        or if they appear as a consecutive pair.
        """

        first = self.regions[0]

        # Bonus unnecessary validation
        if mirror not in first:
            raise ValueError(f"{mirror} is not in the first region: {first}")
        if -mirror not in first:
            raise ValueError(f"{-mirror} is not in the first region: {first}")

        pos_idx = first.index(mirror)
        neg_idx = first.index(-mirror)

        # Check they are not a consecutive pair [abs(mirror), -abs(mirror)]. Strictly unnecessary
        abs_mirror = abs(mirror)
        for i in range(len(first) - 1):
            if first[i] == abs_mirror and first[i + 1] == -abs_mirror:
                raise ValueError(
                    f"[{abs_mirror}, {-abs_mirror}] appears as a consecutive pair "
                    f"in the first region; use update_endpoint instead: {first}"
                )

        next_edge = self.edge_count + 1
        puncture = self.assignment[abs(mirror)]
        sign = 1 if mirror > 0 else -1
        signed_next_edge = sign * next_edge

        if neg_idx < pos_idx:
            # first = [{a}, -mirror, {b}, mirror, {c}] ->
            # [-signed_next_edge, {b}, signed_next_edge, {a}, -mirror],  [mirror, {c}]
            a = first[:neg_idx]
            b = first[neg_idx + 1:pos_idx]
            c = first[pos_idx + 1:]
            new_front = [-signed_next_edge] + b + [signed_next_edge] + a + [-mirror]
            new_second = [mirror] + c
        else:
            # [{a}, mirror, {b}, -mirror, {c}] ->
            # [-signed_next_edge, {c}, mirror, {b}, -mirror], [{a}, signed_next_edge]
            a = first[:pos_idx]
            b = first[pos_idx + 1:neg_idx]
            c = first[neg_idx + 1:]
            new_front = [-signed_next_edge] + c + [mirror] + b + [-mirror]
            new_second = a + [signed_next_edge]

        self.regions = [new_front, new_second] + self.regions[1:]
        self.edge_count = next_edge
        self.assignment[next_edge] = puncture



    def update(self, k: int) -> None:
        """
        Update the arrangement by calling update_endpoint or update_window appropriately.

        Args:
            k: A non-zero integer with abs(k) <= edge_count.

        Raises:
            TypeError:  If k is not a non-zero integer.
            ValueError: If abs(k) > edge_count, or if neither condition for
                        update_endpoint nor update_window is met.
        """

        # Data validation, checks that k is a valid edge.
        if not isinstance(k, int) or k == 0:
            raise TypeError(f"k must be a non-zero integer, got {k!r}")
        if abs(k) > self.edge_count:
            raise ValueError(f"abs(k) must be <= edge_count ({self.edge_count}), got {k}")

        first = self.regions[0]
        pos_k = abs(k)

        # Check for endpoint: is [abs(k), -abs(k)] a consecutive pair in first
        for i in range(len(first) - 1):
            if first[i] == pos_k and first[i + 1] == -pos_k:
                self.update_endpoint(k)
                return

        # Check for window and mirror: is k in first
        if k in first:
            if -k in first: # is it a mirror
                self.update_mirror(k)
            else:
                self.update_window(k)
            return

        # Otherwise
        raise ValueError(
            f"Cannot update with k={k}: {k} is not in the first region: {first}"
        )

    # String representation, for if you want to print out an arrangement
    def __repr__(self) -> str:
        return (
            f"Arrangement(puncture_count={self.puncture_count}, "
            f"edge_count={self.edge_count}, "
            f"regions={self.regions}, "
            f"assignment={self.assignment})"
        )


def is_reduced(subword: list[int]) -> bool:
    """
    Check whether a subword is reduced.

    Args:
        subword: A list of non-zero integers.

    Returns:
        True if reduced, False otherwise.
    """
    return all(subword[i] != -subword[i + 1] for i in range(len(subword) - 1))


def check_subword(rank: int, subword: list[int]) -> bool:
    """
    Check whether subword is realisable.

    Args:
        rank:    A positive integer, the number of punctures.
        subword: A non-empty reduced list of non-zero integers, each with
                 abs value <= rank.

    Returns:
        True if possible_arrangements is non-empty after processing all of
        subword, False if it becomes empty at any point.

    Raises:
        TypeError:  If rank is not a positive integer, or subword is not a
                    list of non-zero integers.
        ValueError: If subword is empty, any entry has abs value > rank,
                    or subword is not reduced.
    """

    # Actually important data validation
    # Checks: rank is positive integer; subword is non-empty list; subword is made of letters; subword is reduced
    if not isinstance(rank, int) or rank <= 0:
        raise TypeError(f"rank must be a positive integer, got {rank!r}")
    if not isinstance(subword, list) or not subword:
        raise ValueError("subword must be a non-empty list")
    for i, s in enumerate(subword):
        if not isinstance(s, int) or s == 0:
            raise TypeError(f"subword[{i}] must be a non-zero integer, got {s!r}")
        if abs(s) > rank:
            raise ValueError(f"subword[{i}] has abs value {abs(s)} > rank {rank}")
    if not is_reduced(subword):
        for i in range(len(subword) - 1):
            if subword[i] == -subword[i + 1]:
                raise ValueError(
                    f"subword is not reduced: entries at positions {i} and {i+1} "
                    f"are {subword[i]} and {subword[i+1]}"
                )

    # This is probably not the most efficient way to search all options, but it works.
    possible_arrangements = [Arrangement(rank, subword[0])]

    # Main loop. For each arrangement, and each reachable edge of the next letter, creates a new arrangement passing
    # through that edge.
    # Deepcopy is fairly slow. It doesn't really matter, but if we want it to be more efficient we could just store
    # each arrangement as a tuple so it copies better. I'll work on this next.
    for s in subword[1:]:
        new_possible_arrangements = []
        for arr in possible_arrangements:
            for edge in arr.regions[0]:
                if arr.assignment[abs(edge)] == abs(s) and (edge > 0) == (s > 0):
                    arr_copy = copy.deepcopy(arr)
                    arr_copy.update(edge)
                    new_possible_arrangements.append(arr_copy)
        possible_arrangements = new_possible_arrangements
        if not possible_arrangements:
            return False

    return True



def generate_reduced_words(rank, length):
    """
    Defines a generator for the list of all reduced words of given rank and length.
    I don't fully understand how yield works in python but hey ho.

    Args:
        rank: A positive integer, the number of punctures.
        length: A positive integer, the length of the word.
    """
    alphabet = list(range(-rank, 0)) + list(range(1, rank + 1))
    word = [None] * length

    def _recurse(pos):
        if pos == length:
            yield word[:]
            return
        for letter in alphabet:
            if pos == 0 or word[pos - 1] != -letter:
                word[pos] = letter
                yield from _recurse(pos + 1)

    yield from _recurse(0)



# ── Main ──────────────────────────────────────────────────────────────

RANK   = 5
LENGTH = 8

print(f"Generating all reduced words of rank {RANK}, length {LENGTH}...")
print(f"Expected count: {RANK*2 * 9**(LENGTH-1):,}")
print()

total      = 0
true_count = 0

t_start = time.perf_counter()
t_last  = t_start

for word in generate_reduced_words(RANK, LENGTH):
    result = check_subword(RANK, word)
    total += 1
    if result:
        true_count += 1

    # Progress report every 1,000,000 words
    if total % 1_000_000 == 0:
        t_now     = time.perf_counter()
        elapsed   = t_now - t_start
        rate      = total / elapsed
        remaining = (10 * 9**(LENGTH-1) - total) / rate
        print(
            f"  {total:>12,} words processed | "
            f"{true_count:>12,} True ({100*true_count/total:.2f}%) | "
            f"elapsed: {elapsed:6.1f}s | "
            f"rate: {rate:,.0f} words/s | "
            f"est. remaining: {remaining:.1f}s"
        )
        t_last = t_now

t_end   = time.perf_counter()
elapsed = t_end - t_start

print()
print("═" * 60)
print(f"  Total words     : {total:,}")
print(f"  True count      : {true_count:,}")
print(f"  False count     : {total - true_count:,}")
print(f"  Proportion True : {true_count/total:.6f}")
print(f"  Total time      : {elapsed:.2f}s")
print(f"  Rate            : {total/elapsed:,.0f} words/s")
print(f"  Time per word   : {elapsed/total*1e6:.2f} µs")
print("═" * 60)