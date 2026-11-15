#!/usr/bin/env python3
"""
Tjedni Reddit skener pritužbi i poslovnih ideja — v2.

NE treba Reddit API app/ključ. Koristi Redditove javne, besplatne JSON
feedove (new.json, top.json, comments.json) koji su dostupni bez
prijave i bez OAuth-a — dovoljan je samo pristojan User-Agent header.

Što je novo u v2:
  - širi popis fraza (formalno + neformalno, hrvatski + engleski)
  - skenira i KOMENTARE, ne samo naslove postova (comments.json)
  - dodaje "top tjedna" uz "najnovije", da se ne promaše popularne teme
  - composite_score rangiranje (glasovi + komentari + broj poklopljenih
    fraza) umjesto plošnog popisa
  - prati ponavljaju li se iste fraze kroz više različitih tjedana
    (jači signal prave poslovne prilike nego jednokratan spomen)

Izlaz:
  data/latest.csv   — svi pogoci iz zadnjeg pokretanja (sirovi podaci)
  data/summary.md   — sažetak na vrhu (top pogoci, ponavljajuće teme)
  data/history.csv  — kumulativna povijest (append, dedup po id-u)

Pokreće se tjedno preko GitHub Actions (.github/workflows/reddit-scan.yml).
"""

import csv
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

import requests

from config import (
    SUBREDDITS,
    POSTS_PER_SUBREDDIT,
    COMMENTS_PER_SUBREDDIT,
    TOP_WEEK_PER_SUBREDDIT,
    KEYWORDS,
    CJENKO_RELEVANT_HINTS,
    RECURRING_MIN_WEEKS,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LATEST_CSV = os.path.join(DATA_DIR, "latest.csv")
HISTORY_CSV = os.path.join(DATA_DIR, "history.csv")
SUMMARY_MD = os.path.join(DATA_DIR, "summary.md")

USER_AGENT = "cjenko-idea-scanner/2.0 (besplatni istrazivacki skener, by u/gogiciganovic-del)"
REQUEST_DELAY_SECONDS = 2.5
PAGE_SIZE = 100

FIELDNAMES = [
    "post_id", "scanned_at", "group", "subreddit", "content_type",
    "buckets", "matched_keywords", "cjenko_relevant", "reddit_score",
    "num_comments", "composite_score", "created_utc", "title",
    "snippet", "url",
]

STOPWORDS = set(
    "i the a an of to for in on is are was were be been and or but with "
    "this that it my your you we they he she just like get got know don't "
    "do does did not no yes app apps about so very really je su da li za "
    "na od do kad kada koji koja koje sam smo ste imam ima ovo ono neki "
    "nešto netko tko što kako zašto"
    .split()
)

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})


def _get(url, params):
    while True:
        resp = _session.get(url, params=params, timeout=15)
        if resp.status_code == 429:
            print(f"[upozorenje] rate-limited na {url}, čekam 10s...", file=sys.stderr)
            time.sleep(10)
            continue
        resp.raise_for_status()
        return resp.json()


def fetch_posts(sub_name, listing, limit, extra_params=None):
    """listing: 'new' ili 'top'."""
    posts = []
    after = None
    while len(posts) < limit:
        url = f"https://www.reddit.com/r/{sub_name}/{listing}.json"
        params = {"limit": min(PAGE_SIZE, limit - len(posts))}
        if extra_params:
            params.update(extra_params)
        if after:
            params["after"] = after
        data = _get(url, params)
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


def fetch_comments(sub_name, limit):
    comments = []
    after = None
    while len(comments) < limit:
        url = f"https://www.reddit.com/r/{sub_name}/comments.json"
        params = {"limit": min(PAGE_SIZE, limit - len(comments))}
        if after:
            params["after"] = after
        data = _get(url, params)
        children = data.get("data", {}).get("children", [])
        if not children:
            break
        for child in children:
            comments.append(child["data"])
        after = data.get("data", {}).get("after")
        if not after:
            break
        time.sleep(REQUEST_DELAY_SECONDS)
    return comments


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


def comment_url(sub_name, comment):
    permalink = comment.get("permalink")
    if permalink:
        return f"https://www.reddit.com{permalink}"
    link_permalink = comment.get("link_permalink")
    if link_permalink:
        return f"{link_permalink.rstrip('/')}/{comment.get('id', '')}/"
    link_id = (comment.get("link_id") or "").split("_")[-1]
    return f"https://www.reddit.com/r/{sub_name}/comments/{link_id}/_/{comment.get('id', '')}/"


def load_existing_ids():
    if not os.path.exists(HISTORY_CSV):
        return set()
    with open(HISTORY_CSV, newline="", encoding="utf-8") as f:
        return {row["post_id"] for row in csv.DictReader(f)}


def make_row(group, sub_name, content_type, item_id, title, body, reddit_score,
             num_comments, created_utc, url, hits):
    buckets = sorted({b for b, _ in hits})
    matched_phrases = sorted({p for _, p in hits})
    composite = reddit_score + num_comments + 25 * len(matched_phrases)
    full_text = f"{title}\n{body}"
    return {
        "post_id": item_id,
        "scanned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "group": group,
        "subreddit": sub_name,
        "content_type": content_type,
        "buckets": ";".join(buckets),
        "matched_keywords": ";".join(matched_phrases),
        "cjenko_relevant": "da" if is_cjenko_relevant(full_text) else "ne",
        "reddit_score": reddit_score,
        "num_comments": num_comments,
        "composite_score": composite,
        "created_utc": datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat(timespec="seconds"),
        "title": title.replace("\n", " ").strip(),
        "snippet": body[:300].replace("\n", " ").strip(),
        "url": url,
    }


def scan():
    rows = []

    for group, subs in SUBREDDITS.items():
        for sub_name in subs:
            # 1) najnoviji postovi
            try:
                for post in fetch_posts(sub_name, "new", POSTS_PER_SUBREDDIT):
                    title = post.get("title", "") or ""
                    selftext = post.get("selftext", "") or ""
                    hits = find_matches(f"{title}\n{selftext}")
                    if not hits:
                        continue
                    rows.append(make_row(
                        group, sub_name, "post", post.get("id", ""), title, selftext,
                        post.get("score", 0), post.get("num_comments", 0),
                        post.get("created_utc", 0),
                        f"https://www.reddit.com{post.get('permalink', '')}", hits,
                    ))
                time.sleep(REQUEST_DELAY_SECONDS)
            except Exception as e:
                print(f"[upozorenje] {sub_name} (new): {e}", file=sys.stderr)

            # 2) najpopularniji postovi ovog tjedna (da ne promašimo "viralne" teme)
            try:
                for post in fetch_posts(sub_name, "top", TOP_WEEK_PER_SUBREDDIT, {"t": "week"}):
                    title = post.get("title", "") or ""
                    selftext = post.get("selftext", "") or ""
                    hits = find_matches(f"{title}\n{selftext}")
                    if not hits:
                        continue
                    rows.append(make_row(
                        group, sub_name, "post_top_week", post.get("id", ""), title, selftext,
                        post.get("score", 0), post.get("num_comments", 0),
                        post.get("created_utc", 0),
                        f"https://www.reddit.com{post.get('permalink', '')}", hits,
                    ))
                time.sleep(REQUEST_DELAY_SECONDS)
            except Exception as e:
                print(f"[upozorenje] {sub_name} (top): {e}", file=sys.stderr)

            # 3) najnoviji komentari (tu se krije najviše pravih pritužbi)
            try:
                for comment in fetch_comments(sub_name, COMMENTS_PER_SUBREDDIT):
                    body = comment.get("body", "") or ""
                    hits = find_matches(body)
                    if not hits:
                        continue
                    title = f"[komentar] {body[:80].strip()}"
                    rows.append(make_row(
                        group, sub_name, "comment", comment.get("id", ""), title, body,
                        comment.get("score", 0), 0,
                        comment.get("created_utc", 0),
                        comment_url(sub_name, comment), hits,
                    ))
                time.sleep(REQUEST_DELAY_SECONDS)
            except Exception as e:
                print(f"[upozorenje] {sub_name} (comments): {e}", file=sys.stderr)

    return rows


def write_latest(rows):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LATEST_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in sorted(rows, key=lambda r: r["composite_score"], reverse=True):
            writer.writerow(row)


def append_history(rows):
    seen_ids = load_existing_ids()
    new_rows = [r for r in rows if r["post_id"] not in seen_ids]
    file_exists = os.path.exists(HISTORY_CSV)
    with open(HISTORY_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        for row in new_rows:
            writer.writerow(row)
    return new_rows


def load_history_rows():
    if not os.path.exists(HISTORY_CSV):
        return []
    with open(HISTORY_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def recurring_themes(history_rows):
    """Fraze koje su se pojavile u >= RECURRING_MIN_WEEKS različitih tjedana."""
    phrase_weeks = defaultdict(set)
    for row in history_rows:
        try:
            dt = datetime.fromisoformat(row["scanned_at"])
        except (KeyError, ValueError):
            continue
        week_key = dt.strftime("%G-W%V")
        for phrase in (row.get("matched_keywords") or "").split(";"):
            if phrase:
                phrase_weeks[phrase].add(week_key)
    recurring = [
        (phrase, len(weeks)) for phrase, weeks in phrase_weeks.items()
        if len(weeks) >= RECURRING_MIN_WEEKS
    ]
    recurring.sort(key=lambda x: x[1], reverse=True)
    return recurring


def top_words(rows, n=15):
    counts = Counter()
    for r in rows:
        for word in re.findall(r"[a-zčćžšđ]{4,}", r["title"].lower()):
            if word not in STOPWORDS:
                counts[word] += 1
    return counts.most_common(n)


def write_summary(new_rows, history_rows):
    os.makedirs(DATA_DIR, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [f"# Reddit sažetak — {now}", ""]

    total = len(history_rows) if history_rows else len(new_rows)
    lines.append(f"Novih pogodaka ovaj tjedan: **{len(new_rows)}** (ukupno u povijesti: {total})")
    lines.append("")

    relevant = [r for r in new_rows if r["cjenko_relevant"] == "da"]
    lines.append(f"Od toga potencijalno relevantno za Cjenko Akcije (cijene/kupovina): **{len(relevant)}**")
    lines.append("")

    recurring = recurring_themes(history_rows)
    if recurring:
        lines.append(f"## Ponavljajuće teme (fraza spomenuta u {RECURRING_MIN_WEEKS}+ različitih tjedana — jači signal)")
        for phrase, weeks in recurring[:10]:
            lines.append(f"- \"{phrase}\" — {weeks} tjedana")
        lines.append("")

    if relevant:
        lines.append("## Cjenko-relevantno (top 10 po composite_score)")
        for r in sorted(relevant, key=lambda r: int(r["composite_score"]), reverse=True)[:10]:
            lines.append(f"- [{r['title']}]({r['url']}) — r/{r['subreddit']} ({r['content_type']}), {r['buckets']}, score {r['composite_score']}")
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
        lines.append(f"## {label} (top 8 po composite_score)")
        for r in sorted(bucket_rows, key=lambda r: int(r["composite_score"]), reverse=True)[:8]:
            lines.append(f"- [{r['title']}]({r['url']}) — r/{r['subreddit']} ({r['content_type']}), score {r['composite_score']}")
        lines.append("")

    words = top_words(new_rows)
    if words:
        lines.append("## Najčešće riječi u naslovima/komentarima pogodaka (grubi signal tema)")
        lines.append(", ".join(f"{w} ({c})" for w, c in words))
        lines.append("")

    with open(SUMMARY_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    rows = scan()
    write_latest(rows)
    new_rows = append_history(rows)
    history_rows = load_history_rows()
    write_summary(new_rows, history_rows)
    print(f"Gotovo: {len(rows)} ukupno pogodaka, {len(new_rows)} novih.")


if __name__ == "__main__":
    main()
