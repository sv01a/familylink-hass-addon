#!/usr/bin/env python3
"""
Google Family Link - Master Token Generator (gpsoauth)

This utility generates a persistent Google Master Token (aas_et/...)
which can be used for long-term authentication without relying on
short-lived browser cookies.
"""

import json
import secrets
import sys
import urllib.parse

try:
    import gpsoauth
except ImportError:
    print("❌ 'gpsoauth' library is required.")
    print("Install it with: pip install gpsoauth")
    sys.exit(1)

def generate_android_id():
    """Generate a random 16-character hexadecimal Android ID"""
    return secrets.token_hex(8)


def main():
    print("=" * 70)
    print(" Google Family Link - Permanent Master Token Generator")
    print("=" * 70)

    android_id = generate_android_id()

    email = input("\nEnter your Google parent account email: ").strip()
    if not email:
        print("❌ Email cannot be empty!")
        sys.exit(1)

    login_url = (
        "https://accounts.google.com/EmbeddedSetup"
        "?source=android&xoauth_display_name=Android%20Device"
        "&lang=en&cc=us"
    )

    print("\n" + "-" * 70)
    print("STEP 1: Open the following URL in your web browser:")
    print("-" * 70)
    print(f"\n{login_url}\n")
    print("-" * 70)
    print("STEP 2: Complete the sign-in and 2-step verification in browser.")
    print("-" * 70)
    print("At the end, the page may show a white screen, 'success', or freeze at:")
    print("   '.../embeddedsigninconsent...#close'")
    print("\nHow to get the 'oauth_token':")
    print("   1. Open Developer Tools in browser (F12 or Cmd+Option+I).")
    print("   2. Go to: Application (or Storage) -> Cookies -> https://accounts.google.com")
    print("   3. Find the cookie named 'oauth_token' and copy its value.")
    print("   (Or if redirected to a URL containing 'oauth_token=', copy the full URL).")
    print("-" * 70)

    token_input = input("\nPaste the 'oauth_token' value (or full URL) here: ").strip()
    if not token_input:
        print("❌ No token provided!")
        sys.exit(1)

    # Extract oauth_token if a full URL was pasted
    oauth_token = token_input
    if "oauth_token=" in token_input:
        parsed = urllib.parse.urlparse(token_input)
        query = urllib.parse.parse_qs(parsed.query)
        fragment = urllib.parse.parse_qs(parsed.fragment)
        if "oauth_token" in fragment:
            oauth_token = fragment["oauth_token"][0]
        elif "oauth_token" in query:
            oauth_token = query["oauth_token"][0]

    print("\n[INFO] Exchanging oauth_token for a permanent Master Token...")
    try:
        res = gpsoauth.exchange_token(email, oauth_token, android_id)
        master_token = res.get("Token")
        if not master_token:
            print(f"\n❌ Token exchange failed: {res}")
            sys.exit(1)

        print("\n" + "=" * 70)
        print(" ✅ MASTER TOKEN SUCCESSFULLY GENERATED!")
        print("=" * 70)
        print(f"\nEmail: {email}")
        print(f"Android ID: {android_id}")
        print(f"\nMaster Token:\n{master_token}\n")
        print("=" * 70)
        print("Keep this Master Token secret. It is permanent and does not expire.")

        # Save to credentials.json
        creds = {
            "email": email,
            "master_token": master_token,
            "android_id": android_id,
        }
        with open("credentials.json", "w") as f:
            json.dump(creds, f, indent=2)
        print("\n[INFO] Saved credentials to credentials.json")

    except Exception as e:
        print(f"\n❌ Error during token exchange: {e}")


if __name__ == "__main__":
    main()
