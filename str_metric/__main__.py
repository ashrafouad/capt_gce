import sys
from datetime import datetime
from statistics import fmean

from html_template import GLOBAL_STYLE
from levenshtein import (
    a,
    cache_init,
    color_output,
    edit_sequence,
    html_output,
)


def benchmark(path="bench_sample.txt"):
    start = datetime.now()
    durations = []
    high_sep = "━" * 120
    low_sep = "─" * 120
    print(high_sep)
    print(f"Bench marking using {path}")
    print(low_sep)
    with open(path) as file:
        lines = file.readlines()

    prev = ""
    for _ in range(10_000):
        mini_start = datetime.now()
        for line in lines:
            line = line.strip()
            a(prev, line)
            prev = line
        durations.append(datetime.now() - mini_start)
    duration = datetime.now() - start

    durations = list(map(lambda d: d.total_seconds(), durations))
    mean = fmean(durations)
    print(f"Total duration: {duration}, μ = {mean} s")
    print(high_sep)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args:
        if args[0] == "bench":
            benchmark()
        else:
            source = args[0]
            target = args[1]
            cache = cache_init(source, target)
            a(source, target, cache)
            sequence = edit_sequence(source, target, cache)
            if len(args) == 2:
                source, target = color_output(source, target, sequence)
                print(source, target, sep="\n")
            elif args[2] == "html":
                source, target = html_output(source, target, sequence)
                print(
                    f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta encoding="utf-8">
        <title>Edit distance sequences</title>
        <style>{GLOBAL_STYLE}</style>
        </head>
        <body>
        <p>{source}</p>
        <p>{target}</p>
        </body>
        </html>
        """,
                )
