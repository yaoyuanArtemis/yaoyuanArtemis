#!/usr/bin/env python3
"""Fetch last 30 days GitHub contribution stats and update README."""

import json, os, re, sys, urllib.request
from datetime import datetime, timedelta, timezone

USER = "yaoyuanArtemis"
TOKEN = os.environ["GH_TOKEN"]
README = os.path.join(os.environ["GITHUB_WORKSPACE"], "README.md")

query = """
query($user: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $user) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
  }
}
"""

today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
start = today - timedelta(days=30)

payload = json.dumps({
    "query": query,
    "variables": {
        "user": USER,
        "from": start.isoformat(),
        "to": today.isoformat()
    }
}).encode()

req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "commit-stats-action"
    }
)

resp = json.loads(urllib.request.urlopen(req).read())
cc = resp["data"]["user"]["contributionsCollection"]

total_commits = cc["totalCommitContributions"]
total_prs = cc["totalPullRequestContributions"]
total_issues = cc["totalIssueContributions"]

# Build daily activity heatmap data
daily = {}
for week in cc["contributionCalendar"]["weeks"]:
    for day in week["contributionDays"]:
        daily[day["date"]] = day["contributionCount"]

# Last 30 days
dates = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30)]

# Simple ASCII-ish mini bar chart (using block chars)
max_count = max(daily.get(d, 0) for d in dates) or 1
bar_chars = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

def bar(val):
    idx = min(round(val / max_count * 8), 8) if max_count else 0
    return bar_chars[idx]

bars = "".join(bar(daily.get(d, 0)) for d in dates)

# Find best streak in last 30 days
streak = best = 0
for d in dates:
    if daily.get(d, 0) > 0:
        streak += 1
        best = max(best, streak)
    else:
        streak = 0

stats_block = f"""<p align="center">
  <sub><b>Last 30 Days</b> &nbsp;|&nbsp;
  🟢 {total_commits} commits &nbsp;|&nbsp;
  🔀 {total_prs} PRs &nbsp;|&nbsp;
  📝 {total_issues} issues &nbsp;|&nbsp;
  🔥 {best}d best streak
  </sub>
  <br/>
  <sub>{bars}</sub>
  <br/>
  <sub><i>updated {today.strftime('%Y-%m-%d')}</i></sub>
</p>"""

# Read README and replace between markers
with open(README) as f:
    content = f.read()

pattern = r"(<!-- commit-stats-start -->).*?(<!-- commit-stats-end -->)"
replacement = f"\\1\n{stats_block}\n\\2"

if re.search(pattern, content, re.DOTALL):
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
else:
    print("Markers not found in README. Check README for <!-- commit-stats-start -->/<!-- commit-stats-end -->.")
    sys.exit(1)

with open(README, "w") as f:
    f.write(new_content)

print(f"Updated README: {total_commits} commits, {total_prs} PRs, {total_issues} issues, {best}d streak")
