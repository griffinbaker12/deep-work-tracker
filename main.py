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
POSSIBLE_DIVIDERS = ["\u2022", ">", "-"]

# UPDATE THIS DEPENDING ON THE QUESTIONS YOU WANT TO ANSWER
POST_SESSION_RECAP_QS = [
    "1) What did you learn / work on?",
    "2) What went well?",
    "3) What didn't go well?",
]

end_session_requested = False
is_handling_signal = False


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


def read_default_divider():
    if os.path.exists(SESSION_TRACKER_FILE):
        with open(SESSION_TRACKER_FILE, "r") as f:
            data = json.load(f)
            return data.get("default_divider")
    return None


def set_default_divider(divider):
    if os.path.exists(SESSION_TRACKER_FILE):
        with open(SESSION_TRACKER_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {"session_number": 1}

    data["default_divider"] = divider

    with open(SESSION_TRACKER_FILE, "w") as f:
        json.dump(data, f)


def prompt_for_divider():
    while True:
        divider = input(
            f"Choose your preferred line starter {POSSIBLE_DIVIDERS}. Press Enter for default '{POSSIBLE_DIVIDERS[0]}' : "
        ).strip()
        if not divider:
            return POSSIBLE_DIVIDERS[0]
        if divider in POSSIBLE_DIVIDERS:
            return divider
        print(f"Invalid divider. Please choose from {POSSIBLE_DIVIDERS}")


def get_session_number():
    if os.path.exists(SESSION_TRACKER_FILE):
        with open(SESSION_TRACKER_FILE, "r") as f:
            data = json.load(f)
            return data.get("session_number", 1)
    return 1


def increment_session_number():
    if os.path.exists(SESSION_TRACKER_FILE):
        with open(SESSION_TRACKER_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {"session_number": 1}

    data["session_number"] = data.get("session_number", 1) + 1

    with open(SESSION_TRACKER_FILE, "w") as f:
        json.dump(data, f)


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


def prompt_user(start_time, cli_divider=None):
    if not os.path.exists(NOTES_DIR):
        os.makedirs(NOTES_DIR)

    session_number = get_session_number()

    session_end_str = "Work session ended, answer these questions to recap how it went!"
    print_underline(f"{session_end_str}", with_str=False)
    print_underline(session_end_str)

    default_divider = read_default_divider()

    if cli_divider:
        divider = cli_divider
        print(f"Using divider provided via CLI: '{divider}' .")
    elif default_divider:
        divider = default_divider
        print(f"Using default divider: '{divider}'.")
        print(
            "You can change this with the '--divider' argument or by editing the 'session_tracker.json' file."
        )
    else:
        divider = prompt_for_divider()
        set_default_divider(divider)
        print(f"Default divider set to: '{divider}'.")
        print(
            "You can change this in the future with the '--divider' argument or by editing the 'session_tracker.json' file."
        )

    answers = {}

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

    increment_session_number()

    subprocess.run(f"echo '{note_file_path}' | pbcopy", shell=True)
    print(f"⭐️ Congrats on working for {session_duration_str} ⭐️")
    print(
        f"\nYour answers have been saved to {note_file_path}.\nThe file path has also been copied to your clipboard!"
    )


def start_session(sites, duration, continuous, all_sites):
    if block_str := block_sites(sites, all_sites):
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration)

        session_number = get_session_number()

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
            pass
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


def end_session(cli_divider=None):
    remove_sites()

    start_time = None
    if exists := os.path.exists(SESSION_INFO_FILE):
        # save the old start time to get full duration
        start_time = remove_old_info_file_and_get_start_time()

    if start_time:
        try:
            prompt_user(start_time, cli_divider)
        except KeyboardInterrupt:
            print("\nSkipping session recap due to interruption.")
    else:
        if not exists:
            print(f"There must be an active session at {SESSION_INFO_FILE} to end one.")
        else:
            print("Error parsing the session info file.")

    sys.exit(0)


def confirm_end_session():
    global end_session_requested
    end_session_requested = True

    try:
        while True:
            confirm = (
                input("\nAre you sure you want to end the study session? (y/n): ")
                .strip()
                .lower()
            )
            if confirm == "y":
                end_session()
                break
            elif confirm == "n":
                end_session_requested = False
                break
            else:
                print("Please type either 'y' or 'n'.")
    except KeyboardInterrupt:
        print("\nForced exit. Cleaning up...")
        cleanup_and_exit()


def cleanup_and_exit():
    remove_sites()
    print("Session ended abruptly. Site blocking has been removed.")
    if os.path.exists(SESSION_INFO_FILE):
        os.remove(SESSION_INFO_FILE)
    sys.exit(1)


def signal_handler(sig, frame):
    global end_session_requested, is_handling_signal
    if is_handling_signal:
        print("\nForced exit. Cleaning up...")
        cleanup_and_exit()

    is_handling_signal = True
    try:
        confirm_end_session()
    finally:
        is_handling_signal = False


def format_timedelta(td):
    hours, remainder = divmod(td.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)
    if int(hours) > 0:
        return f"{int(hours)} hours, {int(minutes)} minutes"
    else:
        return f"{int(minutes)} minutes"


def sum_durations(durations):
    total_minutes = 0
    for duration in durations:
        if "hours" in duration and "minutes" in duration:
            hours, minutes = map(int, re.findall(r"\d+", duration))
            total_minutes += (hours * 60) + minutes
        elif "minutes" in duration:
            minutes = int(re.findall(r"\d+", duration)[0])
            total_minutes += minutes
    hours, minutes = divmod(total_minutes, 60)
    if hours > 0:
        return f"{hours} hours, {minutes} minutes"
    else:
        return f"{minutes} minutes"


def detect_divider(text):
    for divider in POSSIBLE_DIVIDERS:
        if any(line.strip().startswith(divider) for line in text.split("\n")):
            return divider
    return None


def has_divider(text):
    return any(text.strip().startswith(d) for d in POSSIBLE_DIVIDERS)


def replace_or_add_divider(text, new_divider):
    if has_divider(text):
        for divider in POSSIBLE_DIVIDERS:
            if text.strip().startswith(divider):
                return re.sub(f"^{re.escape(divider)}\\s*", f"{new_divider} ", text)
    return f"{new_divider} {text.strip()}"


def get_and_increment_day_number():
    if os.path.exists(SESSION_TRACKER_FILE):
        with open(SESSION_TRACKER_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {"session_number": 1, "day_number": 0}

    data["day_number"] = data.get("day_number", 0) + 1

    with open(SESSION_TRACKER_FILE, "w") as f:
        json.dump(data, f)

    return data["day_number"]


def collect_notes(start_session, end_session, cli_divider=None):
    if not os.path.exists(NOTES_DIR):
        print(
            f"Error: No session notes found in {NOTES_DIR}. Please run a session first."
        )
        sys.exit(1)

    session_files = [
        f
        for f in os.listdir(NOTES_DIR)
        if f.startswith("session_") and f.endswith(".md")
    ]
    if not session_files:
        print(
            f"Error: No session notes found in {NOTES_DIR}. Please run a session first."
        )
        sys.exit(1)

    default_divider = read_default_divider()

    if cli_divider:
        final_divider = cli_divider
    elif default_divider:
        final_divider = default_divider
    else:
        final_divider = prompt_for_divider()
        set_default_divider(final_divider)

    used_dividers = set()
    combined_content = [(q, []) for q in POST_SESSION_RECAP_QS]
    session_durations = []

    if not os.path.exists(COLLECTED_SESSIONS_DIR):
        os.makedirs(COLLECTED_SESSIONS_DIR)

    for note_num in range(start_session, end_session + 1):
        filename = f"session_{note_num:02}.md"
        filepath = os.path.join("session_notes", filename)

        if not os.path.exists(filepath):
            print(
                f"Warning: Session {note_num} not found in the {NOTES_DIR} directory. Skipping."
            )
            continue

        with open(filepath, "r") as f:
            content = f.read()
        duration_match = re.search(r"\*\*Session \d+ - (.+)\*\*", content)
        if duration_match:
            session_durations.append(duration_match.group(1))
        for i, (question, answers) in enumerate(combined_content):
            pattern = f"\\*\\*{re.escape(question)}\\*\\*\n(.*?)(?=\\*\\*|$)"
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                if divider := detect_divider(matches[0]):
                    used_dividers.add(divider)
                if match_arr := matches[0].strip().split("\n"):
                    filtered_matches = [m.strip() for m in match_arr if m.strip()]
                    if filtered_matches:
                        combined_content[i] = (question, answers + filtered_matches)

    day_number = get_and_increment_day_number()
    combined_filename = (
        f"day_{day_number:02}_sessions_{start_session:02d}_to_{end_session:02d}.md"
    )
    combined_filepath = os.path.join(COLLECTED_SESSIONS_DIR, combined_filename)

    with open(combined_filepath, "w") as combined_file:
        combined_file.write(f"**Day {day_number}**\n\n")
        combined_file.write(f"Total duration: {sum_durations(session_durations)}\n\n")
        for question, answers in combined_content:
            combined_file.write(f"**{question}**\n")
            for answer in answers:
                formatted_answer = replace_or_add_divider(answer, final_divider)
                combined_file.write(f"{formatted_answer}\n")
            combined_file.write("\n")

    print(f"Combined notes saved to: {combined_filepath}")
    subprocess.run(f"echo '{combined_filepath}' | pbcopy", shell=True)
    print("File path copied to clipboard!")


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
    parser.add_argument(
        "--divider",
        choices=POSSIBLE_DIVIDERS,
        help="Set the divider for the collect action. Also sets as new default if different from current default.",
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
        end_session(args.divider)
    elif args.action == "collect":
        if not args.collect_from and not args.to:
            print(
                "Error: Must pass which session notes to collect into one daily note. The relevant args are: 'collect_from' and 'to')."
            )
            sys.exit(1)

        if args.divider and args.divider != read_default_divider():
            set_default_divider(args.divider)

        collect_notes(args.collect_from, args.to, args.divider)
    else:
        print("Please enter a valid action: start, end.")


if __name__ == "__main__":
    main()
