# Google Master Token Generator

This tool allows you to obtain a permanent **Google Master Token (`aas_et/...`)** for the Google Family Link integration.

---

## Why Use a Master Token?
- **Does not expire**: Unlike browser cookies (`__Secure-1PSIDTS`) which can expire in hours due to Google's dynamic session rotation, the Master Token is permanent (years of validity).
- **Official Android Flow**: Emulates how the official Google Family Link Android application authenticates via Google Play Services (`gpsoauth`).

---

## Requirements

Python 3.8+ with `gpsoauth` library installed:

```bash
pip install gpsoauth
```

---

## Step-by-Step Instructions

### 1. Run the Generator Script
In your terminal, execute:

```bash
python3 tools/get_master_token.py
```

### 2. Enter Your Google Account Email
Enter the email address of the parent Google account managing the family.

### 3. Open the Authentication Link
The script will provide an Embedded Setup link:
```text
https://accounts.google.com/EmbeddedSetup?source=android&xoauth_display_name=Android%20Device&lang=en&cc=us
```
1. Open this URL in your browser.
2. Sign in with your parent Google credentials (and complete 2-Step Verification).
3. At the final step, the browser will navigate to a page that seems stuck or ends with `#close`:
   ```text
   https://accounts.google.com/v3/signin/speedbump/embeddedsigninconsent?...#close
   ```

### 4. Copy the `oauth_token`
Because the browser doesn't know how to handle the Android `#close` intent, the authentication cookie is already set:

1. On that stuck page, open **Browser Developer Tools**:
   - macOS: `Cmd + Option + I`
   - Windows/Linux: `F12` or `Ctrl + Shift + I`
2. Navigate to the **Application** (Chrome/Edge) or **Storage** (Firefox/Safari) tab.
3. In the left sidebar, expand **Cookies** → click **`https://accounts.google.com`**.
4. Locate the cookie named **`oauth_token`**.
5. Double-click its **Value** and copy it (starts with `oauth2_4/...` or `4/...`).

### 5. Paste the Token
Paste the copied `oauth_token` value (or the full URL if it contained `oauth_token=`) back into your terminal prompt.

### 6. Done!
The script will exchange this temporary token with Google OAuth servers and output your permanent **Master Token**:
```text
======================================================================
 ✅ MASTER TOKEN SUCCESSFULLY GENERATED!
======================================================================
Master Token:
aas_et/AKppw...
======================================================================
```
It will also automatically create a `credentials.json` file in the current working directory.
