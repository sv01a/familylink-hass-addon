#!/usr/bin/env python3
"""
Google Family Link CLI & Automation Controller
Supports Master Token auto-session minting via gpsoauth (MergeSession) and Browser Cookies
"""

import argparse
from collections import defaultdict
from datetime import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
import time
import requests

try:
    import gpsoauth
except ImportError:
    gpsoauth = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("familylink_ctl")

BASE_URL = "https://kidsmanagement-pa.clients6.google.com/kidsmanagement/v1"
ORIGIN = "https://familylink.google.com"
API_KEY = "AIzaSyAQb1gupaJhY3CXQy2xmTwJMcjmot3M2hw"


class FamilyLinkClient:
    def __init__(self, cookies_file="cookies.json", credentials_file=None):
        self.cookies_file = Path(cookies_file)
        self.credentials_file = Path(credentials_file) if credentials_file else Path("credentials.json")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
        })
        self.cookies = {}
        self.master_token_info = None
        self.session_expiry = 0
        self.load_auth()

    def load_auth(self):
        """Load credentials from environment (add-on), credentials.json (Master Token) or cookies.json"""
        email = os.getenv("GOOGLE_EMAIL")
        master_token = os.getenv("MASTER_TOKEN")
        android_id = os.getenv("ANDROID_ID")
        if email and master_token:
            if not self.master_token_info or self.master_token_info.get("master_token") != master_token:
                self.master_token_info = {
                    "email": email,
                    "master_token": master_token,
                    "android_id": android_id or "0123456789abcdef",
                }
                logger.info("Loaded Master Token configuration from environment.")
                self._ensure_master_session()
            return

        if self.credentials_file and self.credentials_file.exists():
            try:
                creds = json.loads(self.credentials_file.read_text())
                if creds.get("master_token") and creds.get("email"):
                    self.master_token_info = creds
                    logger.info("Loaded Master Token configuration.")
                    self._ensure_master_session()
                    return
            except Exception as e:
                logger.warning(f"Failed to load credentials file: {e}")

        # Fallback to cookies
        if self.cookies_file.exists():
            content = self.cookies_file.read_text().strip()
            if content.startswith("{") or content.startswith("["):
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        for c in data:
                            self.cookies[c["name"]] = c["value"]
                    elif isinstance(data, dict):
                        self.cookies = data
                except Exception as e:
                    logger.warning(f"Failed to parse cookies JSON: {e}")
            else:
                for line in content.split(";"):
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        self.cookies[k] = v
            if self.cookies:
                logger.info("Loaded browser cookies successfully.")
                for k, v in self.cookies.items():
                    self.session.cookies.set(k, v, domain=".google.com")

    def _ensure_master_session(self, force=False):
        """Mint brand new fresh Google web session cookies from Master Token"""
        if not self.master_token_info:
            return

        now = time.time()
        # Refresh session every 12 hours or on demand
        if not force and self.session_expiry and now < self.session_expiry:
            return

        if not gpsoauth:
            raise RuntimeError("gpsoauth library is required for Master Token mode")

        email = self.master_token_info["email"]
        master_token = self.master_token_info["master_token"]
        android_id = self.master_token_info.get("android_id", "0123456789abcdef")

        logger.info("Minting fresh Family Link session cookies via Master Token...")
        res = gpsoauth.perform_oauth(
            email=email,
            master_token=master_token,
            android_id=android_id,
            service="weblogin:continue=https://familylink.google.com",
            app="com.google.android.apps.kids.familylink",
            client_sig="38918a453d07199354f8b19af05ec6562ced5788",
        )

        merge_url = res.get("Auth")
        if not merge_url or not merge_url.startswith("http"):
            raise RuntimeError(f"Failed to exchange Master Token for weblogin session: {res}")

        # Follow redirects on Google MergeSession endpoint to collect fresh cookies
        resp = self.session.get(merge_url, allow_redirects=True)
        if resp.status_code not in (200, 302):
            raise RuntimeError(f"Failed MergeSession exchange, HTTP status: {resp.status_code}")

        # Populate internal cookies dict
        self.cookies = self.session.cookies.get_dict()
        sapisid = self.cookies.get("SAPISID") or self.cookies.get("__Secure-3PAPISID")
        if not sapisid:
            raise RuntimeError("MergeSession completed, but no SAPISID cookie was set.")

        self.session_expiry = now + 43200  # 12 hours
        logger.info(f"Successfully generated permanent web session. Cookies count: {len(self.cookies)}")

    def _get_headers(self):
        """Generate request headers with valid SAPISIDHASH timestamp"""
        self._ensure_master_session()

        cookie_dict = self.session.cookies.get_dict()
        if not cookie_dict:
            cookie_dict = self.cookies

        cookie_header = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
            "Origin": ORIGIN,
            "Referer": f"{ORIGIN}/",
            "X-Goog-Api-Key": API_KEY,
            "Cookie": cookie_header,
        }

        sapisid = cookie_dict.get("SAPISID") or cookie_dict.get("__Secure-3PAPISID")
        if sapisid:
            now = int(time.time() * 1000)
            sapisidhash = hashlib.sha1(f"{now} {sapisid} {ORIGIN}".encode("utf-8")).hexdigest()
            headers["Authorization"] = f"SAPISIDHASH {now}_{sapisidhash}"

        return headers

    def get_family_members(self):
        """Retrieve family members and child IDs"""
        url = f"{BASE_URL}/families/mine/members?allowEmptyFamily=true"
        r = self.session.get(url, headers=self._get_headers())
        if r.status_code == 401 and self.master_token_info:
            logger.info("Session expired, forcing Master Token re-authentication...")
            self._ensure_master_session(force=True)
            r = self.session.get(url, headers=self._get_headers())

        if r.status_code != 200:
            raise RuntimeError(f"Failed to fetch family members ({r.status_code}): {r.text}")

        data = r.json()
        children = []
        for m in data.get("members", []):
            role = (m.get("role") or m.get("familyRole") or "").lower()
            if role in ["child", "supervised_member", "head_of_household_supervised_child"]:
                children.append({
                    "id": m.get("userId") or m.get("id"),
                    "name": m.get("profile", {}).get("displayName") or m.get("profile", {}).get("givenName", "Child"),
                })
        return children

    def get_devices(self, account_id):
        """Retrieve devices for a given child account"""
        url = f"{BASE_URL}/people/{account_id}/appsandusage"
        params = [
            ("capabilities", "CAPABILITY_APP_USAGE_SESSION"),
            ("capabilities", "CAPABILITY_SUPERVISION_CAPABILITIES"),
        ]
        r = self.session.get(url, headers=self._get_headers(), params=params)
        if r.status_code == 401 and self.master_token_info:
            self._ensure_master_session(force=True)
            r = self.session.get(url, headers=self._get_headers(), params=params)

        if r.status_code != 200:
            raise RuntimeError(f"Failed to fetch devices ({r.status_code}): {r.text}")

        data = r.json()
        devices = []
        for dev in data.get("deviceInfo", []):
            display = dev.get("displayInfo", {})
            name = display.get("friendlyName") or display.get("model") or display.get("defaultFriendlyName") or "Android Device"
            model = display.get("model")
            label = f"{name} ({model})" if model and model != name else name
            devices.append({
                "id": dev.get("deviceId"),
                "name": label,
            })
        return devices

    def get_screen_time(self, account_id, target_date=None):
        """Retrieve screen time stats for a child"""
        url = f"{BASE_URL}/people/{account_id}/appsandusage"
        params = [
            ("capabilities", "CAPABILITY_APP_USAGE_SESSION"),
            ("capabilities", "CAPABILITY_SUPERVISION_CAPABILITIES"),
        ]
        r = self.session.get(url, headers=self._get_headers(), params=params)
        if r.status_code == 401 and self.master_token_info:
            self._ensure_master_session(force=True)
            r = self.session.get(url, headers=self._get_headers(), params=params)

        if r.status_code != 200:
            raise RuntimeError(f"Failed to fetch usage statistics ({r.status_code}): {r.text}")

        data = r.json()

        app_titles = {
            a.get("packageName"): a.get("title")
            for a in data.get("apps", [])
            if a.get("packageName")
        }

        device_names = {}
        for dev in data.get("deviceInfo", []):
            disp = dev.get("displayInfo", {})
            name = disp.get("friendlyName") or disp.get("model") or "Android Device"
            device_names[dev.get("deviceId")] = name

        sessions = data.get("appUsageSessions", [])
        now = datetime.now()
        today_tuple = (now.year, now.month, now.day)

        if target_date:
            try:
                dt = datetime.strptime(target_date, "%Y-%m-%d")
                target_tuple = (dt.year, dt.month, dt.day)
            except ValueError:
                raise ValueError("Date must be in format YYYY-MM-DD")
        else:
            all_dates = [
                (s["date"]["year"], s["date"]["month"], s["date"]["day"])
                for s in sessions if "date" in s
            ]
            max_date = max(all_dates) if all_dates else None
            # If the device has sessions recorded for a date ahead of local time (e.g. timezone difference),
            # respect the device's date. Otherwise, default to today's date so that usage resets to 0
            # when a new day starts.
            if max_date and max_date > today_tuple:
                target_tuple = max_date
            else:
                target_tuple = today_tuple

        date_str = f"{target_tuple[0]}-{target_tuple[1]:02d}-{target_tuple[2]:02d}"

        if not sessions:
            return {"date": date_str, "total_seconds": 0, "by_device": [], "by_app": []}

        by_device = defaultdict(float)
        by_app = defaultdict(float)

        for s in sessions:
            d = s.get("date", {})
            if (d.get("year"), d.get("month"), d.get("day")) == target_tuple:
                usage_str = s.get("usage", "0s").rstrip("s")
                sec = float(usage_str)
                dev_id = s.get("deviceMudId")
                pkg = s.get("appId", {}).get("androidAppPackageName")
                by_device[dev_id] += sec
                by_app[pkg] += sec

        total_seconds = sum(by_device.values())
        date_str = f"{target_tuple[0]}-{target_tuple[1]:02d}-{target_tuple[2]:02d}"

        device_stats = []
        for dev_id, sec in sorted(by_device.items(), key=lambda x: -x[1]):
            device_stats.append({
                "device_id": dev_id,
                "device_name": device_names.get(dev_id, "Unknown Device"),
                "seconds": int(sec),
            })

        app_stats = []
        for pkg, sec in sorted(by_app.items(), key=lambda x: -x[1]):
            app_stats.append({
                "package": pkg,
                "title": app_titles.get(pkg, pkg),
                "seconds": int(sec),
            })

        return {
            "date": date_str,
            "total_seconds": int(total_seconds),
            "by_device": device_stats,
            "by_app": app_stats,
        }

    def get_applied_time_limits(self, account_id):
        """Retrieve live time limits, remaining minutes, and locked state per device"""
        url = f"{BASE_URL}/people/{account_id}/appliedTimeLimits"
        r = self.session.get(url, headers=self._get_headers())
        if r.status_code == 401 and self.master_token_info:
            self._ensure_master_session(force=True)
            r = self.session.get(url, headers=self._get_headers())

        if r.status_code != 200:
            logger.warning(f"Failed to fetch appliedTimeLimits ({r.status_code}): {r.text[:100]}")
            return {}

        data = r.json()
        result = {}
        for item in data.get("appliedTimeLimits", []):
            dev_id = item.get("deviceId")
            if not dev_id:
                continue

            remaining_mins = item.get("currentUsageRemainingMins", 0)
            is_locked = bool(item.get("isLocked", False))
            active_policy = item.get("activePolicy", "unknown")
            daily_limit_mins = item.get("currentUsageLimitEntry", {}).get("usageQuotaMins", 0)

            result[dev_id] = {
                "remaining_minutes": int(remaining_mins),
                "is_locked": is_locked,
                "active_policy": active_policy,
                "daily_limit_minutes": int(daily_limit_mins),
            }
        return result

    def get_active_bonus_time(self, account_id):
        """Calculate active bonus minutes remaining per device from timeLimit overrides"""
        url = f"{BASE_URL}/people/{account_id}/timeLimit"
        r = self.session.get(url, headers=self._get_headers())
        if r.status_code == 401 and self.master_token_info:
            self._ensure_master_session(force=True)
            r = self.session.get(url, headers=self._get_headers())

        if r.status_code != 200:
            logger.warning(f"Failed to fetch timeLimit ({r.status_code}): {r.text[:100]}")
            return {}

        data = r.json()
        overrides = data.get("timeLimit", {}).get("overrides", [])
        now_ms = int(time.time() * 1000)

        bonus_by_dev = defaultdict(int)

        for o in overrides:
            if o.get("action") == "unlockFor":
                dev_id = o.get("deviceId")
                created_ms = int(o.get("createdAtMillis", 0))
                dur_str = o.get("unlockForData", {}).get("duration", "0s").rstrip("s")
                duration_sec = int(dur_str) if dur_str.isdigit() else 0
                expires_ms = created_ms + (duration_sec * 1000)

                if expires_ms > now_ms:
                    rem_sec = (expires_ms - now_ms) // 1000
                    rem_mins = int((rem_sec + 59) // 60)
                    bonus_by_dev[dev_id] += rem_mins

        return dict(bonus_by_dev)

    def grant_bonus_time(self, account_id, device_id, minutes):
        """Grant bonus screen time in minutes"""
        seconds = int(minutes) * 60
        url = f"{BASE_URL}/people/{account_id}/timeLimitOverrides:batchCreate"

        payload = [
            None,
            account_id,
            [
                [
                    None, None, 10, device_id,
                    None, None, None, None, None, None, None, None, None,
                    [[str(seconds), 0]]
                ]
            ],
            [1]
        ]

        headers = self._get_headers()
        headers["Content-Type"] = "application/json+protobuf"
        r = self.session.post(url, headers=headers, data=json.dumps(payload))
        if r.status_code == 401 and self.master_token_info:
            self._ensure_master_session(force=True)
            headers = self._get_headers()
            headers["Content-Type"] = "application/json+protobuf"
            r = self.session.post(url, headers=headers, data=json.dumps(payload))

        if r.status_code == 200:
            logger.info(f"Successfully granted +{minutes}m to device {device_id}!")
            return True
        else:
            logger.error(f"Failed to grant bonus time ({r.status_code}): {r.text}")
            return False

    def control_device(self, account_id, device_id, action="lock"):
        """1 = Lock, 4 = Unlock"""
        action_code = 1 if action == "lock" else 4
        url = f"{BASE_URL}/people/{account_id}/timeLimitOverrides:batchCreate"
        payload = [
            None,
            account_id,
            [[None, None, action_code, device_id]],
            [1]
        ]
        headers = self._get_headers()
        headers["Content-Type"] = "application/json+protobuf"
        r = self.session.post(url, headers=headers, data=json.dumps(payload))
        if r.status_code == 401 and self.master_token_info:
            self._ensure_master_session(force=True)
            headers = self._get_headers()
            headers["Content-Type"] = "application/json+protobuf"
            r = self.session.post(url, headers=headers, data=json.dumps(payload))

        if r.status_code == 200:
            logger.info(f"Device successfully {action}ed!")
            return True
        else:
            logger.error(f"Failed to execute {action} on device ({r.status_code}): {r.text}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Google Family Link Automation Tool")
    parser.add_argument("--cookies", default="cookies.json", help="Path to cookies file")
    parser.add_argument("--credentials", default="credentials.json", help="Path to credentials file")
    parser.add_argument("--list", action="store_true", help="List children and devices")
    parser.add_argument("--usage", action="store_true", help="Show screen time usage")
    parser.add_argument("--limits", action="store_true", help="Show time limits and remaining time")
    parser.add_argument("--date", help="Date in YYYY-MM-DD format")
    parser.add_argument("--bonus", type=int, help="Grant bonus time (minutes)")
    parser.add_argument("--lock", action="store_true", help="Lock device")
    parser.add_argument("--unlock", action="store_true", help="Unlock device")
    parser.add_argument("--child", help="Child ID (optional, defaults to first child)")
    parser.add_argument("--device", help="Device ID (optional, defaults to first device)")

    args = parser.parse_args()
    client = FamilyLinkClient(cookies_file=args.cookies, credentials_file=args.credentials)

    if args.list:
        children = client.get_family_members()
        print(f"Children found: {len(children)}")
        for ch in children:
            print(f"\n👤 Child: {ch['name']} (ID: {ch['id']})")
            devices = client.get_devices(ch['id'])
            for d in devices:
                print(f"  📱 Device: {d['name']} (ID: {d['id']})")
        return

    children = client.get_family_members()
    if not children:
        logger.error("No supervised children found!")
        return

    child_id = args.child or children[0]["id"]
    child_name = next((c["name"] for c in children if c["id"] == child_id), "Child")

    if args.limits:
        limits = client.get_applied_time_limits(child_id)
        bonuses = client.get_active_bonus_time(child_id)
        print(f"\n⏳ Time limits and remaining time for {child_name}:")
        devices = client.get_devices(child_id)
        for d in devices:
            dev_id = d["id"]
            lim = limits.get(dev_id, {})
            b = bonuses.get(dev_id, 0)
            print(f"  📱 {d['name']}:")
            print(f"     Locked: {lim.get('is_locked', False)} ({lim.get('active_policy', 'none')})")
            print(f"     Remaining quota: {lim.get('remaining_minutes', 0)} min")
            print(f"     Active bonus remaining: {b} min")
        return

    if args.usage:
        usage = client.get_screen_time(child_id, target_date=args.date)
        total_sec = usage["total_seconds"]
        hours = total_sec // 3600
        mins = (total_sec % 3600) // 60

        print(f"\n📊 Screen time [{usage['date']}] for {child_name}:")
        print(f"   Total: {hours}h {mins}m ({total_sec // 60} min)")

        if usage["by_device"]:
            print("\n📱 By device:")
            for d in usage["by_device"]:
                dh = d["seconds"] // 3600
                dm = (d["seconds"] % 3600) // 60
                time_str = f"{dh}h {dm}m" if dh else f"{dm}m"
                print(f"   • {d['device_name']}: {time_str}")

        if usage["by_app"]:
            print("\n🎮 Top applications:")
            for a in usage["by_app"][:10]:
                ah = a["seconds"] // 3600
                am = (a["seconds"] % 3600) // 60
                as_sec = a["seconds"] % 60
                time_str = f"{ah}h {am}m" if ah else (f"{am}m {as_sec}s" if am else f"{as_sec}s")
                print(f"   • {a['title']}: {time_str}")
        return

    devices = client.get_devices(child_id)
    if not devices:
        logger.error("No devices found for child!")
        return
    device_id = args.device or devices[0]["id"]

    if args.bonus:
        client.grant_bonus_time(child_id, device_id, args.bonus)
    elif args.lock:
        client.control_device(child_id, device_id, action="lock")
    elif args.unlock:
        client.control_device(child_id, device_id, action="unlock")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
