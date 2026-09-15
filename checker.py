import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE = "http://www.happyikindergarten.com"
LOGIN_URL = BASE + "/core/module/membership/membership.html?Mode=login"

BOARDS = {
    "사랑반": {"pageCode": 54, "boardID": "www54"},
    "가정통신문": {"pageCode": 21, "boardID": "www21"},
    "오늘의 식단": {"pageCode": 32, "boardID": "www32"},
}

STATE_FILE = Path(".state/seen.json")

STATE_DIR = Path(".state")
STATE_DIR.mkdir(parents=True, exist_ok=True)

HEARTBEAT_FILE = Path(".state/heartbeat.txt")

POST_ID_PATTERNS = [
    re.compile(r"permitCheck\('beforeview',\s*'(\d+)'"),
    re.compile(r"[?&]num=(\d+)"),
]
DATE_RE = re.compile(r"\b20\d{2}[.\-/]\d{2}[.\-/]\d{2}\b")


def required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required secret: {name}")
    return value


def post_hash(board, post_id):
    return hashlib.sha256(f"{board}:{post_id}".encode("utf-8")).hexdigest()


def load_state():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def touch_heartbeat():
    """Keep scheduled workflow from going inactive on a public repo."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    should_write = True
    if HEARTBEAT_FILE.exists():
        try:
            old = datetime.fromisoformat(HEARTBEAT_FILE.read_text().strip())
            should_write = (now - old).days >= 30
        except Exception:
            pass
    if should_write:
        HEARTBEAT_FILE.write_text(now.isoformat(), encoding="utf-8")


def extract_post_id(tag):
    text = (tag.get("onclick", "") or "") + " " + (tag.get("href", "") or "")
    for pat in POST_ID_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1)
    return None


def find_date_near(tag):
    tr = tag.find_parent("tr")
    if tr:
        m = DATE_RE.search(tr.get_text(" ", strip=True))
        if m:
            return m.group(0)
    parent = tag.parent
    for _ in range(6):
        if not parent:
            break
        m = DATE_RE.search(parent.get_text(" ", strip=True))
        if m:
            return m.group(0)
        parent = parent.parent
    return ""


def parse_posts(html, board_id):
    soup = BeautifulSoup(html, "html.parser")
    found = {}

    for a in soup.find_all("a"):
        post_id = extract_post_id(a)
        if not post_id:
            continue

        title = a.get_text(" ", strip=True)
        if not title or title in {"다운로드", "이전", "다음"}:
            continue

        href = a.get("href", "") or ""
        detail_url = (
            urljoin(BASE, href)
            if href and not href.lower().startswith("javascript:")
            else f"{BASE}/main/sub.html?Mode=view&boardID={board_id}&num={post_id}&page=0&keyfield=&key=&bCate="
        )

        found.setdefault(post_id, {
            "id": post_id,
            "title": title,
            "date": find_date_near(a),
            "url": detail_url,
        })

    return sorted(found.values(), key=lambda x: int(x["id"]), reverse=True)


def login(context, user_id, password):
    page = context.new_page()
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
    page.locator('input[name="id"]').fill(user_id)
    page.locator('input[name="password"]').fill(password)
    page.locator("#loginBtn").click()
    time.sleep(3)

    test = context.new_page()
    test.goto(BASE + "/main/sub.html?pageCode=54",
              wait_until="domcontentloaded", timeout=30000)
    html = test.content()

    if "logout.php" not in html and "로그아웃" not in html:
        raise RuntimeError("Could not confirm kindergarten login.")
    return test


def send_push(app_id, api_key, pages_url, board, post):
    target = (
        f"{pages_url.rstrip('/')}/"
        f"?board={quote(board)}"
        f"&title={quote(post['title'])}"
        f"&target={quote(post['url'], safe='')}"
    )

    payload = {
        "app_id": app_id,
        "target_channel": "push",
        "included_segments": ["Subscribed Users"],
        "headings": {"en": f"해피아이 · {board}"},
        "contents": {"en": post["title"]},
        "url": target,
    }

    r = requests.post(
        "https://api.onesignal.com/notifications",
        headers={
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    r.raise_for_status()


def main():
    user_id = required_env("HAPPI_ID")
    password = required_env("HAPPI_PASSWORD")
    os_app_id = required_env("ONESIGNAL_APP_ID")
    os_api_key = required_env("ONESIGNAL_API_KEY")
    pages_url = required_env("PAGES_URL")

    state = load_state()
    touch_heartbeat()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="ko-KR")

        try:
            page = login(context, user_id, password)
            new_state = dict(state)
            total_new = 0

            for board, info in BOARDS.items():
                page.goto(
                    f"{BASE}/main/sub.html?pageCode={info['pageCode']}",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                posts = parse_posts(page.content(), info["boardID"])

                current_hashes = [post_hash(board, p["id"]) for p in posts]
                previous = set(state.get(board, []))

                if board not in state:
                    # First cloud run becomes baseline; no old-post notification storm.
                    new_posts = []
                else:
                    new_posts = [
                        post for post in posts
                        if post_hash(board, post["id"]) not in previous
                    ]

                for post in reversed(new_posts):
                    send_push(os_app_id, os_api_key, pages_url, board, post)
                    total_new += 1

                merged = list(dict.fromkeys(current_hashes + list(previous)))[:250]
                new_state[board] = merged

            save_state(new_state)
            print(f"Check completed. New posts: {total_new}")

        finally:
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except PlaywrightTimeoutError:
        raise SystemExit("Kindergarten site timed out.")
