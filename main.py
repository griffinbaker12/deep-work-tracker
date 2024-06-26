import argparse
import os
import re
import signal
import subprocess
import sys
from datetime import datetime, timedelta

HOSTS_PATH = "/etc/hosts"
HEADER_BLOCK = "# Added by work script\n"
FOOTER_BLOCK = "End of section\n"
EM_DASH = "\u2014"
SITE_PATTERN = r"(?:www\.)?([a-zA-Z0-9-]+)\.com"
SESSION_INFO_FILE = "/tmp/site_blocker_session_info"
TIME_FORMAT = "%m/%d/%y, %H:%M:%S"
POST_SESSION_RECAP_QS = [
    "What did you learn?",
    "What went well?",
    "What did not go well?",
]


def reset_dns(success_str):
    subprocess.run(["sudo", "killall", "-HUP", "mDNSResponder"])
    print(success_str)


def remove_spaces(arr):
    return list(filter(bool, arr))


def get_site_name(line):
    return remove_spaces(line.split("\n"))[0].split(" ")[1]


def already_a_session():
    return os.path.exists(SESSION_INFO_FILE)


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
        reset_dns(
            f"Blocked sites {EM_DASH} {", ".join(sites)} {EM_DASH} for {duration} minutes."
        )
        return True
    else:
        print("Error: Already a current study session in progress.")
        return False


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

    reset_dns(f"Removed blocked sites: {", ".join(blocked_sites)}.")


def prompt_user():
    print("\nStudy session ended, answer these questions to recap how it went")
    # for q in POST_SESSION_RECAP_QS:
    #     x = input(q)


def start_session(sites, duration):
    if block_sites(sites, duration):
        try:
            with open(SESSION_INFO_FILE, "w") as session_file:
                start_time = datetime.now()
                # TODO: change back to minutes
                end_time = start_time + timedelta(seconds=duration)
                session_file.write(
                    f"study session started at {start_time.strftime(TIME_FORMAT)}, session to end at {end_time.strftime(TIME_FORMAT)}"
                )
                removal_script = os.path.abspath(__file__)
                # at_command = f'echo "hey there" | at {end_time.strftime("%H:%M")} {end_time.strftime("%m%d%y")}'
                # at_command = f"echo ?? | tee /tmp/test.txt"
                # print(at_command)
                # # Q: what does shell=True do and all the other commands?
                # subprocess.run(
                #     at_command, shell=True, check=True, capture_output=True, text=True
                # )

                at_command = (
                    'echo "echo did this work? > /tmp/test.txt" | at now + 1 minute'
                )
                subprocess.run(
                    at_command,
                    shell=True,
                    check=True,
                    text=True,
                )
                print(
                    f"Your study session has started! It will end at {end_time.strftime(TIME_FORMAT)}."
                )
        except subprocess.CalledProcessError as e:
            print(f"Command failed with exit code {e.returncode}")
            print("Command output:", e.output)
            print("Command error:", e.stderr)
        except Exception as e:
            print("Something went wrong:", e)


def end_session():
    remove_sites()
    os.remove(SESSION_INFO_FILE)
    prompt_user()
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="Block websites during this study session of a specified time period."
    )
    parser.add_argument(
        "action",
        choices=["start", "info", "end"],
        help="Action to perform: 'start' a new session, get 'info' about the current session, or 'end' the current session.",
    )
    # Q: assume that the --sites makes it optional?
    parser.add_argument(
        "--sites",
        help="Comma-separated list of site names (eg, x, instagram, etc.) to block.",
    )
    # Q: assume that the --sites makes it optional?
    parser.add_argument(
        "--duration",
        type=int,
        help="Time to block sites (in minutes).",
    )
    args = parser.parse_args()

    if args.action == "start":
        if not args.sites or not args.duration:
            print("Error: Both --sites and --duration are required for 'start' action.")
            sys.exit(1)
        sites = args.sites.split(",")
        start_session(sites, args.duration)
    elif args.action == "info":
        print("*** need to implement ***")
    elif args.action == "end":
        end_session()


if __name__ == "__main__":
    main()
