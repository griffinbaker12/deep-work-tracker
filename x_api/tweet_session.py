import os
import re
import sys
import time
from textwrap import wrap

import dotenv
from requests_oauthlib import OAuth1Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import COLLECTED_SESSIONS_DIR, NOTES_DIR

dotenv.load_dotenv()

consumer_key = os.environ.get("X_CLIENT_ID")
consumer_secret = os.environ.get("X_CLIENT_SECRET")

TWEET_CHAR_LIMIT = 280


def read_session_note(filename):
    with open(filename) as f:
        return f.read()


def clean_markdown(text):
    text = re.sub(r"\*\*", "", text)
    return text


def split_into_tweets(text):
    cleaned_text = clean_markdown(text)
    return wrap(
        cleaned_text, TWEET_CHAR_LIMIT, replace_whitespace=False, drop_whitespace=False
    )


def create_oauth_session():
    # Get request token
    request_token_url = "https://api.twitter.com/oauth/request_token?oauth_callback=oob&x_auth_access_type=write"
    oauth = OAuth1Session(consumer_key, client_secret=consumer_secret)

    try:
        fetch_response = oauth.fetch_request_token(request_token_url)
    except ValueError:
        print(
            "There may have been an issue with the consumer_key or consumer_secret you entered."
        )
        exit(1)

    resource_owner_key = fetch_response.get("oauth_token")
    resource_owner_secret = fetch_response.get("oauth_token_secret")
    print("Got OAuth token: %s" % resource_owner_key)

    # Get authorization
    base_authorization_url = "https://api.twitter.com/oauth/authorize"
    authorization_url = oauth.authorization_url(base_authorization_url)
    print("Please go here and authorize: %s" % authorization_url)
    verifier = input("Paste the PIN here: ")

    # Get the access token
    access_token_url = "https://api.twitter.com/oauth/access_token"
    oauth = OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=resource_owner_key,
        resource_owner_secret=resource_owner_secret,
        verifier=verifier,
    )
    oauth_tokens = oauth.fetch_access_token(access_token_url)

    access_token = oauth_tokens["oauth_token"]
    access_token_secret = oauth_tokens["oauth_token_secret"]

    # Create the final OAuth session
    return OAuth1Session(
        consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
    )


def post_tweet(oauth, payload, in_reply_to_id=None):
    if in_reply_to_id:
        payload["reply"] = {"in_reply_to_tweet_id": in_reply_to_id}

    response = oauth.post("https://api.twitter.com/2/tweets", json=payload)

    if response.status_code == 429:  # Rate limit exceeded
        reset_time = int(response.headers.get("x-rate-limit-reset", 0))
        sleep_time = max(reset_time - time.time(), 0) + 1
        print(f"Rate limit exceeded. Waiting for {sleep_time} seconds.")
        time.sleep(sleep_time)
        return post_tweet(oauth, payload, in_reply_to_id)  # Retry after waiting

    if response.status_code != 201:
        raise Exception(
            f"Request returned an error: {response.status_code} {response.text}"
        )

    return response.json()


def post_thread(oauth, tweets):
    previous_tweet_id = None
    for i, tweet in enumerate(tweets):
        payload = {"text": tweet}
        response = post_tweet(oauth, payload, previous_tweet_id)
        previous_tweet_id = response["data"]["id"]
        print(f"Posted tweet {i} of length {len(tweet)}")
    print(
        f"Thread posted successfully! It was {len(tweets)} post{"s" if len(tweets) > 1 else ""} long."
    )


def select_directory():
    while True:
        choice = input(
            "Select source directory:\n1. Collected Sessions\n2. Session Notes\nEnter 1 or 2: "
        ).strip()
        if choice == "1":
            return COLLECTED_SESSIONS_DIR, "collected session"
        elif choice == "2":
            return NOTES_DIR, "session note"
        else:
            print("Invalid choice. Please enter 1 or 2.")


def main():
    oauth = create_oauth_session()

    selected_dir, file_type = select_directory()

    if not os.path.exists(selected_dir):
        err_str = "Error: {selected_dir} does not exist. "
        if file_type == "collected session":
            err_str += "Run 'sudo python3 main.py collect' command to collect multiple notes into one note before trying this command again."
        else:
            err_str += "Run 'sudo python3 main.py start...' to create a session that you can then upload to X."
        print(err_str)
        exit(1)

    files = [f for f in os.listdir(selected_dir) if f.endswith(".md")]
    if not files:
        print(f"No markdown files found in the {file_type} directory.")
        exit(1)

    for i, file in enumerate(files):
        print(f"{i+1}. {file}")

    while True:
        try:
            selection = (
                int(input(f"Select a {file_type} to upload (enter number): ")) - 1
            )
            if 0 <= selection < len(files):
                selected_file = files[selection]
                break
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a number.")

    print(selected_dir, selected_file)

    note_content = read_session_note(os.path.join(selected_dir, selected_file))
    tweets = split_into_tweets(note_content)

    post_thread(oauth, tweets)


if __name__ == "__main__":
    main()
