import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta

HOSTS_PATH = "/etc/hosts"
HEADER_BLOCK = "# Added by work script\n"
FOOTER_BLOCK = "End of section\n"
EM_DASH = "\u2014"
SITE_PATTERN = r"(?:www\.)?([a-zA-Z0-9-]+)\.com"
SESSION_INFO_FILE = "/tmp/site_blocker_session_info"
TEST_FILE = "/tmp/exit_ran"
TIME_FORMAT = "%m/%d/%y, %H:%M:%S"
NOTES_DIR = "session_notes"
SESSION_TRACKER_FILE = "session_tracker.json"
NO_SITES_STR = "No sites entered to block."
DEFAULT_SITES_FILE = "default_sites.txt"
COLLECTED_SESSIONS_DIR = "collected_sessions"

# UPDATE THIS DEPENDING ON THE QUESTIONS YOU WANT TO ANSWER
POST_SESSION_RECAP_QS = [
    "1) What did you learn / work on?",
    "2) What went well?",
    "3) What didn't go well?",
]

end_session_requested = False


def reset_dns(success_str):
    subprocess.run(["sudo", "killall", "-HUP", "mDNSResponder"])
    return success_str


def print_underline(s, with_str=True):
    if with_str:
        print(s)
    print("-" * len(s))


def remove_spaces(arr):
    return list(filter(bool, arr))


def get_site_name(line):
    return remove_spaces(line.split("\n"))[0].split(" ")[1]


def already_a_session():
    return os.path.exists(SESSION_INFO_FILE)


def read_default_sites():
    if os.path.exists(DEFAULT_SITES_FILE):
        with open(DEFAULT_SITES_FILE, "r") as f:
            return [site.strip() for site in f.readlines() if site.strip()]
    return [""]


def block_sites(sites, all_sites=False):
    if not already_a_session():
        if all_sites:
            return "Allowing all sites."

        if sites[0] == "":
            sites = read_default_sites()

        if sites[0] != "":
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
            return reset_dns(f"Blocked the following sites: {", ".join(sites)}.")
        return NO_SITES_STR
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

    reset_dns(f"\nRemoved blocked sites: {", ".join(blocked_sites)}.")


def get_multi_line_input(prompt, divider):
    print(prompt)
    lines = []
    while True:
        line = input(f"{divider} ").rstrip()
        if not line:
            break
        else:
            lines.append(f"{divider} {line}")
    return "\n".join(lines)


# If the first time, ask about the divider, and let them know they can change with the line-starter arg the next time they run
# the script...


def prompt_user(start_time):
    if not os.path.exists(NOTES_DIR):
        os.makedirs(NOTES_DIR)

    if not os.path.exists(SESSION_TRACKER_FILE):
        with open(SESSION_TRACKER_FILE, "w") as tracker_file:
            json.dump({"session_number": 1}, tracker_file)

    with open(SESSION_TRACKER_FILE, "r") as tracker_file:
        data = json.load(tracker_file)
        session_number = data["session_number"]

    session_end_str = "Work session ended, answer these questions to recap how it went!"
    print_underline(f"{session_end_str}", with_str=False)
    print_underline(session_end_str)

    answers = {}

    divider = input(
        "Choose your preferred line starter (\u2022, '>', '-'). Press Enter for default '\u2022' :\n"
    ).strip()
    if divider not in [
        "\u2022",
        ">",
        "-",
    ]:
        divider = "\u2022"

    print()
    for q in POST_SESSION_RECAP_QS:
        answer = get_multi_line_input(f"{q}", divider)
        answers[q] = answer
        print()

    note_file_path = os.path.join(NOTES_DIR, f"session_{session_number:02}.md")
    with open(note_file_path, "w") as note_file:
        session_start_time = start_time
        session_end_time = datetime.now()
        session_duration_str = format_timedelta(session_end_time - session_start_time)
        note_file.write(f"**Session {session_number} - {session_duration_str}**\n\n")

        for q, a in answers.items():
            note_file.write(f"**{q}**\n{a}\n\n")

    data["session_number"] += 1
    with open(SESSION_TRACKER_FILE, "w") as tracker_file:
        json.dump(data, tracker_file)

    subprocess.run(f"echo '{note_file_path}' | pbcopy", shell=True)
    print(f"⭐️ Congrats on working for {session_duration_str} ⭐️")
    print(
        f"\nYour answers have been saved to {note_file_path}. The file path has also been copied to your clipboard!"
    )


def start_session(sites, duration, continuous, all_sites):
    if block_str := block_sites(sites, all_sites):
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration)

        with open(SESSION_TRACKER_FILE, "r") as tracker_file:
            data = json.load(tracker_file)
            session_number = data["session_number"]

        with open(SESSION_INFO_FILE, "w") as session_file:
            session_str = f"Session number {session_number}\nStart time:{start_time.strftime(TIME_FORMAT)}\n"
            if end_time:
                session_str += "End time:{end_time.strftime(TIME_FORMAT)}\n"
            session_file.write(session_str)
            if block_str != NO_SITES_STR:
                session_file.write("\n".join(sites))

        session_started_str = f"Work session {session_number} started "
        if continuous:
            session_started_str += (
                "in continuous mode. It will run until you stop the script."
            )
        else:
            session_started_str += f"for {duration} minutes."

        underline_str = (
            session_started_str
            if len(session_started_str) > len(block_str)
            else block_str
        )

        print_underline(underline_str, with_str=False)
        print(session_started_str)
        print(block_str)
        print_underline(underline_str, with_str=False)

        try:
            if continuous:
                while True:
                    time.sleep(1)
            else:
                time.sleep(duration * 60)
        except KeyboardInterrupt:
            confirm_end_session()
        finally:
            if not end_session_requested:
                end_session()


def remove_old_info_file_and_get_start_time():
    start_time = None
    if os.path.exists(SESSION_INFO_FILE):
        with open(SESSION_INFO_FILE, "r") as f:
            for line in f:
                if line.startswith("Start time:"):
                    start_time_str = line.split("Start time:")[1].strip()
                    start_time = datetime.strptime(start_time_str, TIME_FORMAT)
                    break
        os.remove(SESSION_INFO_FILE)
    return start_time


def end_session():
    remove_sites()

    start_time = None
    if os.path.exists(SESSION_INFO_FILE):
        # save the old start time to get full duration
        start_time = remove_old_info_file_and_get_start_time()

    if start_time:
        prompt_user(start_time)
    else:
        print("Error parsing the session info file.")
        sys.exit(1)

    sys.exit(0)


def confirm_end_session():
    global end_session_requested
    end_session_requested = True
    valid_input = False

    while not valid_input:
        confirm = (
            input("\nAre you sure you want to end the study session? (y/n): ")
            .strip()
            .lower()
        )
        if confirm == "y":
            end_session()
            valid_input = True
        elif confirm == "n":
            end_session_requested = False
            valid_input = True
        else:
            print("Please type either 'y' or 'n'.")


def signal_handler(sig, frame):
    confirm_end_session()


def format_timedelta(td):
    hours, remainder = divmod(td.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)
    if int(hours) > 0:
        return f"{int(hours)} hours, {int(minutes)} minutes"
    else:
        return f"{int(minutes)} minutes"


def collect_notes(start_session, end_session):
    if not os.path.exists(COLLECTED_SESSIONS_DIR):
        os.makedirs(COLLECTED_SESSIONS_DIR)

    combined_content = {}
    session_durations = []

    for session_num in range(start_session, end_session + 1):
        filename = f"session_{session_num:02}.md"
        filepath = os.path.join(NOTES_DIR, filename)

        if not os.path.exists(filepath):
            print(
                f"Warning: Session {session_num} not found in the {NOTES_DIR} directory. Skipping."
            )
            continue

        with open(filepath, "r") as f:
            content = f.read()

         tn


# Q: assume that the --sites makes it optional?


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(
        description="Block websites during this study session of a specified time period."
    )
    parser.add_argument(
        "action",
        choices=["start", "end", "collect"],
        help="Actions to perform: 'start' a new session, 'end' the current session, or 'collect' to group multiple sessions into one note.",
    )
    parser.add_argument(
        "--sites",
        help="Comma-separated list of site names (eg, x, instagram, etc.) to block.",
        default="",
    )
    parser.add_argument(
        "--duration",
        type=int,
        help="Time to block sites (in minutes).",
        default=0,
    )
    parser.add_argument(
        "--continuous",
        type=bool,
        help="Instead of entering a duration, the script will continue until you explicitly end it.",
        default=False,
    )
    parser.add_argument(
        "--all-sites",
        type=bool,
        dest="all_sites",
        help="If true, will not block any sites regardless of your default_sites.txt or the arg(s) passed to --sites parameter.",
        default=False,
    )
    parser.add_argument(
        "--collect-from",
        dest="collect_from",
        type=int,
    )
    parser.add_argument(
        "--to",
        type=int,
    )
    args = parser.parse_args()

    if args.action == "start":
        if not args.duration and not args.continuous:
            print(
                "Error: Either--duration or --continuous is required for 'start' action."
            )
            sys.exit(1)
        sites = [""] if args.all_sites else args.sites.split(",")
        start_session(
            sites,
            args.duration,
            args.continuous,
            args.all_sites,
        )
    elif args.action == "end":
        end_session()
    elif args.actions == "collect":
        if not args.collect_from and not args.to:
            print(
                "Error: Must pass which session notes to collect into one daily note."
            )
        collect_notes(args.collect_from, args.to)
    else:
        print("Please enter a valid action: start, end.")


if __name__ == "__main__":
    main()
