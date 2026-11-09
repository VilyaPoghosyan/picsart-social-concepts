#!/usr/bin/env python3
"""Weekly portfolio 1-pager (portfolio/index.html + portfolio/portfolio.png): every brand's purpose and concept,
the week's numbers with the change on the week before, and the overall totals since Oct 15, in six classes from
reach to conversion, with one chart of total reach over the whole run.

Tigran's brief (2026-11-06): one short page as a portfolio, each brand with its purpose and concept, current numbers,
updated and shared every week: overall numbers, week-over-week change, impressions and conversions in the product.
Vilya (2026-11-06): overall first, then the week, as separate sections (Tigran's order), one chart of overall reach (impressions), refreshed every Monday at 11:30.

Numbers come from two places:
  reach, audience, engagement   the refreshed brand report (summary/<brand>/index.html via build_exec.brand_numbers).
                                Views are totals, so a week's views = today's total minus the total 7 days earlier.
                                Past days are read from this repo's git history (last report commit on or before that day).
  visits, used AI, converted    Argus only, written by the Monday task to
                                ~/vilya-ai/context/reports/conversion/weekly/<report day>.json (shape: see the 2026-11-06 file)

Run (after bin/brand_summary_weekly.py and the conversion file): python3 onepagers/build_portfolio.py --png [--publish]
Reads local files and git history. --publish commits only the portfolio files, pushes to GitHub Pages
(https://vilyapoghosyan.github.io/picsart-social-concepts/portfolio/) and checks the live page shows today's update.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import build_exec as be

HERE = Path(__file__).resolve().parent
OUT = HERE / "portfolio"
KIT = Path.home() / ".claude/skills/picsart-product-design/assets"
CONV = Path.home() / "vilya-ai/context/reports/conversion/weekly"
START = date(2026, 10, 15)  # official start of the run (Vilya, 2026-11-06); earlier posts are left out of every number
CUT = datetime(2026, 10, 14, 20, 0, tzinfo=timezone.utc)  # Oct 15 00:00 Yerevan
E = html.escape

# Why each brand exists, in one line. The concept line comes from build_exec.BRANDS.
PURPOSE = {
    "reelo": "Mass reach: show what Picsart video AI makes for families and pet lovers.",
    "microdramas": "A loyal audience that follows a story, and taps through to make its own.",
    "dwell": "Home and interior lovers who save ideas, on Instagram, TikTok and Pinterest.",
    "faceless": "Creators who want to earn money with AI content made in Picsart.",
    "listed": "Online sellers who need better product photos, fixed in Picsart.",
}

# The six classes, top of the funnel first. (key, label, meaning for the week, meaning overall)
CLASSES = [
    ("views", "Reach", "views on Instagram and TikTok", "views on Instagram and TikTok"),
    ("fol", "Audience", "new followers", "followers today"),
    ("eng", "Engagement", "saves and shares", "saves and shares"),
    ("visits", "Visits", "people who tapped through to Picsart", "people who tapped through to Picsart"),
    ("used_ai", "Used AI", "visitors who used a Picsart AI tool", "visitors who used a Picsart AI tool"),
    ("conv", "Converted", "new sign-ups and purchases", "new sign-ups and purchases"),
]


def eng_synced(root: Path, slug: str) -> bool:
    page = (root / f"summary/{slug}/index.html").read_text()
    return 'not synced</div><div class="k">Saves' not in page


def views_synced(root: Path, slug: str) -> bool:
    """False when the platform has not returned views for every post yet ("Posts with views 12 of 32")."""
    page = (root / f"summary/{slug}/index.html").read_text()
    return all(a == b for a, b in re.findall(r'<div class="n">(\d+) of (\d+)</div><div class="k">Posts with views', page))


def posted(p: dict):
    try:
        return datetime.fromisoformat(str(p.get("publishedAt") or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def before_start(root: Path, slug: str) -> dict:
    """Views, saves + shares and post count of the brand's posts published before START, read the way the report reads
    them (live platform numbers where the report has them, else the publishing rail), so they can be taken off its totals."""
    lv = root / "live_views.json"
    live = json.loads(lv.read_text()) if lv.exists() else {}
    out = dict(views=0, eng=0, posts=0, pins=0, undated=0)
    if slug == "reelo":  # brand_numbers already drops posts before Oct 3
        feed = json.loads((root / "reelo/feed.json").read_text())
        posts = [dict(p, platform=pl) for pl in ("instagram", "tiktok") for p in (feed.get(pl) or {}).get("posts", [])]
        posts = [p for p in posts if posted(p) and be.SINCE <= posted(p)]
    else:
        posts = list(json.loads((root / f"{slug}/stats.json").read_text()).values())
    for p in posts:
        if not isinstance(p, dict):
            continue
        if not posted(p):  # the rail has not synced this post yet, so its date is unknown
            out["undated"] += 1
            continue
        if posted(p) >= CUT:
            continue
        views, saves, shares = p.get("views") or 0, p.get("saves") or 0, p.get("shares") or 0
        url = p.get("url", "")
        if "/reel/" in url and url.split("/reel/")[1].strip("/") in live.get("instagram", {}):
            views = live["instagram"][url.split("/reel/")[1].strip("/")]
        tid = re.search(r"/video/(\d+)", url)
        if tid and tid.group(1) in live.get("tiktok", {}):
            t = live["tiktok"][tid.group(1)]
            views, saves, shares = t.get("views") or 0, t.get("saves") or 0, t.get("shares") or 0
        out["views"] += views
        out["eng"] += saves + shares
        out["posts"] += 1
    pins = root / "dwell/pinterest.json"
    if slug == "dwell" and pins.exists():
        out["pins"] = sum(p.get("impressions") or 0 for p in json.loads(pins.read_text()).get("pins", [])
                          if posted(p) and posted(p) < CUT)
    return out


def snapshot(root: Path) -> dict:
    be.HERE = root
    out = {}
    try:
        for b in be.BRANDS:
            n, old = be.brand_numbers(b["slug"]), before_start(root, b["slug"])
            views = max(n["views"] - old["views"], 0)
            out[b["slug"]] = dict(views=views if views_synced(root, b["slug"]) else None, raw_views=views, fol=n["fol"],
                                  eng=max(n["eng"] - old["eng"], 0) if eng_synced(root, b["slug"]) else None,
                                  posts=None if old["undated"] else max(n["published"] - old["posts"], 0), pins=max(be.num(n["pins"]) - old["pins"], 0))
    finally:
        be.HERE = HERE
    return out


def report_commits() -> list[tuple[date, str]]:
    """The last report commit of every day, oldest first."""
    log = subprocess.run(["git", "-C", str(HERE), "log", "--format=%h %ad", "--date=format:%Y-%m-%d", "--", "summary/index.html"],
                         capture_output=True, text=True, check=True).stdout.split("\n")
    days: dict[date, str] = {}
    for line in log:
        if line.strip():
            sha, d = line.split()
            days.setdefault(date.fromisoformat(d), sha)  # log is newest first, so the first seen is the day's last
    return sorted(days.items())


def snapshot_at(sha: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        tar = subprocess.run(["git", "-C", str(HERE), "archive", sha, "summary", "reelo/feed.json",
                              *(f"{s}/stats.json" for s in ("microdramas", "dwell", "faceless", "listed")), "dwell/pinterest.json"], capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", tmp], input=tar.stdout, check=True)
        return snapshot(Path(tmp))


def snapshot_on(day: date, commits: list[tuple[date, str]]) -> dict:
    """The brand numbers as the last report commit on or before `day` left them."""
    before = [sha for d, sha in commits if d <= day]
    return snapshot_at(before[-1]) if before else {}


def diff(a: dict, b: dict, key: str):
    if a.get(key) is None or b.get(key) is None:
        return None
    return max(a[key] - b[key], 0)  # platforms revise counts down a little; a week never adds negative views


def fmt(n, k: str = "") -> str:
    """A number not known yet says why, never 0."""
    if n is None:
        return "not synced" if k in ("views", "eng") else "pending"
    return f"{max(n, 0):,}"


def short(n: int) -> str:
    return f"{n / 1e6:.1f}M" if n >= 1e6 else (f"{n / 1000:.0f}K" if n >= 10000 else (f"{n / 1000:.1f}K" if n >= 1000 else f"{n:,}"))


def add(*xs):
    return None if any(x is None for x in xs) else sum(xs)


def change(now, before) -> str:
    """Week-over-week mark: a coloured arrow and percent, never a fill."""
    if now is None or before is None:
        return '<span class="wow">no compare</span>'
    if before == 0:
        return '<span class="wow up">new</span>' if now > 0 else '<span class="wow">no change</span>'
    pct = round(100 * (now - before) / before)
    if pct == 0:
        return '<span class="wow">no change</span>'
    cls, arrow = ("up", "&uarr;") if pct > 0 else ("down", "&darr;")
    if pct >= 1000:  # "142x" reads better than "14067%"
        return f'<span class="wow {cls}">{arrow} {now / before:.0f}x</span>'
    return f'<span class="wow {cls}">{arrow} {abs(pct)}%</span>'


def nice(d: date) -> str:
    return f"{d:%a} {d.day} {d:%b}"


def overall_chart(points: list[tuple[date, int]]) -> str:
    """Total reach since Oct 15, one point per report day. The plot is SVG, the labels are HTML, so text never scales."""
    points = [(START, 0)] + points
    span = (points[-1][0] - START).days or 1
    top = max(v for _, v in points)
    step = 10 ** (len(str(top)) - 1)
    ymax = -(-top // step) * step  # round up to a clean axis top
    xy = [(100 * (d - START).days / span, 100 - 100 * v / ymax) for d, v in points]
    line = " ".join(f"{x:.2f},{y:.2f}" for x, y in xy[1:])
    area = f"{xy[1][0]:.2f},100 {line} 100,100"
    gap = f'<line x1="0" y1="100" x2="{xy[1][0]:.2f}" y2="{xy[1][1]:.2f}" class="gap"/>'  # launch to first reading: no data
    grid = "".join(f'<span class="gl" style="top:{100 - 100 * g / 4:.2f}%"><em>{short(int(ymax * g / 4))}</em></span>' for g in range(1, 5))
    dots = "".join(f'<i class="pt" style="left:{x:.2f}%;top:{y:.2f}%" title="{E(nice(d))}: {v:,} views since Oct 15"></i>'
                   for (x, y), (d, v) in zip(xy[1:], points[1:]))
    last_x, last_y = xy[-1]
    label = f'<b class="last" style="left:{last_x:.2f}%;top:{last_y:.2f}%">{short(points[-1][1])}</b>'
    ticks, prev = [], None
    for d, _ in reversed(points):  # newest first, so the latest day always keeps its label
        if prev is None or (prev - d).days >= 5:
            ticks.append(d)
            prev = d
    xl = "".join(f'<span style="left:{100 * (d - START).days / span:.2f}%">{d.day} {d:%b}</span>' for d in reversed(ticks))
    return (f'<div class="lc"><div class="plot">{grid}'
            f'<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'
            f'<polygon points="{area}" class="area"/>{gap}<polyline points="{line}" class="line"/></svg>{dots}{label}</div>'
            f'<div class="xl">{xl}</div></div>')


def auto_notes(week: dict, prev: dict, names: dict, tw: dict, ta: dict) -> list[str]:
    """Plain-word lines computed from the numbers, so the Monday run needs nobody to write them."""
    out = []
    if tw["views"]:
        top = max(week, key=lambda s: week[s]["views"] or 0)
        share = round(100 * (week[top]["views"] or 0) / tw["views"])
        out.append(f"{names[top]} brought {short(week[top]['views'] or 0)} of this week's {short(tw['views'])} views ({share}%).")
    moves = [(s, (week[s]["views"] - prev[s]["views"]) / prev[s]["views"]) for s in week
             if week[s]["views"] is not None and (prev[s]["views"] or 0) >= 1000]
    if moves:
        s, m = max(moves, key=lambda x: abs(x[1]))
        out.append(f"Biggest reach change: {names[s]}, {'up' if m > 0 else 'down'} {abs(round(100 * m))}% on the week before.")
    if tw["visits"]:
        lead = max(week, key=lambda s: week[s]["visits"] or 0)
        n, ai = tw["visits"], week[lead]["used_ai"] or 0
        who = (f"Only 1 real visitor reached Picsart this week, from {names[lead]}" if n == 1 else
               f"{names[lead]} sent {week[lead]['visits']} of the {n} real visitors to Picsart this week")
        out.append(f"{who}; {'nobody' if not ai else ai} used a Picsart AI tool.")
    else:
        out.append("No brand sent a real visitor to Picsart this week.")
    if ta["conv"] == 0:
        out.append("No sign-ups or purchases from any brand yet.")
    elif tw["conv"]:
        out.append(f"{tw['conv']} new sign-ups and purchases this week, {ta['conv']} since Oct 15.")
    return out


def stat_cards(vals: dict, meanings: dict, sub: dict) -> str:
    return "".join(
        f'<div class="stat"><span class="cls">{E(label)}</span><b>{fmt(vals[k])}</b>'
        f'<span>{E(meanings[k])}</span><small>{sub[k]}</small></div>'
        for k, label, *_ in CLASSES)


def build(day: date) -> str:
    commits = report_commits()
    now = snapshot(HERE)
    wk1, wk2 = snapshot_on(day - timedelta(days=7), commits), snapshot_on(day - timedelta(days=14), commits)
    conv = json.loads((CONV / f"{day.isoformat()}.json").read_text())
    start, end = (date.fromisoformat(conv["week"][k]) for k in ("start", "end"))

    week, prev, alltime = {}, {}, {}
    for b in be.BRANDS:
        s, c = b["slug"], conv["brands"][b["slug"]]
        week[s] = {k: diff(now[s], wk1.get(s, {}), k) for k in ("views", "fol", "eng")}
        prev[s] = {k: diff(wk1.get(s, {}), wk2.get(s, {}), k) for k in ("views", "fol", "eng")}
        alltime[s] = {k: now[s][k] for k in ("views", "fol", "eng")}
        for k, src in (("visits", "real"), ("used_ai", "used_ai")):  # real taps only: team link tests stay out
            week[s][k], prev[s][k], alltime[s][k] = c["this"][src], c["prev"][src], c["all"][src]
        for target, p in ((week, "this"), (prev, "prev"), (alltime, "all")):
            target[s]["conv"] = add(c[p]["signups"], c[p]["purchases"])

    def total(table: dict, k: str):
        vals = [table[s][k] for s in table]
        if k in ("views", "eng"):  # a brand that has not synced is left out, and says so in its row
            return sum(v for v in vals if v is not None)
        return add(*vals)

    tw = {k: total(week, k) for k, *_ in CLASSES}
    tp = {k: total(prev, k) for k, *_ in CLASSES}
    ta = {k: total(alltime, k) for k, *_ in CLASSES}

    week_stats = stat_cards(tw, {k: m for k, _, m, _ in CLASSES}, {k: change(tw[k], tp[k]) + " vs the week before" for k, *_ in CLASSES})
    all_stats = stat_cards(ta, {k: m for k, _, _, m in CLASSES},
                           {k: f'+{fmt(tw[k])} this week' if tw[k] else "nothing new this week" for k, *_ in CLASSES})

    heads = "".join(f'<th scope="col">{E(label)}</th>' for _, label, *_ in CLASSES)
    week_rows, all_rows = [], []
    for b in be.BRANDS:
        s = b["slug"]
        week_rows.append(f'<tr><th scope="row"><span class="bn">{E(b["name"])}</span></th>' + "".join(
            f'<td data-label="{E(label)}"><b class="n">{fmt(week[s][k], k)}</b>{change(week[s][k], prev[s][k])}</td>'
            for k, label, *_ in CLASSES) + "</tr>")
        pins = f' Plus {now[s]["pins"]:,} Pinterest impressions.' if now[s]["pins"] else ""
        views_all = fmt(alltime[s]["views"], "views") if alltime[s]["views"] is not None else f'{now[s]["raw_views"]:,} (partly synced)'
        all_rows.append(
            f'<tr><th scope="row"><span class="bn">{E(b["name"])}</span><span class="pp">{E(PURPOSE[s])}</span>'
            f'<span class="cc">{E(b["concept"])}{E(pins)} {f'{now[s]["posts"]:,} posts since Oct 15.' if now[s]["posts"] is not None else ""}</span></th>'
            f'<td data-label="Reach"><b class="n">{views_all}</b></td>' + "".join(
                f'<td data-label="{E(label)}"><b class="n">{fmt(alltime[s][k], k)}</b></td>' for k, label, *_ in CLASSES[1:]) + "</tr>")

    history = []
    for d, sha in commits:
        if d < day:
            history.append((d, sum(v["views"] or 0 for v in snapshot_at(sha).values())))  # same rule as the cards
    history.append((day, sum(v["views"] or 0 for v in now.values())))

    names = {b["slug"]: b["name"] for b in be.BRANDS}
    notes = "".join(f"<li>{E(n)}</li>" for n in auto_notes(week, prev, names, tw, ta) + conv.get("notes", []))
    css = (OUT / "page.css").read_text()
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Social Brands Portfolio</title>
<meta name="description" content="Five social brands on one page: purpose, concept, the week's numbers with the change on the week before, and the totals since Oct 15.">
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#121212">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Mulish:wght@400;500;600;700&display=swap">
<link rel="preload" href="fonts/Acorn-Regular.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="fonts/Gilroy-SemiBold.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="picsart.css">
<style>{css}</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">
  <symbol id="i-sun" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/></symbol>
  <symbol id="i-moon" viewBox="0 0 24 24"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></symbol>
</svg>
<header class="top">
  <div class="top-in">
    <a class="brand" href="#main" aria-label="Social portfolio, back to top"><b>Social portfolio</b></a>
    <span class="chname">/ {nice(start)} to {nice(end)}</span>
    <div class="tools">
      <button type="button" class="ibtn theme-btn" id="theme-btn" aria-label="Switch light or dark theme">
        <svg class="icon sun" aria-hidden="true"><use href="#i-sun"/></svg><svg class="icon moon" aria-hidden="true"><use href="#i-moon"/></svg>
      </button>
    </div>
  </div>
</header>
<main class="wrap" id="main">
  <div class="page-head">
    <h1>Five brands, one <span class="g">week.</span></h1>
    <p class="dek">AI-made social brands that grow an audience and send it to Picsart. First everything since Oct 15, then the week.</p>
  </div>

  <section class="sec" aria-labelledby="o-h">
    <div class="sec-head"><h2 id="o-h">Overall</h2><span class="pill">since Thu 15 Oct</span></div>
    <div class="stats">{all_stats}</div>
    <div class="panel chart">
      <div class="chart-head"><h3>Total reach since Oct 15</h3><span class="legend">views on Instagram and TikTok, all brands. Dashed: launch to the first reading</span></div>
      {overall_chart(history)}
    </div>
    <div class="panel tbl">
      <table class="pf pf-all">
        <thead><tr><th scope="col">Brand<small>purpose, concept</small></th>{heads}</tr></thead>
        <tbody>{"".join(all_rows)}</tbody>
      </table>
    </div>
  </section>

  <section class="sec" aria-labelledby="w-h">
    <div class="sec-head"><h2 id="w-h">This week</h2><span class="pill">{nice(start)} to {nice(end)}</span></div>
    <div class="stats">{week_stats}</div>
    <div class="panel tbl">
      <table class="pf pf-week">
        <thead><tr><th scope="col">Brand</th>{heads}</tr></thead>
        <tbody>{"".join(week_rows)}</tbody>
      </table>
    </div>
  </section>

  {f'<section class="panel moved" aria-labelledby="m-h"><h2 id="m-h">What moved</h2><ul>{notes}</ul></section>' if notes else ""}
  <footer class="foot">
    <p>Updated {datetime.now():%a %-d %b %Y, %H:%M} Yerevan. Refreshed every Monday at 11:30.</p>
  </footer>
</main>
<script>
document.getElementById("theme-btn").addEventListener("click", () => {{
  const r = document.documentElement; r.dataset.theme = r.dataset.theme === "light" ? "dark" : "light";
}});
</script>
</body>
</html>
"""


def png(page: Path) -> Path:
    """Full-page screenshot for Slack, dark theme, 1280 wide."""
    shot = page.with_name("portfolio.png")
    code = (
        "import sys, http.server, threading, functools, glob, os\n"
        "from playwright.sync_api import sync_playwright\n"
        "d=sys.argv[1]; h=functools.partial(http.server.SimpleHTTPRequestHandler, directory=d)\n"
        "s=http.server.ThreadingHTTPServer(('127.0.0.1',0),h); threading.Thread(target=s.serve_forever,daemon=True).start()\n"
        "ex=sorted(glob.glob(os.path.expanduser('~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-*/chrome-headless-shell')))\n"
        "with sync_playwright() as p:\n"
        "  b=p.chromium.launch(executable_path=ex[-1] if ex else None)\n"
        "  pg=b.new_page(viewport={'width':1280,'height':900}, device_scale_factor=2, color_scheme='dark')\n"
        "  pg.goto(f'http://127.0.0.1:{s.server_address[1]}/index.html'); pg.wait_for_load_state('networkidle')\n"
        "  pg.evaluate('document.fonts.ready'); pg.add_style_tag(content='.top{position:static}')\n"
        "  pg.screenshot(path=sys.argv[2], full_page=True); b.close()\n"
    )
    subprocess.run(["uv", "run", "--quiet", "--with", "playwright", "python", "-c", code, str(page.parent), str(shot)],
                   check=True, stderr=subprocess.DEVNULL)
    return shot


LIVE = "https://vilyapoghosyan.github.io/picsart-social-concepts/portfolio/"
FILES = ["build_portfolio.py", "portfolio/index.html", "portfolio/page.css", "portfolio/picsart.css", "portfolio/fonts",
         "portfolio/portfolio.png"]


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(HERE), *args], capture_output=True, text=True, check=True).stdout


def publish(day: date) -> None:
    """Commit only the portfolio's files, push, then wait for GitHub Pages to show this build."""
    git("add", "--", *FILES)
    if not git("diff", "--cached", "--name-only", "--", *FILES).strip():
        print("publish: nothing changed")
        return
    git("commit", "-m", f"chore(portfolio): weekly refresh {day.isoformat()}", "--", *FILES)
    git("push", "origin", "HEAD")
    stamp = re.search(r"Updated [^<]*Yerevan", (OUT / "index.html").read_text()).group(0)  # this build's exact time
    for _ in range(24):  # Pages usually updates within a few minutes
        time.sleep(15)
        try:
            page = urllib.request.urlopen(f"{LIVE}?v={time.time():.0f}", timeout=20).read().decode()
        except OSError:
            continue
        if stamp in page:
            print(f"publish: pushed, live {LIVE}")
            return
    print(f"publish: pushed, but the live page does not show '{stamp}' yet: {LIVE}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--day", type=date.fromisoformat, default=date.today(), help="report day (default today)")
    ap.add_argument("--png", action="store_true", help="also render portfolio.png for Slack")
    ap.add_argument("--publish", action="store_true", help="commit the portfolio files and push them to GitHub Pages")
    a = ap.parse_args()
    if not (CONV / f"{a.day.isoformat()}.json").exists():
        sys.exit(f"Missing {CONV / (a.day.isoformat() + '.json')}: write this week's Argus numbers first.")
    (OUT / "fonts").mkdir(parents=True, exist_ok=True)
    shutil.copy(KIT / "picsart.css", OUT / "picsart.css")
    for f in (KIT / "fonts").glob("*.woff2"):
        shutil.copy(f, OUT / "fonts" / f.name)
    page = OUT / "index.html"
    page.write_text(build(a.day))
    print(page)
    if a.png:
        print(png(page))
    if a.publish:
        publish(a.day)


if __name__ == "__main__":
    main()
