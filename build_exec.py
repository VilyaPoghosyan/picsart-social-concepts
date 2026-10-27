#!/usr/bin/env python3
"""Executive summary page (executive-summary/index.html): what we are doing, the goal, one dashboard table
(brand · concept · platforms · views · followers · saves + shares · credits all-in) and the single best post per brand.

Every number is read from the refreshed brand report (summary/<brand>/index.html, summary/index.html, reelo/feed.json),
so run bin/brand_summary_weekly.py (or build_brand_summary.py) first, then this. The summary pages are not touched.
Views for Reelo count posts from Oct 3 only (the accounts carry older posts from a previous pipeline).

Run: python3 onepagers/build_exec.py
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from build_brand_summary import CSS, E, NOW

HERE = Path(__file__).resolve().parent
SINCE = datetime(2026, 10, 3, tzinfo=timezone.utc)

WHAT = ("Five social media brands run end to end on Picsart GenAI. An automated pipeline writes, generates, quality-checks "
        "and publishes four to eight posts a day on Instagram, TikTok and Pinterest; one person reviews and approves, no "
        "production team. Every post carries \"made with Picsart\". Running since Oct 3.")
GOAL = ("Millions of engagements, converted into Picsart users: every post is labelled \"made with Picsart\", and keyword "
        "posts send viewers the exact Picsart steps by DM. Five concepts run side by side to learn which formats earn "
        "reach, which earn engagement and what each costs on Picsart's premium models (Seedance 2.5, Gemini 3 Pro Image, "
        "Nano Banana Pro).")

BRANDS = [  # slug, name, concept, hue, platforms (name, handle, url)
    dict(slug="reelo", name="Reelo", hue="#BF3F18", concept="15-second Pixar-style family cartoons, no dialogue. Four a day.",
         plats=[("Instagram", "@reelo.hq", "https://www.instagram.com/reelo.hq/"), ("TikTok", "@reelostudio", "https://www.tiktok.com/@reelostudio")],
         since="Oct 17"),
    dict(slug="microdramas", name="Microdramas", hue="#C40F6B", concept="Serialized AI drama: 30 to 60-second episodes with dialogue, 8 to 9 parts a series.",
         plats=[("Instagram", "@microdramas.ai", "https://www.instagram.com/microdramas.ai/"), ("TikTok", "@microdramas.ai", "https://www.tiktok.com/@microdramas.ai")],
         since="Oct 13"),
    dict(slug="dwell", name="Dwell", hue="#8A6D3B", concept="Luxury interiors: before/afters, room tours and trend carousels, plus Pinterest pins.",
         plats=[("Instagram", "@dwell.rooms", "https://www.instagram.com/dwell.rooms/"), ("TikTok", "@dwellrooms", "https://www.tiktok.com/@dwellrooms"),
                ("Pinterest", "@dwellrooms", "https://www.pinterest.com/dwellrooms/")],
         since="Oct 12 · pins Oct 3"),
    dict(slug="faceless", name="Faceless", hue="#2F6FDE", concept="Price Tag reels: our finished video, what buyers pay for it, the receipt.",
         plats=[("Instagram", "@faceless_monetization", "https://www.instagram.com/faceless_monetization/")], since="Oct 5"),
    dict(slug="listed", name="Listed", hue="#0C7446", concept="Product photos for online sellers: a phone photo fixed in Picsart, then the tutorial.",
         plats=[("Instagram", "@listed.hq", "https://www.instagram.com/listed.hq/")], since="Oct 5"),
]


def txt(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def num(s: str) -> int:
    m = re.search(r"[\d,]+", s or "")
    return int(m.group(0).replace(",", "")) if m else 0


def brand_numbers(slug: str) -> dict:
    """Views, followers, saves + shares, credits all-in and the #1 Instagram tile from the brand's report page."""
    h = (HERE / f"summary/{slug}/index.html").read_text()
    out = dict(views=0, fol=0, eng=0, pins="", tile="", tile_url="", tile_title="", tile_m="")
    for plat, card in re.findall(r'<article class="card" id="(\w+)">(.*?)</article>', h, re.S):
        tiles = {txt(k): txt(v) for v, k in re.findall(r'<div class="n">(.*?)</div><div class="k">(.*?)</div>', card, re.S)}
        if plat == "pinterest":
            out["pins"] = f'{num(tiles.get("Impressions", "0")):,} pin impressions'
            out["fol"] += num(tiles.get("Followers", "0"))
            continue
        out["views"] += num(tiles.get("Views", "0"))
        out["fol"] += num(tiles.get("Followers", "0"))
        if tiles.get("Saves", "").lower() != "not synced":
            out["eng"] += num(tiles.get("Saves", "0")) + num(tiles.get("Shares", "0"))
        if plat == "instagram" and not out["tile"]:
            best = re.search(r'<div class="best">(.*?)</div>\s*<div class="sub">Cost', card, re.S)
            ex = re.findall(r'<div class="ex">(.*?)</div>', best.group(1), re.S)[0] if best else ""
            v = re.search(r'(?:src|poster)="([^"]+\.(?:mp4|jpg))"', ex)
            out["tile"] = ex.replace("../../", "../")
            vid = re.search(r'<video src="([^"]+)" poster="([^"]+)"', out["tile"])
            out["video"], out["poster"] = (vid.group(1), vid.group(2)) if vid else ("", "")
            out["tile_url"] = (re.search(r'href="(https?://[^"]+)"', ex) or [None, ""])[1]
            out["tile_title"] = txt((re.search(r'class="h">(.*?)</span>', ex) or [None, ""])[1])
            out["tile_m"] = txt((re.search(r'class="m">(.*?)</span>', ex) or [None, ""])[1]).split(" · open")[0].split(" · watch")[0]
    # all-in credits from the overview table
    ov = (HERE / "summary/index.html").read_text()
    row = re.search(r"<tr>\s*<td><a[^>]*href=['\"]%s/['\"]" % slug + r".*?</tr>", ov, re.S)
    cells = re.findall(r"<td[^>]*>(.*?)</td>", row.group(0), re.S) if row else []
    out["credits"] = txt(cells[-1]).split(" incl.")[0] if cells else "n/a"
    out["published"] = num(txt(cells[2])) if cells else 0
    if slug == "reelo":  # drop posts before Oct 3 (previous pipeline) from views and engagement
        feed = json.loads((HERE / "reelo/feed.json").read_text())
        for plat in ("instagram", "tiktok"):
            items = feed.get(plat, [])
            items = items.get("posts", []) if isinstance(items, dict) else items
            for p in items:
                if not isinstance(p, dict):
                    continue
                try:
                    dt = datetime.fromisoformat(str(p.get("publishedAt", "")).replace("Z", "+00:00"))
                except ValueError:
                    continue
                if dt < SINCE:
                    out["views"] -= int(p.get("views") or 0)
                    out["eng"] -= int(p.get("saves") or 0) + int(p.get("shares") or 0)
                    out["published"] -= 1
    return out


def k(n: int) -> str:
    return f"{n / 1000:.0f}K" if n >= 10000 else (f"{n / 1000:.1f}K" if n >= 1000 else f"{n:,}")


def main() -> None:
    data = {b["slug"]: brand_numbers(b["slug"]) for b in BRANDS}
    tot_views = sum(d["views"] for d in data.values())
    tot_fol = sum(d["fol"] for d in data.values())
    tot_eng = sum(d["eng"] for d in data.values())
    tot_posts = sum(d["published"] for d in data.values())
    max_views = max(d["views"] for d in data.values()) or 1
    pulled = re.search(r"pulled ([0-9-]+ [0-9:]+)", (HERE / "summary/index.html").read_text())
    as_of = pulled.group(1) if pulled else f"{NOW:%Y-%m-%d %H:%M}"

    days = (NOW.replace(tzinfo=None) - datetime(2026, 10, 3)).days
    half = round(days / 7 * 2) / 2  # nearest half week
    weeks = (f"{int(half)}" + ("½" if half % 1 else "")) + " weeks"
    rows = ""
    for b in BRANDS:
        d = data[b["slug"]]
        plats = " ".join(f'<a class="plat" href="{u}" target="_blank" rel="noopener" title="{E(h)}">{E(n)}</a>' for n, h, u in b["plats"])
        bar = f'<span class="bar" style="--w:{100 * d["views"] / max_views:.0f}%;--hue:{b["hue"]}"></span>'
        views = f'<div class="v">{k(d["views"])}{(" <small>+ " + E(d["pins"]) + "</small>") if d["pins"] else ""}</div>{bar}'
        eng = f'{d["eng"]:,}' if d["eng"] else "not synced"
        rows += (f'<tr><td><a class="bname" href="#{b["slug"]}" style="--hue:{b["hue"]}"><img src="../{b["slug"]}/assets/logo-{b["slug"]}.jpg" alt="">'
                 f'<span>{E(b["name"])}<small>since {E(b["since"])}</small></span></a></td>'
                 f'<td class="c">{E(b["concept"])}</td><td class="p">{plats}</td>'
                 f'<td class="r">{views}</td><td class="r">{d["fol"]:,}</td><td class="r">{eng}</td><td class="r">{E(d["credits"])}</td></tr>')
    rows += (f'<tr class="tot"><td>All five</td><td></td><td></td><td class="r"><div class="v">{k(tot_views)}</div></td>'
             f'<td class="r">{tot_fol:,}</td><td class="r">{tot_eng:,}</td><td class="r">{E(_sum_credits(data))}</td></tr>')

    best = ""
    for b in BRANDS:
        d = data[b["slug"]]
        m = d["tile_m"]
        views = num(m.split("·")[0])
        rest = [x.strip() for x in m.split("·")[1:] if "credits" not in x and not x.strip().startswith("0 ")]
        plat_name, _, plat_url = b["plats"][0]
        media = (f'<video src="{d["video"]}" poster="{d["poster"]}" controls playsinline preload="none"></video>' if d["video"]
                 else f'<img src="{d["poster"]}" alt="" loading="lazy">')
        best += (f'<figure class="pick" id="{b["slug"]}" style="--hue:{b["hue"]}">'
                 f'<div class="media">{media}<span class="chip">{E(b["name"])}</span>'
                 f'<span class="views"><b>{k(views)}</b>views</span></div>'
                 f'<figcaption><span class="t">{E(d["tile_title"])}</span>'
                 f'<span class="m">{E(" · ".join(rest))}</span>'
                 f'<a class="open" href="{E(d["tile_url"] or plat_url)}" target="_blank" rel="noopener">Open on {E(plat_name)} →</a></figcaption></figure>')

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Executive Summary · Picsart Social</title>
<meta name="description" content="Social automation at Picsart: what we are doing, the goal, one dashboard of the five brands and the best post of each.">
<style>{CSS}
  :root{{--faint:#6F6D7A}}
  @media (prefers-color-scheme:dark){{ :root:not([data-theme="light"]){{--faint:#9A98A8}} }}
  :root[data-theme="dark"]{{--faint:#9A98A8}}
  ::selection{{background:var(--accent-soft); color:var(--ink)}}
  .wrap{{max-width:1040px}}
  .note{{font-size:.76rem}} .sec-label{{font-size:.72rem}} footer{{font-size:.76rem}}
  .kpis{{display:grid; grid-template-columns:repeat(3,1fr); gap:.7rem; margin-top:1.6rem}}
  .kpi{{background:linear-gradient(160deg,var(--accent-soft),var(--surface)); border:1px solid var(--line); border-radius:14px; padding:1rem 1.1rem}}
  .kpi .n{{font-size:2rem; font-weight:800; letter-spacing:-.03em; line-height:1; color:var(--accent-ink); font-variant-numeric:tabular-nums}}
  .kpi .k{{font-family:var(--mono); font-size:.72rem; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); margin-top:.5rem}}
  .two{{display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-top:1rem}}
  .two .card{{margin:0}}
  .two h2{{font-family:var(--mono); font-size:.72rem; letter-spacing:.14em; text-transform:uppercase; color:var(--accent-ink); margin:0 0 .5rem}}
  .two p{{margin:0; color:var(--ink); font-size:.97rem; line-height:1.55}}
  .dash{{padding:.6rem .4rem .4rem}}
  table.dash-t{{font-size:.86rem; table-layout:fixed; min-width:720px}}
  table.dash-t col.w-brand{{width:16%}} table.dash-t col.w-concept{{width:27%}} table.dash-t col.w-plat{{width:17%}}
  table.dash-t col.w-views{{width:15%}} table.dash-t col.w-fol{{width:8%}} table.dash-t col.w-eng{{width:8%}} table.dash-t col.w-cr{{width:9%}}
  table.dash-t th{{padding:.6rem .6rem; border-bottom:2px solid var(--line); font-size:.7rem}}
  table.dash-t td{{padding:.75rem .6rem; vertical-align:middle}}
  table.dash-t tbody tr:hover td{{background:var(--surface-2)}}
  .bname{{display:flex; align-items:center; gap:.6rem; font-weight:800; white-space:nowrap}}
  .bname img{{width:34px; height:34px; border-radius:50%; object-fit:cover; border:2px solid var(--hue)}}
  .bname small{{display:block; font-family:var(--mono); font-size:.7rem; font-weight:500; color:var(--faint); letter-spacing:.04em}}
  td.c{{color:var(--muted); font-size:.82rem; line-height:1.4}}
  td.r{{white-space:nowrap}}
  a.plat{{display:inline-block; font-family:var(--mono); font-size:.72rem; font-weight:600; padding:.22em .55em; border-radius:999px; border:1px solid var(--line); color:var(--accent-ink); background:var(--surface-2); margin:.1rem .15rem .1rem 0}}
  a.plat:hover{{border-color:var(--accent); background:var(--accent-soft)}}
  .v{{font-weight:800; font-variant-numeric:tabular-nums; white-space:nowrap}}
  .v small{{font-weight:500; color:var(--faint); font-size:.72rem}}
  .bar{{display:block; height:5px; border-radius:3px; background:var(--line); margin-top:.35rem; margin-left:auto; width:min(110px,100%); position:relative; overflow:hidden}}
  .bar::after{{content:""; position:absolute; right:0; top:0; bottom:0; width:var(--w); background:var(--hue); border-radius:3px}}
  tr.tot td{{font-weight:800; border-top:2px solid var(--line); border-bottom:0; background:var(--surface-2)}}
  .picks{{display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:1rem}}
  .pick{{margin:0; display:flex; flex-direction:column; gap:.55rem}}
  .pick .media{{position:relative; border-radius:14px; overflow:hidden; background:#111; aspect-ratio:9/16; box-shadow:0 10px 28px rgba(20,18,28,.18)}}
  .pick .media video,.pick .media img{{width:100%; height:100%; object-fit:cover; display:block; border:0; border-radius:0}}
  .pick .media::before{{content:""; position:absolute; left:0; right:0; top:0; height:38%; background:linear-gradient(to bottom,rgba(0,0,0,.72),rgba(0,0,0,0)); pointer-events:none; z-index:1}}
  .pick .chip,.pick .views{{z-index:2}}
  .pick .chip{{position:absolute; top:10px; left:10px; font-family:var(--mono); font-size:.7rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:#fff; background:var(--hue); padding:.3em .6em; border-radius:999px; pointer-events:none}}
  .pick .views{{position:absolute; top:10px; right:10px; display:flex; flex-direction:column; align-items:flex-end; line-height:1; color:#fff; text-shadow:0 1px 8px rgba(0,0,0,.6); pointer-events:none}}
  .pick .views b{{font-size:1.55rem; font-weight:800; letter-spacing:-.03em; font-variant-numeric:tabular-nums}}
  .pick .views{{font-family:var(--mono); font-size:.7rem; letter-spacing:.1em; text-transform:uppercase}}
  .pick .t{{display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; font-weight:700; font-size:.86rem; line-height:1.3; letter-spacing:-.01em}}
  .pick .m{{display:block; font-family:var(--mono); font-size:.76rem; color:var(--muted); margin-top:.3rem; line-height:1.5}}
  .pick .open{{display:inline-block; margin-top:.45rem; font-family:var(--mono); font-size:.74rem; font-weight:600; color:var(--hue); border-bottom:1px solid transparent}}
  .pick .open:hover{{border-bottom-color:var(--hue)}}
  @media(max-width:860px){{ table.dash-t{{table-layout:auto; min-width:860px}} .picks{{grid-template-columns:repeat(2,minmax(0,1fr))}} .two{{grid-template-columns:1fr}} .kpis{{grid-template-columns:1fr 1fr 1fr}} td.c{{max-width:none}} }}
  @media(max-width:520px){{ .kpis{{grid-template-columns:1fr}} .picks{{grid-template-columns:1fr 1fr}} }}
</style>
</head>
<body>
<main class="wrap">
  <h1>Social automation at Picsart</h1>
  <p class="dek">Five AI-run brands, {weeks} in. Numbers from Instagram, TikTok and Pinterest, pulled {as_of} Yerevan.</p>

  <div class="kpis">
    <div class="kpi"><div class="n">{k(tot_views)}</div><div class="k">Views</div></div>
    <div class="kpi"><div class="n">{tot_fol:,}</div><div class="k">Followers</div></div>
    <div class="kpi"><div class="n">{tot_posts:,}</div><div class="k">Posts published</div></div>
  </div>

  <div class="two">
    <div class="card"><h2>What we are doing</h2><p>{E(WHAT)}</p></div>
    <div class="card"><h2>The goal</h2><p>{E(GOAL)}</p></div>
  </div>

  <div class="sec-label">Dashboard</div>
  <div class="card dash"><div style="overflow-x:auto"><table class="dash-t">
    <colgroup><col class="w-brand"><col class="w-concept"><col class="w-plat"><col class="w-views"><col class="w-fol"><col class="w-eng"><col class="w-cr"></colgroup>
    <thead><tr><th>Brand</th><th>Concept</th><th>Platforms</th><th class="r">Views</th><th class="r">Followers</th><th class="r">Saves + shares</th><th class="r">Credits, all-in</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
  <p class="note" style="padding:0 .6rem">Views = Instagram + TikTok video views on posts from Oct 3; Pinterest impressions shown beside Dwell. One video on two platforms counts on each.
    Credits are all-in: every reroll, remake, test and unposted asset included. Click a platform to open the account.</p></div>

  <div class="sec-label">What worked best</div>
  <div class="picks">{best}</div>

  <footer>Picsart Social automation project · made with Picsart · built {NOW:%Y-%m-%d %H:%M} Yerevan</footer>
</main>
</body>
</html>
"""
    out = HERE / "executive-summary/index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page)
    refs = set(re.findall(r'(?:src|poster)="([^"]+)"', page))
    missing = [u for u in refs if not u.startswith("http") and not (out.parent / u).resolve().exists()]
    print(f"executive-summary/index.html · views {tot_views:,} · followers {tot_fol} · posts {tot_posts} · missing media: {missing or 'none'}")


def _sum_credits(data: dict) -> str:
    tot = 0.0
    for d in data.values():
        m = re.search(r"[\d,.]+", d["credits"])
        tot += float(m.group(0).replace(",", "")) if m else 0
    return f"{tot:,.0f}"


if __name__ == "__main__":
    main()
