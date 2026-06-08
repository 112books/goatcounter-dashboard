#!/usr/bin/env python3
"""
Run this script once locally to obtain a GSC refresh token.

Usage:
    GSC_CLIENT_ID=<id> GSC_CLIENT_SECRET=<secret> python scripts/get_gsc_token.py
"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow

CLIENT_ID     = os.environ["GSC_CLIENT_ID"]
CLIENT_SECRET = os.environ["GSC_CLIENT_SECRET"]

CLIENT_CONFIG = {
    "installed": {
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
        "token_uri":     "https://oauth2.googleapis.com/token",
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
    }
}

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

def main():
    flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n=== CREDENCIALS OBTINGUDES ===")
    print(f"refresh_token: {creds.refresh_token}")
    print(f"client_id:     {CLIENT_ID}")
    print(f"client_secret: {CLIENT_SECRET}")
    print("\nGuarda aquests tres valors com a secrets de GitHub.")

if __name__ == "__main__":
    main()
