#!/usr/bin/env python3

import os
import sys
import argparse
import tempfile
import datetime

parser = argparse.ArgumentParser(
    usage = "pbpaste | %(prog)s [options]",
    description="Split a long command into multiple lines. It's useful to make swiftc/clang commands more readable.",
)
parser.add_argument("-l", "--new-line-escape", action=argparse.BooleanOptionalAction, help="print '\\' to escape new lines")
parser.add_argument("-s", "--save", action=argparse.BooleanOptionalAction, help="save the output an file")
args = parser.parse_args()

words = sys.stdin.read().split()

SCRIPT_BEGIN = """
local ARGS=(
"""
SCRIPT_END = """)

set -x
${ARGS[@]}
"""

if len(words) == 0:
    sys.stderr.write("No input.\n")
    exit(1)

if args.save:
    # Force not to print new line escape if outputing to a file, because we are using an array
    args.new_line_escape = False

    timestamp = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    fd, filepath = tempfile.mkstemp(suffix=".sh", prefix=f"po_{timestamp}_", dir=os.getcwd())

    fp = open(filepath, 'w+')
    fp.write(SCRIPT_BEGIN)
else:
    fp = sys.stdout

fp.write(words[0])
previous_word = words[0]

for word in words[1:]:
    if word.endswith(('.swift', '.m', '.c', '.cpp', '.mm')):
        separator = " \\\n" if args.new_line_escape else "\n"
    elif previous_word.startswith("-X"):
        separator = " "
    elif word.startswith("-") or word.startswith("@"):
        separator = " \\\n" if args.new_line_escape else "\n"
    else:
        separator = " "

    fp.write(f"{separator}{word}")
    previous_word = word

fp.write("\n")

if args.save:
    fp.write(SCRIPT_END)
    # Dump the file before closing
    fp.seek(0)
    print(fp.read())
    fp.close()

    sys.stdout.write(f"\033[34mzsh {filepath}\033[0m\n")
