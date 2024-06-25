import argparse
import re
import subprocess
from typing import List

HOSTS_PATH = "/etc/hosts"
HEADER_BLOCK = "# Added by work script\n"
FOOTER_BLOCK = "End of section\n"
EM_DASH = "\u2014"
SITE_PATTERN = r"(?:www\.)?([a-zA-Z0-9-]+)\.com"


def remove_spaces(arr: List) -> List:
    return list(filter(bool, arr))


def get_site_name(line):
    return remove_spaces(line.split("\n"))[0].split(" ")[1]


def already_a_session():
    with open(HOSTS_PATH, "r") as hosts_file:
        for line in hosts_file:
            if line == HEADER_BLOCK:
                return True


def block_sites(sites, duration):
    if not already_a_session():
        entries = []
        with open(HOSTS_PATH, "a") as hosts_file:
            for site in sites:
                entries.extend(
                    [
                        f"0.0.0.0 {site}.com",
                        f"0.0.0.0 www.{site}.com",
                    ]
                )
            hosts_file.write(HEADER_BLOCK)
            hosts_file.write("\n".join(entries))
            hosts_file.write("\n")
            hosts_file.write(FOOTER_BLOCK)
        subprocess.run(["sudo", "killall", "-HUP", "mDNSResponder"])
        print(
            f"Blocked sites {EM_DASH} {", ".join(sites)} {EM_DASH} for {duration} minutes."
        )
    else:
        print("Error: Already a current study session in progress.")
        exit(1)


def remove_sites():
    blocked_sites = set()

    with open(HOSTS_PATH, "r") as hosts_file:
        lines = hosts_file.readlines()

    with open(HOSTS_PATH, "w") as hosts_file:
        seen_header_block = False
        for line in lines:
            if line == HEADER_BLOCK:
                seen_header_block = True
            elif not seen_header_block:
                hosts_file.write(line)
            elif line == FOOTER_BLOCK:
                break
            else:
                parsed_line = get_site_name(line)
                if m := re.match(SITE_PATTERN, parsed_line):
                    if m not in blocked_sites:
                        site_name = m.group(1)
                        blocked_sites.add(site_name)

    print(f"Removed blocked sites: {", ".join(blocked_sites)}.")


def main():
    parser = argparse.ArgumentParser(
        description="Block websites during this study session of a specified time period."
    )
    parser.add_argument(
        "blocked_sites",
        help="Comma-separated list of site names (eg, x, instgram, etc.) to block",
    )
    parser.add_argument(
        "block_time",
        type=int,
        help="Time to block sites (in minutes)",
    )

    args = parser.parse_args()

    sites, block_duration = args.blocked_sites.split(","), args.block_time

    block_sites(sites, block_duration)

    # TODO: when the time is up, the remove the sites
    remove_sites()


if __name__ == "__main__":
    main()
