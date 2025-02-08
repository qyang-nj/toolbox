#!/usr/bin/env python3

import sys
import json
import re
import argparse
import os
from colorama import Fore, Style
import psutil


def match_pattern(name, pattern):
    """Check if the name matches the pattern. If pattern is None, return True (always match)."""
    return (pattern is None) or re.search(name, pattern)


def process_name(pid):
    """Get the process name by PID."""
    try:
        process = psutil.Process(pid)
        return process.name()
    except psutil.NoSuchProcess:
        return None


def filter_eslogger(name_pattern, show_child_process=False, show_env_vars=False):
    """Filter the output of `eslogger` to only show cared processes and information."""
    pid_set = set()

    for proc in psutil.process_iter():
        if match_pattern(proc.name(), name_pattern):
            pid_set.add(proc.pid)

    for line in sys.stdin:
        try:
            data = json.loads(line)
            event = data["event"]
            process = data["process"]
            pid = process["audit_token"]["pid"]
            ppid = process["parent_audit_token"]["pid"]
            responsible_pid = process["responsible_audit_token"]["pid"]
            executable_path = process["executable"]["path"]
            executable_name = os.path.basename(executable_path)

            if match_pattern(executable_name, name_pattern):
                pid_set.add(pid)
            elif show_child_process and (responsible_pid in pid_set):
                pid_set.add(pid)
            else:
                continue

            print(f"{Fore.GREEN}{executable_name} {Style.DIM}({pid},{ppid},{
                  process_name(responsible_pid)}){Style.RESET_ALL} ", end="")

            if "exec" in event:
                args = event["exec"]["args"]
                print(f'[EXEC] {" ".join(args)}')

                if show_env_vars:
                    for element in event["exec"]["env"]:
                        print(f"{Style.DIM}  {element}{Style.RESET_ALL}")
            elif "fork" in event:
                child_pid = event["fork"]["child"]["audit_token"]["pid"]
                print(f'[FORK] Child PID: {child_pid}')
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
    parser.add_argument("-e", "--show-env-vars", action="store_true",
                        help="Include environment variables in the output.")
    args = parser.parse_args()

    try:
        filter_eslogger(args.name, args.show_child_process, args.show_env_vars)
    except KeyboardInterrupt:
        sys.exit(0)
