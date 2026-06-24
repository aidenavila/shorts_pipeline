"""
reddit.py — pull real story posts from a subreddit using PRAW.

Credentials come from environment variables (never hard-code them):
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT

Create an app at https://www.reddit.com/prefs/apps  (type: "script").
A read-only instance (client id + secret only) is enough to read public
subreddits — no username/password needed.

fetch_story() returns the first qualifying post that hasn't been used before,
recording its id in a small JSON file so repeat runs pick something new.
"""
import os
import json

import praw


def _client():
    cid = os.environ.get("REDDIT_CLIENT_ID")
    secret = os.environ.get("REDDIT_CLIENT_SECRET")
    ua = os.environ.get("REDDIT_USER_AGENT", "shorts-pipeline/0.1")
    if not cid or not secret:
        raise RuntimeError(
            "Missing Reddit credentials. Set REDDIT_CLIENT_ID and "
            "REDDIT_CLIENT_SECRET (and optionally REDDIT_USER_AGENT). "
            "Create a 'script' app at https://www.reddit.com/prefs/apps"
        )
    reddit = praw.Reddit(client_id=cid, client_secret=secret, user_agent=ua)
    reddit.read_only = True
    return reddit


def _load_seen(path):
    if not path or not os.path.exists(path):
        return set()
    try:
        with open(path) as f:
            return set(json.load(f))
    except (json.JSONDecodeError, OSError):
        return set()


def _save_seen(path, seen):
    if not path:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(sorted(seen), f)


def fetch_story(subreddit, *, sort="top", time_filter="week",
                min_chars=200, max_chars=1100, skip_nsfw=True,
                scan_limit=80, seen_path=None):
    """
    Return the first unused self-post whose combined title+body length is within
    [min_chars, max_chars], as a dict:
        {"id", "title", "text", "url", "subreddit"}
    or None if nothing qualifies. Picks affect length budget: ~1100 chars keeps
    a Short under ~60s; raise max_chars for long-form videos.
    """
    reddit = _client()
    seen = _load_seen(seen_path)
    sub = reddit.subreddit(subreddit)

    if sort == "hot":
        listing = sub.hot(limit=scan_limit)
    elif sort == "new":
        listing = sub.new(limit=scan_limit)
    else:
        listing = sub.top(time_filter=time_filter, limit=scan_limit)

    for post in listing:
        if post.id in seen:
            continue
        if post.stickied or not post.is_self:   # text posts only
            continue
        if skip_nsfw and post.over_18:
            continue
        body = (post.selftext or "").strip()
        if not body:
            continue
        text = f"{post.title}. {body}"
        if not (min_chars <= len(text) <= max_chars):
            continue

        seen.add(post.id)
        _save_seen(seen_path, seen)
        return {
            "id": post.id,
            "title": post.title,
            "text": text,
            "url": f"https://reddit.com{post.permalink}",
            "subreddit": str(post.subreddit),
        }
    return None
