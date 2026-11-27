#!/usr/bin/env python3
"""Visitors dashboard: who came to Picsart from our social links and what they did (public, no ids, abridged prompts).

Vilya (2026-11-27): a dashboard of the Argus deep dive, Picsart design without the logo, on the GitLab Pages site
next to the performance and AI Playground pages. Every number comes from
context/reports/conversion/visitors-dash/<day>.json (written from the Argus runs of that day); nothing is typed here.
The internal deep-dive file keeps the verbatim prompts; this page shows only short, grouped quotes.

Run: python3 onepagers/build_visitors_dash.py --day YYYY-MM-DD [--gitlab]
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
from datetime import date, datetime
from pathlib import Path

import build_dashboard as bd

E = html.escape
HERE = Path(__file__).resolve().parent
OUT = HERE / "visitors-dash"
DATA = Path.home() / "vilya-ai/context/reports/conversion/visitors-dash"


def bars(rows, peak=None, two=False) -> str:
    """Horizontal bars, highest first; two=True draws a magenta and a grey bar per row (Microdramas, Rich Ronnie)."""
    if two:
        top = peak or max(max(a, b) for _, a, b in rows) or 1
        return '<div class="vb">' + "".join(
            f'<div class="vr"><span class="vl">{E(l)}</span>'
            f'<div class="vt"><i class="m" style="width:{100 * a / top:.1f}%"></i><b>{a:,}</b></div>'
            f'<div class="vt"><i class="r" style="width:{100 * b / top:.1f}%"></i><b>{b:,}</b></div></div>'
            for l, a, b in rows) + "</div>"
    top = peak or max(v for _, v in rows) or 1
    return '<div class="vb">' + "".join(
        f'<div class="vr one"><span class="vl">{E(l)}</span><div class="vt"><i class="m" style="width:{100 * v / top:.1f}%"></i><b>{v:,}</b></div></div>'
        for l, v in sorted(rows, key=lambda r: -r[1])) + "</div>"


def build(day: date) -> str:
    d = json.loads((DATA / f"{day.isoformat()}.json").read_text())
    j, su, t = d["journey"], d["signup"], d["time"]
    md_n, rr_n = j["n"]

    tiles = "".join(f'<div class="kpi"><span class="kl">{E(l)}</span><b>{v:,}</b><small class="ks">{E(s)}</small></div>' for l, v, s in [
        ("People from Instagram", d["people_ig"], "opened Picsart through our links since Oct 15"),
        ("Reached the sign-in page", j["rows"][2][1] + j["rows"][2][2], "Microdramas + Rich Ronnie"),
        ("Pressed Generate", j["rows"][4][1] + j["rows"][4][2], "every press first stopped by sign-in"),
        ("New Picsart accounts", d["results"][0][1], "staff accounts left out"),
        ("Finished videos", d["results"][4][1], "from Rich Ronnie's link"),
        ("Paid", d["results"][5][1], "no purchase yet"),
    ])

    acc = "".join(f'<li><img src="img/{s}.jpg" alt=""><span>{E(n)}</span><b>{v:,}</b></li>' for s, n, v in d["accounts"])
    who = "".join(
        f'<div class="whoc"><div class="whoh"><img src="img/{k}.jpg" alt=""><b>{E(name)}</b><small>{v["n"]:,} people</small></div>'
        + "".join(f'<div class="wr"><span>{E(l)}</span><div class="vt"><i class="{"m" if k == "microdramas" else "r"}" style="width:{100 * n / v["n"]:.1f}%"></i><b>{n:,}</b></div></div>' for l, n in v["rows"])
        + "</div>" for k, name, v in (("microdramas", "Microdramas", d["who"]["microdramas"]), ("rich_ronnie", "Rich Ronnie", d["who"]["rich_ronnie"])))

    wk = t["weekday"]
    peak = max(max(wk["microdramas"]), 1)
    peak_r = max(max(wk["rich_ronnie"]), 1)
    days = "".join(
        f'<div class="dc"><div class="dbar"><i class="m" style="height:{100 * a / peak:.1f}%" title="Microdramas: {a}"></i></div>'
        f'<div class="dbar"><i class="r" style="height:{100 * b / peak_r:.1f}%" title="Rich Ronnie: {b}"></i></div><span>{dd}</span><small>{a} · {b}</small></div>'
        for dd, a, b in zip(wk["days"], wk["microdramas"], wk["rich_ronnie"]))

    prompts = "".join(
        f'<div class="pc"><div class="ph2"><b>{g["n"]}</b><span>{E(g["group"])}</span></div><p class="q">{E(g["quote"])}</p><small>{E(g["note"])}</small></div>'
        for g in sorted(d["prompts"], key=lambda g: -g["n"]))
    results = "".join(f'<li><span>{E(l)}</span><b>{v:,}</b></li>' for l, v in d["results"])
    says = "".join(f"<li>{E(x)}</li>" for x in d["says"])
    legend = '<span class="lgd"><i class="m"></i>Microdramas</span><span class="lgd"><i class="r"></i>Rich Ronnie</span>'

    css = (bd.OUT / "page.css").read_text() + (OUT / "extra.css").read_text()
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Social Link Visitors</title>
<meta name="description" content="Who came to Picsart from our social accounts' links and what they did: sources, people, journey, prompts and results.">
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#121212">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Mulish:wght@400;500;600;700&display=swap">
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
    <a class="brand" href="#main" aria-label="Social link visitors, back to top"><b>Social link visitors</b></a>
    <span class="chname">/ Oct 15 to {E(d['read'].split(',')[0])}</span>
    <div class="tools">
      <button type="button" class="ibtn theme-btn" id="theme-btn" aria-label="Switch light or dark theme">
        <svg class="icon sun" aria-hidden="true"><use href="#i-sun"/></svg><svg class="icon moon" aria-hidden="true"><use href="#i-moon"/></svg>
      </button>
    </div>
  </div>
</header>
<main class="wrap" id="main">
  <div class="page-head">
    <h1>Who came from our links, and <span class="g">what they did</span></h1>
    <p class="dek">Everyone who opened Picsart from the Instagram app through our social accounts' links since Oct 15: where they came from, who they are, how far they got, what they typed and what came of it.</p>
  </div>

  <section class="kpis" aria-label="Key numbers">{tiles}</section>

  <div class="two eq">
    <section class="panel ch" aria-labelledby="s-h">
      <div class="chh"><h2 id="s-h">Where they came from</h2><span class="legend">people, highest first</span></div>
      {bars(d["sources"])}
    </section>
    <section class="panel ch" aria-labelledby="a-h">
      <div class="chh"><h2 id="a-h">By account</h2><span class="legend">first visit</span></div>
      <ul class="accl">{acc}</ul>
      <p class="fine">{E(d['zero_accounts'])}</p>
    </section>
  </div>

  <section class="panel ch" aria-labelledby="w-h">
    <div class="chh"><h2 id="w-h">Who they are</h2><span class="legend">the two accounts that bring 99% of visitors</span></div>
    <div class="who">{who}</div>
  </section>

  <section class="panel ch" aria-labelledby="j-h">
    <div class="chh"><h2 id="j-h">How far they got</h2><span class="legend">{legend}</span></div>
    {bars(j["rows"], two=True)}
    <div class="alert"><b>This week</b> {d['week']['signin']} of {d['week']['n']} new Microdramas visitors reached the sign-in page, and {d['week']['left_signin']} left there.</div>
  </section>

  <div class="two eq">
    <section class="panel ch" aria-labelledby="u-h">
      <div class="chh"><h2 id="u-h">At the sign-in page</h2><span class="legend">{legend}</span></div>
      {bars(su["rows"], two=True)}
      <p class="fine">Email was rejected for {su['rejected_people']} of Rich Ronnie's visitors.</p>
    </section>
    <section class="panel ch" aria-labelledby="t-h">
      <div class="chh"><h2 id="t-h">When they come</h2><span class="legend">{legend}</span></div>
      <p class="fine">Visits by weekday since Oct 15; each account on its own scale (Microdramas · Rich Ronnie under each day).</p>
      <div class="days">{days}</div>
      <ul class="kv">
        <li><span>Median time on Picsart</span><b>{t['median'][0]} s · {t['median'][1]} s</b></li>
        <li><span>Came only once</span><b>{t['one_session'][0]:,} · {t['one_session'][1]:,}</b></li>
        <li><span>Came back on another day</span><b>{t['returned'][0]:,} · {t['returned'][1]:,}</b></li>
      </ul>
    </section>
  </div>

  <section class="panel ch" aria-labelledby="p-h">
    <div class="chh"><h2 id="p-h">What they typed</h2><span class="legend">people per kind of prompt</span></div>
    <div class="pcs">{prompts}</div>
    <p class="fine">{E(d['prompts_note'])}</p>
  </section>

  <div class="two eq">
    <section class="panel ch" aria-labelledby="r-h">
      <div class="chh"><h2 id="r-h">What came of it</h2></div>
      <ul class="kv big">{results}</ul>
      <p class="fine">{E(d['results_note'])}</p>
    </section>
    <section class="panel ch" aria-labelledby="g-h">
      <div class="chh"><h2 id="g-h">Pages they opened</h2><span class="legend">people, besides AI Playground</span></div>
      {bars(d["pages"])}
    </section>
  </div>

  <section class="panel ch" aria-labelledby="k-h">
    <div class="chh"><h2 id="k-h">What it tells us</h2></div>
    <ol class="says">{says}</ol>
  </section>

  <footer class="foot"><p>{E(d['source'])} Updated {datetime.now():%a %-d %b %Y, %H:%M} Yerevan.</p></footer>
</main>
<script>
document.getElementById("theme-btn").addEventListener("click", () => {{
  const r = document.documentElement; r.dataset.theme = r.dataset.theme === "light" ? "dark" : "light";
}});
</script>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=date.fromisoformat, required=True)
    ap.add_argument("--gitlab", action="store_true", help="publish under /visitors/ on the dashboard's GitLab Pages site")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    shutil.copy(bd.KIT / "picsart.css", OUT / "picsart.css")
    shutil.copytree(bd.KIT / "fonts", OUT / "fonts", dirs_exist_ok=True)
    shutil.copytree(HERE / "portfolio/img", OUT / "img", dirs_exist_ok=True)
    page = OUT / "index.html"
    page.write_text(build(a.day))
    print(page)
    if a.gitlab:
        pub = bd.GITLAB / "public/visitors"
        pub.mkdir(parents=True, exist_ok=True)
        subprocess.run(["python3", str(bd.KIT.parent / "scripts/inline_assets.py"), str(page), "-o", str(pub / "index.html")], check=True)
        h = (pub / "index.html").read_text()
        if 'name="robots"' not in h:
            h = h.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta name="robots" content="noindex">', 1)
        (pub / "index.html").write_text(h)
        shutil.copytree(OUT / "img", pub / "img", dirs_exist_ok=True)
        run = lambda *x: subprocess.run(["git", "-C", str(bd.GITLAB), *x], check=True)  # noqa: E731
        run("add", "--", "public/visitors")
        run("commit", "-q", "-m", f"feat: social link visitors page {a.day.isoformat()}")
        run("push", "-q", "origin", "HEAD:main")
        print("gitlab: pushed, live https://social-performance-dashboard-ac007a.gitlab.io/visitors/")


if __name__ == "__main__":
    main()
