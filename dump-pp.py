#!/usr/bin/env python3

import argparse
from datetime import datetime, timedelta, timezone
import plistlib
from pathlib import Path
import subprocess
import sys


PROFILE_EXTENSIONS = (".mobileprovision", ".provisionprofile")
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def parse_provisioning_profile(profile_path):
    result = subprocess.run(
        ["security", "cms", "-D", "-i", str(profile_path)],
        capture_output=True,
    )
    if result.returncode != 0:
        error = result.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"Error reading profile '{profile_path}': {error}")

    return plistlib.loads(result.stdout)


def default_provisioning_profiles_directory():
    return Path.home() / "Library" / "MobileDevice" / "Provisioning Profiles"


def profile_platform(profile):
    platform_names = {
        "iOS": "iOS",
        "OSX": "macOS",
        "macOS": "macOS",
    }
    platforms = profile.get("Platform", [])
    return ", ".join(platform_names.get(platform, platform) for platform in platforms)


def profile_type(profile):
    entitlements = profile.get("Entitlements", {})
    return "developer" if entitlements.get("get-task-allow") else "distribution"


def format_expiration(expiration):
    if not isinstance(expiration, datetime):
        return str(expiration or "")

    if expiration.tzinfo is None:
        expiration = expiration.replace(tzinfo=timezone.utc)
    expiration = expiration.astimezone(timezone.utc)
    formatted = f"{expiration.replace(tzinfo=None).isoformat(sep=' ', timespec='seconds')}Z"

    now = datetime.now(timezone.utc)
    if sys.stdout.isatty():
        if expiration < now:
            return f"{RED}{formatted}{RESET}"
        if expiration <= now + timedelta(days=30):
            return f"{YELLOW}{formatted}{RESET}"
    return formatted


def visible_length(value):
    return len(value.replace(RED, "").replace(YELLOW, "").replace(RESET, ""))


def print_table(headers, rows):
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], visible_length(value))

    def format_row(row):
        return "  ".join(
            value + " " * (widths[index] - visible_length(value))
            for index, value in enumerate(row)
        )

    print(format_row(headers))
    print(format_row(tuple("-" * width for width in widths)))
    for row in rows:
        print(format_row(row))


def dump_provisioning_profiles(provisioning_profiles_directory):
    directory = Path(provisioning_profiles_directory).expanduser()
    if not directory.is_dir():
        print(f"The directory '{directory}' does not exist.", file=sys.stderr)
        return 1

    profile_paths = sorted(
        (
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in PROFILE_EXTENSIONS
        ),
        key=lambda path: path.name.lower(),
    )

    rows = []
    had_errors = False
    for profile_path in profile_paths:
        try:
            profile = parse_provisioning_profile(profile_path)
        except (RuntimeError, plistlib.InvalidFileException) as error:
            print(error, file=sys.stderr)
            had_errors = True
            continue

        rows.append(
            (
                profile_path.name,
                str(profile.get("Name", "")),
                profile_platform(profile),
                profile_type(profile),
                format_expiration(profile.get("ExpirationDate")),
            )
        )

    print_table(("File name", "Name", "Platform", "Type", "Expiration"), rows)
    return 1 if had_errors else 0


def dump_provisioning_profile(profile_path):
    path = Path(profile_path).expanduser()
    if not path.is_file():
        print(f"The provisioning profile '{path}' does not exist.", file=sys.stderr)
        return 1

    try:
        profile = parse_provisioning_profile(path)
    except (RuntimeError, plistlib.InvalidFileException) as error:
        print(error, file=sys.stderr)
        return 1

    result = subprocess.run(
        ["plutil", "-p", "-"],
        input=plistlib.dumps(profile, fmt=plistlib.FMT_XML, sort_keys=False),
        capture_output=True,
    )
    if result.returncode != 0:
        error = result.stderr.decode(errors="replace").strip()
        print(f"Error formatting profile '{path}': {error}", file=sys.stderr)
        return 1

    sys.stdout.buffer.write(result.stdout)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Inspect local Apple provisioning profiles.",
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=Path,
        help="Directory to summarize (default: %(default)s).",
        default=default_provisioning_profiles_directory(),
    )
    parser.add_argument(
        "profile",
        nargs="?",
        type=Path,
        help="Provisioning profile to decode and print in full.",
    )
    args = parser.parse_args()

    if args.profile is not None:
        return dump_provisioning_profile(args.profile)
    return dump_provisioning_profiles(args.directory)


if __name__ == "__main__":
    raise SystemExit(main())
