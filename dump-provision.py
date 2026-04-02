#!/usr/bin/env python3

import argparse
import subprocess
import plistlib
import sys
from pathlib import Path
from colorama import Fore, Style


def parse_provisioning_profile(profile_path):
    result = subprocess.run(['security', 'cms', '-D', '-i', profile_path], capture_output=True)
    if result.returncode == 0:
        data = plistlib.loads(result.stdout)
        return data
    else:
        raise Exception(f"Error reading profile {profile_path}: {result.stderr.decode()}")


def default_provisioning_profiles_directory():
    return Path.home() / "Library" / "Developer" / "Xcode" / "UserData" / "Provisioning Profiles"


def dump_all_provisioning_profile(provisioning_profiles_directory, show_details=False):

    directory = Path(provisioning_profiles_directory)
    if not directory.exists():
        print(f"The directory '{directory}' does not exist.", file=sys.stderr)
        return

    provisioning_profiles = sorted(
        [p for p in directory.iterdir() if p.suffix in ('.mobileprovision', '.provisionprofile')],
        key=lambda p: (p.suffix, len(p.name)),
    )

    # Read and parse the contents of each provisioning profile
    for profile_path in provisioning_profiles:
        profile = parse_provisioning_profile(profile_path)
        basename = profile_path.name

        if show_details:
            print(f'{Fore.BLUE}{basename}{Style.RESET_ALL}: ')
            print(f"  Name           : {profile['Name']}")
            print(f"  Application ID: {profile['Entitlements'].get('application-identifier', None)
                                       or profile['Entitlements'].get('com.apple.application-identifier', None)}")
            print(f"  Platform       : {', '.join(profile['Platform'])}")
            print(f"  UUID           : {profile['UUID']}")
            print(f"  Expiration Date: {profile['ExpirationDate']}")
        else:
            print(f"{Fore.BLUE}{basename}{Style.RESET_ALL}: {profile['Name']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Print all the local provisioning profiles.",
    )
    parser.add_argument("-d", "--default-directory", action="store_true",
                        help="Just print the default directory of provisioning profiles.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show the detail information of the provisioning profile.")
    args = parser.parse_args()

    default_directory = default_provisioning_profiles_directory()
    if args.default_directory:
        print(default_directory)
    else:
        dump_all_provisioning_profile(default_directory, args.verbose)
