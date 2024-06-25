import argparse
import subprocess

EM_DASH = "\u2014"


def block_sites(sites):
    header = "# Added by work script\n"
    entries = []

    with open("/etc/hosts", "a") as hosts_file:
        for site in sites:
            entries.extend(
                [
                    f"0.0.0.0 {site}.com",
                    f"0.0.0.0 www.{site}.com",
                ]
            )
        hosts_file.write(header)
        hosts_file.write("\n".join(entries))
        hosts_file.write("\n")

    subprocess.run(["sudo", "killall", "-HUP", "mDNSResponder"])


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


if __name__ == "__main__":
    main()
