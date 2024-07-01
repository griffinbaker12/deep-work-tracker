import os
import subprocess

from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session

load_dotenv()

consumer_key = os.environ.get("X_CLIENT_ID")
consumer_secret = os.environ.get("X_CLIENT_SECRET")

if not consumer_key or not consumer_secret:
    print("Error: need both consumer key and secret to interact with the X API.")
    exit(1)

fields = "created_at,description"
params = {"user.fields": fields}

# Get request token
request_token_url = "https://api.twitter.com/oauth/request_token?oauth_callback=oob&x_auth_access_type=read"
oauth = OAuth1Session(consumer_key, client_secret=consumer_secret)


try:
    fetch_response = oauth.fetch_request_token(request_token_url)
except ValueError as e:
    print("Error fetching request token: {e}")
    print(
        "There may have been an issue with the consumer_key or consumer_secret you entered."
    )
    exit(1)

resource_owner_key = fetch_response.get("oauth_token")
resource_owner_secret = fetch_response.get("oauth_token_secret")
print("Got OAuth token: %s" % resource_owner_key)

# # Get authorization
base_authorization_url = "https://api.twitter.com/oauth/authorize"
authorization_url = oauth.authorization_url(base_authorization_url)
subprocess.run(f"echo '{authorization_url}' | pbcopy", shell=True)
print(
    "Please go here and authorize (it has been copied to your clipboard): %s"
    % authorization_url
)
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

# Make the request
oauth = OAuth1Session(
    consumer_key,
    client_secret=consumer_secret,
    resource_owner_key=access_token,
    resource_owner_secret=access_token_secret,
)

response = oauth.get("https://api.twitter.com/2/users/me", params=params)

if response.status_code != 200:
    raise Exception(
        "Request returned an error: {} {}".format(response.status_code, response.text)
    )

json_response = response.json()
user_id = json_response["data"]["id"]

with open(".env", "a") as f:
    f.write(f"X_USER_ID = {user_id}\n")

print(f'We wrote your user_id to you .env file: "{user_id}".')
