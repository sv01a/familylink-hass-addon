#!/usr/bin/env python3
"""
Google Family Link CLI & Automation Controller (Lightweight, No Playwright)
"""

import argparse
import hashlib
import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import requests

BASE_URL = "https://kidsmanagement-pa.clients6.google.com/kidsmanagement/v1"
ORIGIN = "https://familylink.google.com"
API_KEY = "AIzaSyAQb1gupaJhY3CXQy2xmTwJMcjmot3M2hw"

class FamilyLinkClient:
    def __init__(self, cookies_file="cookies.json"):
        self.cookies_file = Path(cookies_file)
        self.session = requests.Session()
        self.cookies = {}
        self.load_cookies()

    def load_cookies(self):
        """Загрузка кук из json файла или Netscape cookies.txt"""
        if not self.cookies_file.exists():
            print(f"❌ Файл кук {self.cookies_file} не найден!")
            print("Создай cookies.json со своими куками Google (SAPISID, SID, HSID, SSID и др.)")
            sys.exit(1)

        content = self.cookies_file.read_text().strip()
        if content.startswith("{") or content.startswith("["):
            data = json.loads(content)
            if isinstance(data, list):
                # Формат экспорта расширений (Cookie-Editor / EditThisCookie)
                for c in data:
                    self.cookies[c["name"]] = c["value"]
            elif isinstance(data, dict):
                self.cookies = data
        else:
            # Текстовый формат netscape / raw string
            for line in content.split(";"):
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    self.cookies[k] = v

        # Собираем заголовок Cookie
        cookie_header = "; ".join([f"{k}={v}" for k, v in self.cookies.items()])
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
            "Origin": ORIGIN,
            "Referer": f"{ORIGIN}/",
            "X-Goog-Api-Key": API_KEY,
            "Cookie": cookie_header,
        }

    def _get_headers(self):
        """Обновление Authorization с актуальным timestamp"""
        headers = dict(self.headers)
        sapisid = self.cookies.get("SAPISID") or self.cookies.get("__Secure-3PAPISID")
        if sapisid:
            now = int(time.time() * 1000)
            sapisidhash = hashlib.sha1(f"{now} {sapisid} {ORIGIN}".encode("utf-8")).hexdigest()
            headers["Authorization"] = f"SAPISIDHASH {now}_{sapisidhash}"
        return headers

    def get_family_members(self):
        """Получить членов семьи и ID детей"""
        url = f"{BASE_URL}/families/mine/members?allowEmptyFamily=true"
        r = self.session.get(url, headers=self._get_headers())
        if r.status_code != 200:
            raise RuntimeError(f"Ошибка получения членов семьи ({r.status_code}): {r.text}")

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
        """Получить список устройств ребенка"""
        url = f"{BASE_URL}/people/{account_id}/appsandusage"
        params = [
            ("capabilities", "CAPABILITY_APP_USAGE_SESSION"),
            ("capabilities", "CAPABILITY_SUPERVISION_CAPABILITIES"),
        ]
        r = self.session.get(url, headers=self._get_headers(), params=params)
        if r.status_code != 200:
            raise RuntimeError(f"Ошибка получения устройств ({r.status_code}): {r.text}")

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
        """
        Получить статистику экранного времени ребенка.
        target_date: строка YYYY-MM-DD или None (сегодня / последний день с активностью)
        """
        url = f"{BASE_URL}/people/{account_id}/appsandusage"
        params = [
            ("capabilities", "CAPABILITY_APP_USAGE_SESSION"),
            ("capabilities", "CAPABILITY_SUPERVISION_CAPABILITIES"),
        ]
        r = self.session.get(url, headers=self._get_headers(), params=params)
        if r.status_code != 200:
            raise RuntimeError(f"Ошибка получения статистики использования ({r.status_code}): {r.text}")

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
        if not sessions:
            return {"date": None, "total_seconds": 0, "by_device": [], "by_app": []}

        if target_date:
            try:
                dt = datetime.strptime(target_date, "%Y-%m-%d")
                target_tuple = (dt.year, dt.month, dt.day)
            except ValueError:
                raise ValueError("Дата должна быть в формате YYYY-MM-DD")
        else:
            all_dates = [
                (s["date"]["year"], s["date"]["month"], s["date"]["day"])
                for s in sessions if "date" in s
            ]
            target_tuple = max(all_dates) if all_dates else None

        if not target_tuple:
            return {"date": None, "total_seconds": 0, "by_device": [], "by_app": []}

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

    def grant_bonus_time(self, account_id, device_id, minutes):
        """Выдать бонусные минуты на Android устройство"""
        seconds = int(minutes) * 60
        url = f"{BASE_URL}/people/{account_id}/timeLimitOverrides:batchCreate"

        # 10 = Android Bonus Time override
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
        if r.status_code == 200:
            print(f"✅ УСПЕШНО! Начислено +{minutes} мин на устройство {device_id}!")
            return True
        else:
            print(f"❌ Ошибка начисления бонуса ({r.status_code}): {r.text}")
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
        if r.status_code == 200:
            print(f"✅ Устройство успешно {action}ed!")
            return True
        else:
            print(f"❌ Ошибка {action} ({r.status_code}): {r.text}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Google Family Link Automation Tool")
    parser.add_argument("--cookies", default="cookies.json", help="Путь к cookies.json")
    parser.add_argument("--list", action="store_true", help="Показать детей и устройства")
    parser.add_argument("--usage", action="store_true", help="Показать использованное экранное время")
    parser.add_argument("--date", help="Дата (YYYY-MM-DD)")
    parser.add_argument("--bonus", type=int, help="Выдать бонусное время (в минутах)")
    parser.add_argument("--lock", action="store_true", help="Заблокировать устройство")
    parser.add_argument("--unlock", action="store_true", help="Разблокировать устройство")
    parser.add_argument("--child", help="ID ребенка (опционально, если один — автовыбор)")
    parser.add_argument("--device", help="ID устройства (опционально, если одно — автовыбор)")

    args = parser.parse_args()
    client = FamilyLinkClient(cookies_file=args.cookies)

    if args.list:
        children = client.get_family_members()
        print(f"Найдено детей: {len(children)}")
        for ch in children:
            print(f"\n👶 Ребенок: {ch['name']} (ID: {ch['id']})")
            devices = client.get_devices(ch['id'])
            for d in devices:
                print(f"  📱 Устройство: {d['name']} (ID: {d['id']})")
        return

    # Авто-определение ребенка и устройства, если не заданы
    children = client.get_family_members()
    if not children:
        print("❌ Не найдено детей под опекой!")
        return

    child_id = args.child or children[0]["id"]
    child_name = next((c["name"] for c in children if c["id"] == child_id), "Ребенок")

    if args.usage:
        usage = client.get_screen_time(child_id, target_date=args.date)
        total_sec = usage["total_seconds"]
        hours = total_sec // 3600
        mins = (total_sec % 3600) // 60

        print(f"\n📊 Экранное время [{usage["date"]}] для {child_name}:")
        print(f"   Всего: {hours} ч {mins} мин ({total_sec // 60} мин)")

        if usage["by_device"]:
            print("\n📱 По устройствам:")
            for d in usage["by_device"]:
                dh = d["seconds"] // 3600
                dm = (d["seconds"] % 3600) // 60
                time_str = f"{dh} ч {dm} мин" if dh else f"{dm} мин"
                print(f"   • {d["device_name"]}: {time_str}")

        if usage["by_app"]:
            print("\n🎮 Топ приложений:")
            for a in usage["by_app"][:10]:
                ah = a["seconds"] // 3600
                am = (a["seconds"] % 3600) // 60
                as_sec = a["seconds"] % 60
                time_str = f"{ah} ч {am} мин" if ah else (f"{am} мин {as_sec} сек" if am else f"{as_sec} сек")
                print(f"   • {a["title"]}: {time_str}")
        return
    devices = client.get_devices(child_id)
    if not devices:
        print("❌ Не найдено устройств у ребенка!")
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
