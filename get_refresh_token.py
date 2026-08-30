"""Run this ONCE locally (not in CI) to generate a YouTube OAuth refresh token.

Prerequisites:
1. In Google Cloud Console, create an OAuth 2.0 Client ID of type "Desktop app".
2. Enable the "YouTube Data API v3" for that project.
3. Download the client secret and set YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET
   env vars (or paste them below).

This opens a browser for a one-time login/consent, then prints a refresh_token.
Save that value as the YOUTUBE_REFRESH_TOKEN GitHub Secret — the pipeline uses
it to mint access tokens automatically on every run, with no further logins.
"""
import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

client_config = {
    "installed": {
        "client_id": os.environ["YOUTUBE_CLIENT_ID"],
        "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}

flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
creds = flow.run_local_server(port=0)

print("\n=== Save this as the YOUTUBE_REFRESH_TOKEN GitHub secret ===")
print(creds.refresh_token)
