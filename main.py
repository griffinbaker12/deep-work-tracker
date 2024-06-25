import argparse
import subprocess

HOSTS_PATH = "/etc/hosts"
HEADER_BLOCK = "# Added by work script\n"
FOOTER_BLOCK = "End of section\n"
EM_DASH = "\u2014"


def already_a_session():
    with open(HOSTS_PATH, "r") as hosts_file:
        for line in hosts_file:
            if line == HEADER_BLOCK:
                return True


def block_sites(sites):
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
            hosts_file.write(FOOTER_BLOCK)

        subprocess.run(["sudo", "killall", "-HUP", "mDNSResponder"])
    else:
        print("Error: Already a current study session in progress.")
        exit(1)


def remove_sites():
    with open(HOSTS_PATH, "r") as hosts_file:
        lines = hosts_file.readlines()

    with open(HOSTS_PATH, "w") as hosts_file:
        for line in lines:
            if line == HEADER_BLOCK:
                break
            hosts_file.write(line)


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

    print(
        f"Blocking sites {EM_DASH} {", ".join(sites)} {EM_DASH} for {block_duration} minutes."
    )

    block_sites(sites)

    # TODO: when the time is up, the remove the sites
    remove_sites()


if __name__ == "__main__":
    main()
