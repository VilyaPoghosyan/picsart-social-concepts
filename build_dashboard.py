#!/usr/bin/env python3
"""Performance dashboard: one screen that shows how every social account performs, for people with no context.

Davit (2026-11-23): "do we have a dashboard where performance is easy to see?". The portfolio is a report (concepts,
prose, tables); this page is numbers and charts only. It reads exactly the same data as the portfolio
(build_portfolio's snapshots, the Argus conversion file and the funnel file of the report day), so the two never
disagree, and it is rebuilt with the portfolio every Monday.

  key numbers     this week vs the week before (views, new followers, people on Picsart, used AI, sign-ups, paid)
  views per week  weekly views per account from the report history (last report on or before each Monday)
  visitors        people from the Instagram app on Picsart per week (Argus, one definition for every bar)
  funnel          views down to paid (funnel.py)
  leaderboard     every account, highest reach first, with its weekly views line

Run: python3 onepagers/build_dashboard.py --day YYYY-MM-DD [--publish]
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path

import build_portfolio as bp
import funnel

E = html.escape
HERE = Path(__file__).resolve().parent
OUT = HERE / "dashboard"
KIT = Path.home() / ".claude/skills/picsart-product-design/assets"
COLORS = ["#FF47FF", "#9B4DF7", "#3D8BFF", "#2BB3C0", "#3FD68F", "#F5B83D", "#FF6B5E", "#B3B3B3"]
START = date(2026, 10, 15)


def k(n) -> str:
    """14,563,267 -> 14.6M; small numbers stay exact."""
    if n is None:
        return "pending"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 10_000:
        return f"{n / 1_000:.0f}K"
    return f"{n:,}"


def weekly_views(day: date, commits) -> tuple[list[date], dict]:
    """Mondays from the first full week to `day`, and per account the views gained in each week."""
    mondays, m = [], day
    while m - timedelta(days=7) >= START:
        mondays.insert(0, m)
        m -= timedelta(days=7)
    snaps = {d: bp.snapshot_on(d, commits) for d in [mondays[0] - timedelta(days=7)] + mondays}
    snaps[day] = bp.snapshot(HERE)  # the report day itself is read live, not from history
    per = {}
    for b in bp.accounts():
        s, row = b["slug"], []
        for d in mondays:
            a, z = snaps[d].get(s, {}), snaps[d - timedelta(days=7)].get(s, {})
            va, vz = a.get("views") if a.get("views") is not None else a.get("raw_views"), z.get("views") if z.get("views") is not None else z.get("raw_views")
            row.append(max((va or 0) - (vz or 0), 0))
        per[s] = row
    return mondays, per


def stacked_bars(mondays: list[date], per: dict, names: dict) -> str:
    """Weekly views, stacked by account; the five biggest accounts get their own colour, the rest is 'Others'."""
    totals = {s: sum(v) for s, v in per.items()}
    top = sorted(totals, key=totals.get, reverse=True)[:5]
    series = [(names[s], per[s]) for s in top] + [("Others", [sum(per[s][i] for s in per if s not in top) for i in range(len(mondays))])]
    peak = max(sum(v[i] for _, v in series) for i in range(len(mondays))) or 1
    cols = []
    for i, d in enumerate(mondays):
        tot = sum(v[i] for _, v in series)
        segs = "".join(f'<i style="height:{100 * v[i] / peak:.2f}%;background:{COLORS[j]}" title="{E(n)}: {v[i]:,}"></i>'
                       for j, (n, v) in enumerate(series) if v[i])
        wk = f"{(d - timedelta(days=7)):%-d %b}"
        cols.append(f'<div class="col"><span class="tot">{k(tot)}</span><div class="stack">{segs}</div><span class="x">wk of {wk}</span></div>')
    legend = "".join(f'<span><i style="background:{COLORS[j]}"></i>{E(n)}</span>' for j, (n, _) in enumerate(series))
    return f'<div class="bars">{"".join(cols)}</div><div class="lg">{legend}</div>'


def visitor_bars(rows: list[tuple[str, int | None]]) -> str:
    peak = max([v for _, v in rows if v] or [1])
    return '<div class="hb">' + "".join(
        f'<div class="hr"><span>{E(l)}</span><div class="tr"><i style="width:{100 * (v or 0) / peak:.1f}%"></i></div><b>{"pending" if v is None else f"{v:,}"}</b></div>'
        for l, v in rows) + "</div>"


def spark(vals: list[int]) -> str:
    if not vals or max(vals) == 0:
        return '<svg class="sp" viewBox="0 0 100 24" aria-hidden="true"><line x1="0" y1="22" x2="100" y2="22"/></svg>'
    top, n = max(vals), len(vals)
    pts = " ".join(f"{100 * i / max(n - 1, 1):.1f},{22 - 20 * v / top:.1f}" for i, v in enumerate(vals))
    return f'<svg class="sp" viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden="true"><polyline points="{pts}"/></svg>'


def tile(label: str, total, this, before, sub: str) -> str:
    """Overall number big; this week's addition and its change on the week before underneath."""
    big = k(total) if label == "Views" else ("pending" if total is None else f"{total:,}")  # only views are shortened (22.0M)
    return (f'<div class="kpi"><span class="kl">{E(label)}</span><b>{big}</b>'
            f'<span class="kc">+{k(this)} this week {bp.change(this, before)}</span><small class="ks">{E(sub)}</small></div>')


def build(day: date) -> str:
    commits = bp.report_commits()
    now = bp.snapshot(HERE)
    wk1, wk2 = bp.snapshot_on(day - timedelta(days=7), commits), bp.snapshot_on(day - timedelta(days=14), commits)
    conv = json.loads((bp.CONV / f"{day.isoformat()}.json").read_text())
    fpath = bp.FUNNEL / f"{day.isoformat()}.json"
    fdata = json.loads(fpath.read_text()) if fpath.exists() else None  # no funnel file this week: the page leaves the funnel out
    start, end = (date.fromisoformat(conv["week"][x]) for x in ("start", "end"))
    names = {b["slug"]: b["name"] for b in bp.accounts()}

    week, prev, alltime = {}, {}, {}
    for b in bp.accounts():
        s = b["slug"]
        c = conv["brands"].get(s) or {}
        g = lambda p, f: (c.get(p) or {}).get(f)  # noqa: E731
        week[s] = {x: bp.diff(now[s], wk1.get(s, {}), x) for x in ("views", "fol", "eng")}
        prev[s] = {x: bp.diff(wk1.get(s, {}), wk2.get(s, {}), x) for x in ("views", "fol", "eng")}
        alltime[s] = {x: now[s][x] for x in ("views", "fol", "eng")}
        for t, p in ((week, "this"), (prev, "prev"), (alltime, "all")):
            t[s].update(visits=g(p, "real"), used_ai=g(p, "used_ai"), signups=g(p, "signups"), paid=g(p, "purchases"))

    def tot(t, x):
        vals = [t[s][x] for s in t]
        return None if any(v is None for v in vals) and x not in ("views", "eng") else sum(v or 0 for v in vals)

    kpis = "".join([
        tile("Views", tot(alltime, "views"), tot(week, "views"), tot(prev, "views"), "since Oct 15 · Instagram + TikTok"),
        tile("Followers", tot(alltime, "fol"), tot(week, "fol"), tot(prev, "fol"), "today · Instagram + TikTok"),
        tile("People on Picsart", tot(alltime, "visits"), tot(week, "visits"), tot(prev, "visits"), "since Oct 15 · from the Instagram app"),
        tile("Used AI", tot(alltime, "used_ai"), tot(week, "used_ai"), tot(prev, "used_ai"), "since Oct 15 · any action on the AI screen"),
        tile("Sign-ups", tot(alltime, "signups"), tot(week, "signups"), tot(prev, "signups"), "since Oct 15 · new Picsart accounts"),
        tile("Paid", tot(alltime, "paid"), tot(week, "paid"), tot(prev, "paid"), "since Oct 15 · subscriptions or credits"),
    ])
    history = [(d, sum(v["views"] or 0 for v in bp.snapshot_at(sha).values())) for d, sha in commits if d < day]
    history.append((day, sum(v["views"] or 0 for v in now.values())))
    reach_chart = bp.overall_chart(history)

    mondays, per = weekly_views(day, commits)
    views_chart = stacked_bars(mondays, per, names)

    earlier = tot(alltime, "visits") - (tot(week, "visits") or 0) - (tot(prev, "visits") or 0)
    vis = visitor_bars([(f"Oct 15 to {(date.fromisoformat(conv['prev']['start']) - timedelta(days=1)):%-d %b}", earlier),
                        (f"{bp.nice(date.fromisoformat(conv['prev']['start']))} to {bp.nice(date.fromisoformat(conv['prev']['end']))}", tot(prev, "visits")),
                        (f"{bp.nice(start)} to {bp.nice(end)}", tot(week, "visits"))])

    fn_css = fn_html = fn_js = ""
    if fdata:
        fn_css, fn_html, fn_js = funnel.render(bp.funnel_data(fdata, now, wk1, {s: {"views": week[s]["views"]} for s in week},
                                                              {s: {"views": alltime[s]["views"]} for s in alltime}, conv, start, end))

    order = sorted(bp.accounts(), key=lambda b: -(alltime[b["slug"]]["views"] or now[b["slug"]].get("raw_views") or 0))
    rows = "".join(
        f'<tr><th scope="row"><span class="bn"><img src="img/{b["slug"]}.jpg" alt="">{E(b["name"])}</span></th>'
        f'<td data-label="Views since Oct 15"><b>{k(alltime[b["slug"]]["views"] if alltime[b["slug"]]["views"] is not None else now[b["slug"]].get("raw_views"))}</b></td>'
        f'<td data-label="Views this week"><b>{k(week[b["slug"]]["views"])}</b>{bp.change(week[b["slug"]]["views"], prev[b["slug"]]["views"])}</td>'
        f'<td data-label="Weekly views">{spark(per[b["slug"]])}</td>'
        f'<td data-label="Followers"><b>{k(alltime[b["slug"]]["fol"])}</b></td>'
        f'<td data-label="People on Picsart"><b>{k(alltime[b["slug"]]["visits"])}</b></td>'
        f'<td data-label="Sign-ups"><b>{k(alltime[b["slug"]]["signups"])}</b></td></tr>'
        for b in order)

    css = (OUT / "page.css").read_text()
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Social Performance Dashboard</title>
<meta name="description" content="How every Picsart social brand and AI influencer performs, on one screen: this week's key numbers, weekly views, visitors, the funnel from views to paying, and every account ranked.">
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#121212">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Mulish:wght@400;500;600;700&display=swap">
<link rel="preload" href="fonts/Acorn-Regular.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="fonts/Gilroy-SemiBold.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="picsart.css">
<style>{css}{fn_css}</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false">
  <symbol id="i-sun" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/></symbol>
  <symbol id="i-moon" viewBox="0 0 24 24"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></symbol>
</svg>
<header class="top">
  <div class="top-in">
    <a class="brand" href="#main" aria-label="Performance dashboard, back to top"><b>Performance dashboard</b></a>
    <span class="chname">/ week of {bp.nice(start)} to {bp.nice(end)}</span>
    <div class="tools">
      <button type="button" class="ibtn theme-btn" id="theme-btn" aria-label="Switch light or dark theme">
        <svg class="icon sun" aria-hidden="true"><use href="#i-sun"/></svg><svg class="icon moon" aria-hidden="true"><use href="#i-moon"/></svg>
      </button>
    </div>
  </div>
</header>
<main class="wrap" id="main">
  <div class="page-head">
    <h1>How our social accounts <span class="g">perform</span></h1>
    <p class="dek">{len(bp.accounts())} accounts: {len(bp.be.BRANDS)} AI-made brands and {len(bp.INFLUENCERS)} AI influencers. Everything since Oct 15, with what this week added.</p>
  </div>

  <section class="kpis" aria-label="Overall key numbers since Oct 15">{kpis}</section>

  <section class="panel chart" aria-labelledby="r-h">
    <div class="chart-head"><h3 id="r-h">Total reach since Oct 15</h3><span class="legend">views on Instagram and TikTok, all brands and AI influencers. Dashed: launch to the first reading</span></div>
    {reach_chart}
  </section>

  <div class="two">
    <section class="panel ch" aria-labelledby="v-h">
      <div class="chh"><h2 id="v-h">Views per week</h2><span class="legend">Instagram + TikTok, by account</span></div>
      {views_chart}
    </section>
    <section class="panel ch" aria-labelledby="p-h">
      <div class="chh"><h2 id="p-h">People on Picsart</h2><span class="legend">from the Instagram app, through our links</span></div>
      {vis}
      <p class="fine">Each person counted once, in the week of their first visit. Our own link checks are left out.</p>
    </section>
  </div>

  {fn_html}

  <section class="panel lb" aria-labelledby="l-h">
    <div class="chh"><h2 id="l-h">Every account</h2><span class="legend">highest reach first</span></div>
    <div class="tblw"><table class="lbt">
      <thead><tr><th scope="col">Account</th><th scope="col">Views since Oct 15</th><th scope="col">Views this week</th><th scope="col">Weekly views</th><th scope="col">Followers</th><th scope="col">People on Picsart</th><th scope="col">Sign-ups</th></tr></thead>
      <tbody>{rows}</tbody>
    </table></div>
  </section>

  <footer class="foot">
    <p>Views, followers and saves/shares: Instagram and TikTok, read {bp.nice(day)} (followers from the live Instagram profiles). People on Picsart, used AI, sign-ups and paid: Picsart's own data (Argus), {bp.nice(start)} to {bp.nice(end)} for the week; used AI counts any action on the AI screen. {('Funnel: ' + E(fdata['sources']['profile_visits'].split(';')[0]) + '. ') if fdata else ''}Updated {datetime.now():%a %-d %b %Y, %H:%M} Yerevan; refreshed every Monday with the weekly report.</p>
  </footer>
</main>
<script>{fn_js}</script>
<script>
document.getElementById("theme-btn").addEventListener("click", () => {{
  const r = document.documentElement; r.dataset.theme = r.dataset.theme === "light" ? "dark" : "light";
}});
</script>
</body>
</html>
"""


GITLAB = Path.home() / "vilya-ai/projects/social-performance-dashboard-site"  # gitlab.com/vilya.poghosyan/social-performance-dashboard


def gitlab_publish(page: Path, day: date) -> None:
    """Self-contained copy (fonts and CSS inlined, images next to it, noindex) into the GitLab Pages repo, then push."""
    pub = GITLAB / "public"
    pub.mkdir(parents=True, exist_ok=True)
    subprocess.run(["python3", str(KIT.parent / "scripts/inline_assets.py"), str(page), "-o", str(pub / "index.html")], check=True)
    html_ = (pub / "index.html").read_text()
    if 'name="robots"' not in html_:
        html_ = html_.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta name="robots" content="noindex">', 1)
    (pub / "index.html").write_text(html_)
    shutil.copytree(OUT / "img", pub / "img", dirs_exist_ok=True)
    run = lambda *a: subprocess.run(["git", "-C", str(GITLAB), *a], check=True)  # noqa: E731
    run("add", "--", "public", ".gitlab-ci.yml")
    if subprocess.run(["git", "-C", str(GITLAB), "diff", "--cached", "--quiet"]).returncode:
        run("commit", "-q", "-m", f"chore: dashboard {day.isoformat()}")
        run("push", "-q", "origin", "HEAD:main")
    print("gitlab: pushed, live https://social-performance-dashboard-ac007a.gitlab.io")


FILES = ["build_dashboard.py", "funnel.py", "dashboard/index.html", "dashboard/page.css", "dashboard/picsart.css",
         "dashboard/fonts", "dashboard/img"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=date.fromisoformat, default=date.today())
    ap.add_argument("--publish", action="store_true", help="commit the dashboard files and push")
    ap.add_argument("--gitlab", action="store_true", help="publish the self-contained page to its public GitLab Pages site")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    shutil.copy(KIT / "picsart.css", OUT / "picsart.css")
    shutil.copytree(KIT / "fonts", OUT / "fonts", dirs_exist_ok=True)
    shutil.copytree(HERE / "portfolio/img", OUT / "img", dirs_exist_ok=True)
    page = OUT / "index.html"
    page.write_text(build(a.day))
    print(page)
    if a.gitlab:
        gitlab_publish(page, a.day)
    if a.publish:
        subprocess.run(["git", "-C", str(HERE), "add", "--", *FILES], check=True)
        subprocess.run(["git", "-C", str(HERE), "commit", "-m", f"feat(dashboard): performance dashboard {a.day.isoformat()}", "--", *FILES], check=True)
        subprocess.run(["git", "-C", str(HERE), "push", "-q"], check=True)
        print("publish: pushed, live https://vilyapoghosyan.github.io/picsart-social-concepts/dashboard/")


if __name__ == "__main__":
    main()
