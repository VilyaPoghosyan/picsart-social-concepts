#!/usr/bin/env python3
"""AI Playground usage dashboard: what the people from our social links did on Picsart's AI Playground.

Vilya (2026-11-24), for Davit, "more concrete" than the performance dashboard: one screen about the Playground only.
Every number comes from one Argus run written to context/reports/conversion/playground/<day>.json (never typed in
here); a value that Argus did not return is null and shows "pending".

  key numbers   landed, stayed >10 s, opened the AI screen, pressed Generate, got a result, spent credits
  steps         the Playground funnel (funnel.py), per account and window
  accounts      what each account's visitors did, highest first
  models        which AI models they used

Run: python3 onepagers/build_playground.py --day YYYY-MM-DD [--gitlab]
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
import build_portfolio as bp
import funnel

E = html.escape
HERE = Path(__file__).resolve().parent
OUT = HERE / "playground"
DATA = Path.home() / "vilya-ai/context/reports/conversion/playground"
STEPS = [  # key, label, what it counts; each step is a smaller group than the one above
    ("landed", "Landed on AI Playground", "People from the Instagram app who opened AI Playground through one of our links, each counted once."),
    ("ai_screen", "Opened the AI screen", "Of those, people who opened an AI tool screen on AI Playground."),
    ("stayed", "Stayed longer than 10 seconds", "People whose AI Playground visit lasted more than 10 seconds (first to last event)."),
    ("type", "Typed a prompt", "People who typed or edited the prompt themselves."),
    ("generate", "Pressed Generate", "People who pressed Generate. Without an account, the sign-in screen stops them here."),
    ("signup", "Created an account", "People who signed up for a new Picsart account after coming through our link."),
    ("credits_users", "Spent credits on AI Playground", "Signed-in people who spent Picsart credits on AI Playground."),
    ("result", "Got a generated result", "People whose generation finished and loaded."),
]
KPIS = ["landed", "ai_screen", "stayed", "generate", "credits_users", "result"]


def build(day: date) -> str:
    d = json.loads((DATA / f"{day.isoformat()}.json").read_text())
    names = {b["slug"]: b["name"] for b in bp.accounts()}
    slugs = [s for s in d["all"] if s in names]
    order = sorted(slugs, key=lambda s: -(d["all"][s].get("landed") or 0))

    def total(w, k):
        vals = [d[w][s].get(k) for s in slugs]
        return None if any(v is None for v in vals) else sum(vals)

    def num(v):
        return "pending" if v is None else f"{v:,}"

    tiles = ""
    for k in KPIS:
        label = dict((s[0], s[1]) for s in STEPS)[k]
        extra = f" · {num(d['credits_total']['all'])} credits" if k == "credits_users" and d.get("credits_total") else ""
        wk = f" · {num(d['credits_total']['week'])} credits" if k == "credits_users" and d.get("credits_total") else ""
        tiles += (f'<div class="kpi"><span class="kl">{E(label)}</span><b>{num(total("all", k))}</b>'
                  f'<span class="kc">+{num(total("week", k))} this week{E(wk)}</span><small class="ks">since Oct 15{E(extra)}</small></div>')

    fdata = {
        "windows": [{"key": "all", "label": "Since Oct 15", "note": f"Since Oct 15 to {bp.nice(date.fromisoformat(d['end']))}."},
                    {"key": "week", "label": "This week", "note": f"{bp.nice(date.fromisoformat(d['week_start']))} to {bp.nice(date.fromisoformat(d['end']))}."}],
        "steps": [{"key": k, "label": l, "def": t, "source": "Picsart data (Argus)"} for k, l, t in STEPS],
        "accounts": [{"slug": s, "name": names[s], "img": f"img/{s}.jpg"} for s in order],
        "values": {"all": d["all"], "week": d["week"]},
        "pending": {},
    }
    fn_css, fn_html, fn_js = funnel.render(fdata)
    fn_html = fn_html.replace("From views to paying", "From landing to spending credits")

    heads = "".join(f'<th scope="col">{E(l)}</th>' for k, l, _ in STEPS)
    rows = "".join(
        f'<tr><th scope="row"><span class="bn"><img src="img/{s}.jpg" alt="">{E(names[s])}</span></th>'
        + "".join(f'<td><b>{num(d["all"][s].get(k))}</b><small>{num(d["week"][s].get(k))} this week</small></td>' for k, _, _ in STEPS)
        + "</tr>" for s in order)

    models = d.get("models_all", [])
    peak = max([m["devices"] for m in models] or [1])
    mbars = "".join(f'<div class="hr"><span>{E(m["name"])}</span><div class="tr"><i style="width:{100 * m["devices"] / peak:.1f}%"></i></div><b>{m["devices"]:,}</b></div>' for m in models)

    css = (bd.OUT / "page.css").read_text() + (OUT / "extra.css").read_text()
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>AI Playground Usage</title>
<meta name="description" content="What the people who came from Picsart's social accounts did on AI Playground: who stayed, opened the AI screen, pressed Generate, got a result and spent credits.">
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#121212">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Mulish:wght@400;500;600;700&display=swap">
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
    <a class="brand" href="#main" aria-label="AI Playground usage, back to top"><b>AI Playground usage</b></a>
    <span class="chname">/ Oct 15 to {bp.nice(date.fromisoformat(d['end']))}</span>
    <div class="tools">
      <button type="button" class="ibtn theme-btn" id="theme-btn" aria-label="Switch light or dark theme">
        <svg class="icon sun" aria-hidden="true"><use href="#i-sun"/></svg><svg class="icon moon" aria-hidden="true"><use href="#i-moon"/></svg>
      </button>
    </div>
  </div>
</header>
<main class="wrap" id="main">
  <div class="page-head">
    <h1>What our visitors did on <span class="g">AI Playground</span></h1>
    <p class="dek">Everyone who came to AI Playground from our social accounts' links, and how far they got: from landing to spending credits. Totals since Oct 15, with this week underneath.</p>
  </div>

  <section class="kpis" aria-label="Key numbers since Oct 15">{tiles}</section>

  {fn_html}

  <div class="two">
    <section class="panel ch" aria-labelledby="m-h">
      <div class="chh"><h2 id="m-h">Models they used</h2><span class="legend">people, since Oct 15</span></div>
      <div class="hb">{mbars}</div>
    </section>
    <section class="panel ch" aria-labelledby="k-h">
      <div class="chh"><h2 id="k-h">What it tells us</h2></div>
      <ol class="says">{"".join(f"<li>{E(x)}</li>" for x in d.get("says", []))}</ol>
    </section>
  </div>

  <footer class="foot">
    <p>{E(d['source'])} Updated {datetime.now():%a %-d %b %Y, %H:%M} Yerevan.</p>
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=date.fromisoformat, required=True)
    ap.add_argument("--gitlab", action="store_true", help="publish to the dashboard's GitLab Pages site under /playground/")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    shutil.copy(bd.KIT / "picsart.css", OUT / "picsart.css")
    shutil.copytree(bd.KIT / "fonts", OUT / "fonts", dirs_exist_ok=True)
    shutil.copytree(HERE / "portfolio/img", OUT / "img", dirs_exist_ok=True)
    page = OUT / "index.html"
    page.write_text(build(a.day))
    print(page)
    if a.gitlab:
        pub = bd.GITLAB / "public/playground"
        pub.mkdir(parents=True, exist_ok=True)
        subprocess.run(["python3", str(bd.KIT.parent / "scripts/inline_assets.py"), str(page), "-o", str(pub / "index.html")], check=True)
        h = (pub / "index.html").read_text()
        if 'name="robots"' not in h:
            h = h.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta name="robots" content="noindex">', 1)
        (pub / "index.html").write_text(h)
        shutil.copytree(OUT / "img", pub / "img", dirs_exist_ok=True)
        run = lambda *x: subprocess.run(["git", "-C", str(bd.GITLAB), *x], check=True)  # noqa: E731
        run("add", "--", "public/playground")
        run("commit", "-q", "-m", f"feat: AI Playground usage page {a.day.isoformat()}")
        run("push", "-q", "origin", "HEAD:main")
        print("gitlab: pushed, live https://social-performance-dashboard-ac007a.gitlab.io/playground/")


if __name__ == "__main__":
    main()
