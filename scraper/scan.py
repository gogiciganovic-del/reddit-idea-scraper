#!/usr/bin/env python3
"""
Tjedni Reddit skener pritužbi i poslovnih ideja.

NE treba Reddit API app/ključ. Koristi Redditove javne, besplatne JSON
feedove (npr. https://www.reddit.com/r/croatia/new.json) koji su
dostupni bez prijave i bez OAuth-a — dovoljan je samo pristojan
User-Agent header. Reddit je u 2026. zatvorio izradu novih "legacy API"
script-aplikacija za obične korisnike (samo za moderacijske slučajeve
uz odobrenje), pa ovaj pristup zaobilazi tu prepreku i dalje ostaje
100% besplatan.

Izlaz:
  data/latest.csv   — svi pogoci (sirovi podaci)
  data/summary.md   — sažetak na vrhu (top pogoci + učestale teme)
  data/history.csv  — kumulativna povijest (append, dedup po post id-u)

Pokreće se tjedno preko GitHub Actions (.github/workflows/reddit-scan.yml),
potpuno besplatno na GitHub-ovoj infrastrukturi (koja ima pun pristup
internetu, za razliku od nekih sandboxed okruženja).
"""

import csv
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone

import requests

from config import SUBREDDITS, POSTS_PER_SUBREDDIT, KEYWORDS, CJENKO_RELEVANT_HINTS

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LATEST_CSV = os.path.join(DATA_DIR, "latest.csv")
HISTORY_CSV = os.path.join(DATA_DIR, "history.csv")
SUMMARY_MD = os.path.join(DATA_DIR, "summary.md")

USER_AGENT = "cjenko-idea-scanner/1.0 (besplatni istrazivacki skener, by u/gogiciganovic-del)"
REQUEST_DELAY_SECONDS = 2.5  # pristojan razmak između zahtjeva prema Redditu
PAGE_SIZE = 100  # max koji Reddit dopušta po stranici

STOPWORDS = set(
    "i the a an of to for in on is are was were be been and or but with "
    "this that it my your you we they he she just like get got know don't "
    "do does did not no yes app apps about so very really je su da li za "
    "na od do kad kada koji koja koje sam smo ste imam ima ovo ono neki "
    "nešto netko tko što kako zašto"
    .split()
)


def fetch_new_posts(sub_name, limit):
    """Dohvati najnovije postove s r/<sub_name> preko javnog .json feeda."""
    posts = []
    after = None
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    while len(posts) < limit:
        url = f"https://www.reddit.com/r/{sub_name}/new.json"
        params = {"limit": min(PAGE_SIZE, limit - len(posts))}
        if after:
            params["after"] = after
        resp = session.get(url, params=params, timeout=15)
        if resp.status_code == 429:
            print(f"[upozorenje] {sub_name}: rate-limited, čekam 10s...", file=sys.stderr)
            time.sleep(10)
            continue
        resp.raise_for_status()
        data = resp.json()
        children = data.get("data", {}).get("children", [])
        if not children:
            break
        for child in children:
            posts.append(child["data"])
        after = data.get("data", {}).get("after")
        if not after:
            break
        time.sleep(REQUEST_DELAY_SECONDS)

    return posts


def find_matches(text):
    text_l = text.lower()
    hits = []
    for bucket, phrases in KEYWORDS.items():
        for phrase in phrases:
            if phrase in text_l:
                hits.append((bucket, phrase))
    return hits


def is_cjenko_relevant(text):
    text_l = text.lower()
    return any(hint in text_l for hint in CJENKO_RELEVANT_HINTS)


def load_existing_ids():
    if not os.path.exists(HISTORY_CSV):
        return set()
    with open(HISTORY_CSV, newline="", encoding="utf-8") as f:
        return {row["post_id"] for row in csv.DictReader(f)}


def scan():
    rows = []

    for group, subs in SUBREDDITS.items():
        for sub_name in subs:
            try:
                posts = fetch_new_posts(sub_name, POSTS_PER_SUBREDDIT)
                for post in posts:
                    title = post.get("title", "") or ""
                    selftext = post.get("selftext", "") or ""
                    full_text = f"{title}\n{selftext}"
                    hits = find_matches(full_text)
                    if not hits:
                        continue
                    buckets = sorted({b for b, _ in hits})
                    matched_phrases = sorted({p for _, p in hits})
                    rows.append(
                        {
                            "post_id": post.get("id", ""),
                            "scanned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "group": group,
                            "subreddit": sub_name,
                            "buckets": ";".join(buckets),
                            "matched_keywords": ";".join(matched_phrases),
                            "cjenko_relevant": "da" if is_cjenko_relevant(full_text) else "ne",
                            "score": post.get("score", 0),
                            "num_comments": post.get("num_comments", 0),
                            "created_utc": datetime.fromtimestamp(
                                post.get("created_utc", 0), tz=timezone.utc
                            ).isoformat(timespec="seconds"),
                            "title": title.replace("\n", " ").strip(),
                            "snippet": selftext[:300].replace("\n", " ").strip(),
                            "url": f"https://www.reddit.com{post.get('permalink', '')}",
                        }
                    )
                time.sleep(REQUEST_DELAY_SECONDS)
            except Exception as e:  # ne prekidaj cijeli run zbog jednog suba
                print(f"[upozorenje] {sub_name}: {e}", file=sys.stderr)

    return rows


def write_latest(rows):
    os.makedirs(DATA_DIR, exist_ok=True)
    fieldnames = [
        "post_id", "scanned_at", "group", "subreddit", "buckets",
        "matched_keywords", "cjenko_relevant", "score", "num_comments",
        "created_utc", "title", "snippet", "url",
    ]
    with open(LATEST_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(rows, key=lambda r: r["score"], reverse=True):
            writer.writerow(row)


def append_history(rows):
    seen_ids = load_existing_ids()
    new_rows = [r for r in rows if r["post_id"] not in seen_ids]
    file_exists = os.path.exists(HISTORY_CSV)
    fieldnames = [
        "post_id", "scanned_at", "group", "subreddit", "buckets",
        "matched_keywords", "cjenko_relevant", "score", "num_comments",
        "created_utc", "title", "snippet", "url",
    ]
    with open(HISTORY_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in new_rows:
            writer.writerow(row)
    return new_rows


def top_words(rows, n=15):
    counts = Counter()
    for r in rows:
        for word in re.findall(r"[a-zčćžšđ]{4,}", r["title"].lower()):
            if word not in STOPWORDS:
                counts[word] += 1
    return counts.most_common(n)


def write_summary(new_rows, all_rows):
    os.makedirs(DATA_DIR, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [f"# Reddit sažetak — {now}", ""]

    lines.append(f"Novih pogodaka ovaj tjedan: **{len(new_rows)}** (ukupno u povijesti: {len(all_rows) if all_rows else len(new_rows)})")
    lines.append("")

    relevant = [r for r in new_rows if r["cjenko_relevant"] == "da"]
    lines.append(f"Od toga potencijalno relevantno za Cjenko Akcije (cijene/kupovina): **{len(relevant)}**")
    lines.append("")

    if relevant:
        lines.append("## Cjenko-relevantno (top 10 po bodovima)")
        for r in sorted(relevant, key=lambda r: r["score"], reverse=True)[:10]:
            lines.append(f"- [{r['title']}]({r['url']}) — r/{r['subreddit']}, {r['buckets']}, {r['score']} bodova")
        lines.append("")

    for bucket in ["traži_app", "feature_request", "pritužba"]:
        bucket_rows = [r for r in new_rows if bucket in r["buckets"]]
        if not bucket_rows:
            continue
        label = {
            "traži_app": "Pitaju postoji li app",
            "feature_request": "Traže da netko napravi app",
            "pritužba": "Pritužbe",
        }[bucket]
        lines.append(f"## {label} (top 8)")
        for r in sorted(bucket_rows, key=lambda r: r["score"], reverse=True)[:8]:
            lines.append(f"- [{r['title']}]({r['url']}) — r/{r['subreddit']}, {r['score']} bodova")
        lines.append("")

    words = top_words(new_rows)
    if words:
        lines.append("## Najčešće riječi u naslovima pogodaka (grubi signal tema)")
        lines.append(", ".join(f"{w} ({c})" for w, c in words))
        lines.append("")

    with open(SUMMARY_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    rows = scan()
    write_latest(rows)
    new_rows = append_history(rows)
    write_summary(new_rows, rows)
    print(f"Gotovo: {len(rows)} ukupno pogodaka, {len(new_rows)} novih.")


if __name__ == "__main__":
    main()
