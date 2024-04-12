#!/usr/bin/env python3

import sys
import json
import re
import argparse
import os
from colorama import Fore, Style


def is_process_event(event):
    return "exec" in event


def match_pattern(name, pattern):
    return (pattern is None) or re.search(name, pattern)


def filter_eslogger(name_pattern, show_child_process=False):
    pid_set = set()

    for line in sys.stdin:
        try:
            data = json.loads(line)
            event = data["event"]
            process = data["process"]
            pid = process["parent_audit_token"]["pid"] if is_process_event(event) else process["audit_token"]["pid"]
            executable_path = process["executable"]["path"]
            executable_name = os.path.basename(executable_path)

            if (pid not in pid_set) and (not match_pattern(executable_name, name_pattern)):
                continue

            print(f'{Fore.GREEN}{executable_name}({pid}){Style.RESET_ALL} ', end="")

            if "exec" in event:
                child_pid = event["exec"]["target"]["audit_token"]["pid"]

                if show_child_process:
                    pid_set.add(child_pid)

                args = event["exec"]["args"]
                print(f'[EXEC]({child_pid}) {" ".join(args)}')
            elif "open" in event:
                print(f'[OPEN] {event["open"]["file"]["path"]}')
            elif "write" in event:
                print(f'[WRITE] {event["write"]["target"]["path"]}')
            elif "create" in event:
                print(f'[CREATE] {event["create"]["destination"]["existing_file"]["path"]}')

        except json.JSONDecodeError:
            print(f"Failed to parse JSON: {line.strip()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        usage="sudo eslogger exec [open write ...] | %(prog)s [options]",
        description="Filter the output of `eslogger` to only show cared processes and information.",
        epilog="""
examples:
  Monitor all the processes spawned by Xcode and related process:
    sudo eslogger exec | eslogger-filter.py --name="(Xcode|XCBBuildService|SourceKitService|com.apple.dt.SKAgent)" --show-child-process

  Monitor open files by Slack
    sudo eslogger open | eslogger-filter.py --name="Slack" --show-child-process

For more information about `eslogger`, please refer to `man eslogger`.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-n", "--name", type=str, required=False,
                        help="Regex pattern for matching process names. Omitting this will log all processes.")
    parser.add_argument("-c", "--show-child-process", action="store_true",
                        help="Include child processes of the processes matched by --name.")
    args = parser.parse_args()

    try:
        filter_eslogger(args.name, args.show_child_process)
    except KeyboardInterrupt:
        sys.exit(0)
