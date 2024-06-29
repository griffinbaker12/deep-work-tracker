HOSTS_PATH = "/etc/hosts"
HEADER_BLOCK = "# Added by work script\n"
FOOTER_BLOCK = "End of section\n"
SITE_PATTERN = r"(?:www\.)?([a-zA-Z0-9-]+)\.com"
SESSION_INFO_FILE = "/tmp/site_blocker_session_info"
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
