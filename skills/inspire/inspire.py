#!/usr/bin/env python3
"""Inspiration dice: draw mid-surprisal English words.

The word list is vendored in words.txt. Bounds are intentionally constant:
words were selected from wordfreq's top 50k English list with Zipf frequency
3.0 <= z <= 4.7, a simple middle-frequency/surprisal band.
"""

from pathlib import Path
import argparse
import random

SIZE = 3
WORD_LIST = Path(__file__).with_name("words.txt")


def load_words():
    return [line.rstrip("\n") for line in WORD_LIST.read_text(encoding="utf-8").splitlines() if line]


def main():
    parser = argparse.ArgumentParser(description="Draw exactly three inspiration words from a fixed mid-surprisal English word list.")
    parser.add_argument("--seed", type=int, help="optional random seed for reproducible draws")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    print(" / ".join(random.sample(load_words(), SIZE)))


if __name__ == "__main__":
    main()
