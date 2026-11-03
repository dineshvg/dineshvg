#!/usr/bin/env python3
"""Fetches public GitHub stats for the dashboard. Usage: fetch_stats.py <user> > stats.json

Runs in GitHub Actions with GH_TOKEN=${{ secrets.GITHUB_TOKEN }}. Only public data is read.
"""
import datetime
import json
import os
import sys
import urllib.request

USER = sys.argv[1]
TOKEN = os.environ.get("GH_TOKEN", "")
API = "https://api.github.com"


def call(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "profile-stats")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


user = call(f"{API}/users/{USER}")

repos, page = [], 1
while True:
    batch = call(f"{API}/users/{USER}/repos?type=owner&per_page=100&page={page}")
    repos += batch
    if len(batch) < 100:
        break
    page += 1
own = [r for r in repos if not r["fork"] and not r.get("archived")]

contributions = None
try:
    q = {"query": "query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{totalContributions}}}}",
         "variables": {"l": USER}}
    contributions = call(f"{API}/graphql", q)["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
except Exception as e:  # GraphQL needs a token; dashboard falls back to "—"
    print(f"contributions unavailable: {e}", file=sys.stderr)

top = sorted(own, key=lambda r: (-r["stargazers_count"], r["name"].lower()))
top = [r for r in top if r["name"].lower() != USER.lower()][:5]

json.dump({
    "public_repos": user["public_repos"],
    "followers": user["followers"],
    "stars": sum(r["stargazers_count"] for r in own),
    "contributions": contributions,
    "top_repos": [{"name": r["name"], "stars": r["stargazers_count"]} for r in top],
    "updated": datetime.date.today().isoformat(),
}, sys.stdout, indent=2)
