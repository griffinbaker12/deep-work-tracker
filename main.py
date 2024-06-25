import argparse

EM_DASH = "\u2014"


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

    print(f"Blocking sites {EM_DASH} {", ".join(sites)} {EM_DASH} for {block_duration} minutes.")


if __name__ == "__main__":
    main()
