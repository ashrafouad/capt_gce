def cache_init(src, tgt):
    return [[-1] * (len(src) + 1) for _ in range(len(tgt) + 1)]


def a(src, tgt, cache=None):
    if not len(src) * len(tgt):
        return len(src) * len(tgt)

    if not cache:
        cache = cache_init(src, tgt)

    source_len, target_len = len(src), len(tgt)

    def loop(i: int, j: int) -> int:
        if i >= source_len:
            return target_len - j
        elif j >= target_len:
            return source_len - i
        elif cache[j][i] >= 0:
            return cache[j][i]
        elif src[i] == tgt[j]:
            cache[j][i] = loop(i + 1, j + 1)
            return cache[j][i]
        else:
            cache[j][i] = 1 + min(loop(i + 1, j), loop(i, j + 1), loop(i + 1, j + 1))
            return cache[j][i]

    return loop(0, 0)


def edit_sequence(src, tgt, cache=None):
    if not src:
        return list(map(lambda x: ("insert", x), range(len(tgt))))
    if not tgt:
        return list(map(lambda x: ("remove", x), range(len(src))))

    if not cache:
        cache = cache_init(src, tgt)
        a(src, tgt, cache)

    res = []
    i, j = 0, 0
    while i < len(cache) - 1 and j < len(cache[0]) - 1:
        if tgt[i] == src[j]:
            i += 1
            j += 1
            continue

        remove = cache[i][j + 1] if cache[i][j + 1] > -1 else float("inf")
        insert = cache[i + 1][j] if cache[i + 1][j] > -1 else float("inf")
        replace = cache[i + 1][j + 1] if cache[i + 1][j + 1] > -1 else float("inf")

        minimum = min(replace, remove, insert)

        if replace == minimum:
            res.append((j, i))
            i += 1
            j += 1
        elif remove == minimum:
            res.append(("remove", j))
            j += 1
        elif insert == minimum:
            res.append(("insert", i))
            i += 1

    if i < len(tgt):
        if j < len(src) and tgt[i] == src[j]:
            i += 1
        res += list(map(lambda x: ("insert", x), range(i, len(tgt))))
    elif j < len(src):
        if i < len(tgt) and tgt[i] == src[j]:
            j += 1
        res += list(map(lambda x: ("remove", x), range(j, len(src))))

    return res


RED = "\033[97;41m"
GREEN = "\033[97;42m"
YELLOW = "\033[97;43m"
END = "\033[0m"


def red(input):
    return RED + input + END


def green(input):
    return GREEN + input + END


def yellow(input):
    return YELLOW + input + END


def color_output(source, target, sequence):
    s, t = "", ""
    i, j = 0, 0
    for op, y in sequence:
        if op == "insert":
            offset = y - j
            s += source[i : i + offset] + green(" ")
            t += target[j : j + offset] + green(target[y])
            i += offset
            j = y + 1
        elif op == "remove":
            offset = y - i
            s += source[i : i + offset] + red(source[y])
            t += target[j : j + offset] + red(" ")
            i = y + 1
            j += offset
        elif isinstance(op, int):
            s_offset = op - i
            t_offset = y - j
            s += source[i : i + s_offset] + source[op]
            t += target[j : j + t_offset] + yellow(target[y])
            i = op + 1
            j = y + 1
    s += source[i:]
    t += target[j:]
    return s, t


def html_output(source, target, sequence=None):
    if not sequence:
        sequence = edit_sequence(source, target)
    s, t = "", ""
    i, j = 0, 0
    for op, y in sequence:
        if op == "insert":
            offset = y - j
            s += source[i : i + offset] + '<span class="_added_fade">_</span>'
            t += target[j : j + offset] + f'<span class="_added">{target[y]}</span>'
            i += offset
            j = y + 1
        elif op == "remove":
            offset = y - i
            s += source[i : i + offset] + f'<span class="_removed">{source[y]}</span>'
            t += target[j : j + offset] + '<span class="_removed_fade">-</span>'
            i = y + 1
            j += offset
        elif isinstance(op, int):
            s_offset = op - i
            t_offset = y - j
            s += source[i : i + s_offset] + source[op]
            t += target[j : j + t_offset] + f'<span class="_mod">{target[y]}</span>'
            i = op + 1
            j = y + 1
    s += source[i:]
    t += target[j:]
    return s, t
