#!/usr/bin/env python3
"""
Tjedni Reddit skener pritužbi i poslovnih ideja.

Koristi SAMO Redditov besplatni službeni API preko PRAW-a, u read-only
modu (treba samo client_id + client_secret, besplatna "script" app na
reddit.com/prefs/apps — nema plaćanja, nema korisničke lozinke).

Izlaz:
  data/latest.csv   — svi pogoci (sirovi podaci)
  data/summary.md   — sažetak na vrhu (top pogoci + učestale teme)
  data/history.csv  — kumulativna povijest (append, dedup po post id-u)

Pokreće se tjedno preko GitHub Actions (.github/workflows/reddit-scan.yml),
potpuno besplatno na GitHub-ovoj infrastrukturi.
"""

import csv
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone

import praw

from config import SUBREDDITS, POSTS_PER_SUBREDDIT, KEYWORDS, CJENKO_RELEVANT_HINTS

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LATEST_CSV = os.path.join(DATA_DIR, "latest.csv")
HISTORY_CSV = os.path.join(DATA_DIR, "history.csv")
SUMMARY_MD = os.path.join(DATA_DIR, "summary.md")

STOPWORDS = set(
    "i the a an of to for in on is are was were be been and or but with "
    "this that it my your you we they he she just like get got know don't "
    "do does did not no yes app apps about so very really je su da li za "
    "na od do kad kada koji koja koje sam smo ste imam ima ovo ono neki "
    "nešto netko tko što kako zašto"
    .split()
)


def get_reddit():
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        sys.exit(
            "Nedostaju REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET env varijable. "
            "Postavi ih kao GitHub Actions secrets (vidi README.md)."
        )
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent="cjenko-idea-scanner/1.0 (by u/gogiciganovic-del)",
    )


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
    reddit = get_reddit()
    seen_ids = load_existing_ids()
    rows = []

    for group, subs in SUBREDDITS.items():
        for sub_name in subs:
            try:
                subreddit = reddit.subreddit(sub_name)
                for post in subreddit.new(limit=POSTS_PER_SUBREDDIT):
                    full_text = f"{post.title}\n{getattr(post, 'selftext', '') or ''}"
                    hits = find_matches(full_text)
                    if not hits:
                        continue
                    buckets = sorted({b for b, _ in hits})
                    matched_phrases = sorted({p for _, p in hits})
                    rows.append(
                        {
                            "post_id": post.id,
                            "scanned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "group": group,
                            "subreddit": sub_name,
                            "buckets": ";".join(buckets),
                            "matched_keywords": ";".join(matched_phrases),
                            "cjenko_relevant": "da" if is_cjenko_relevant(full_text) else "ne",
                            "score": post.score,
                            "num_comments": post.num_comments,
                            "created_utc": datetime.fromtimestamp(
                                post.created_utc, tz=timezone.utc
                            ).isoformat(timespec="seconds"),
                            "title": post.title.replace("\n", " ").strip(),
                            "snippet": (getattr(post, "selftext", "") or "")[:300].replace("\n", " ").strip(),
                            "url": f"https://www.reddit.com{post.permalink}",
                        }
                    )
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
