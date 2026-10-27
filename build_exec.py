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
    dict(slug="reelo", name="Reelo", hue="#E8572A", concept="15-second Pixar-style family cartoons, no dialogue. Four a day.",
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
    dict(slug="listed", name="Listed", hue="#0E8A54", concept="Product photos for online sellers: a phone photo fixed in Picsart, then the tutorial.",
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
        best += (f'<figure class="pick" id="{b["slug"]}" style="--hue:{b["hue"]}">{d["tile"]}'
                 f'<figcaption><b>{E(b["name"])}</b></figcaption></figure>')

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Executive Summary · Picsart Social</title>
<meta name="description" content="Social automation at Picsart: what we are doing, the goal, one dashboard of the five brands and the best post of each.">
<style>{CSS}
  .wrap{{max-width:1040px}}
  .kpis{{display:grid; grid-template-columns:repeat(3,1fr); gap:.7rem; margin-top:1.6rem}}
  .kpi{{background:linear-gradient(160deg,var(--accent-soft),var(--surface)); border:1px solid var(--line); border-radius:14px; padding:1rem 1.1rem}}
  .kpi .n{{font-size:2rem; font-weight:800; letter-spacing:-.03em; line-height:1; color:var(--accent-ink); font-variant-numeric:tabular-nums}}
  .kpi .k{{font-family:var(--mono); font-size:.62rem; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); margin-top:.5rem}}
  .two{{display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-top:1rem}}
  .two .card{{margin:0}}
  .two h3{{font-family:var(--mono); font-size:.66rem; letter-spacing:.14em; text-transform:uppercase; color:var(--accent-ink); margin:0 0 .5rem}}
  .two p{{margin:0; color:var(--ink); font-size:.97rem; line-height:1.55}}
  .dash{{padding:.6rem .4rem .4rem}}
  table.dash-t{{font-size:.86rem; table-layout:fixed; min-width:720px}}
  table.dash-t col.w-brand{{width:16%}} table.dash-t col.w-concept{{width:27%}} table.dash-t col.w-plat{{width:17%}}
  table.dash-t col.w-views{{width:15%}} table.dash-t col.w-fol{{width:8%}} table.dash-t col.w-eng{{width:8%}} table.dash-t col.w-cr{{width:9%}}
  table.dash-t th{{padding:.6rem .6rem; border-bottom:2px solid var(--line)}}
  table.dash-t td{{padding:.75rem .6rem; vertical-align:middle}}
  table.dash-t tbody tr:hover td{{background:var(--surface-2)}}
  .bname{{display:flex; align-items:center; gap:.6rem; font-weight:800; white-space:nowrap}}
  .bname img{{width:34px; height:34px; border-radius:50%; object-fit:cover; border:2px solid var(--hue)}}
  .bname small{{display:block; font-family:var(--mono); font-size:.6rem; font-weight:500; color:var(--faint); letter-spacing:.04em}}
  td.c{{color:var(--muted); font-size:.82rem; line-height:1.4}}
  td.r{{white-space:nowrap}}
  a.plat{{display:inline-block; font-family:var(--mono); font-size:.66rem; font-weight:600; padding:.22em .55em; border-radius:999px; border:1px solid var(--line); color:var(--accent-ink); background:var(--surface-2); margin:.1rem .15rem .1rem 0}}
  a.plat:hover{{border-color:var(--accent); background:var(--accent-soft)}}
  .v{{font-weight:800; font-variant-numeric:tabular-nums; white-space:nowrap}}
  .v small{{font-weight:500; color:var(--faint); font-size:.68rem}}
  .bar{{display:block; height:5px; border-radius:3px; background:var(--line); margin-top:.35rem; margin-left:auto; width:min(110px,100%); position:relative; overflow:hidden}}
  .bar::after{{content:""; position:absolute; right:0; top:0; bottom:0; width:var(--w); background:var(--hue); border-radius:3px}}
  tr.tot td{{font-weight:800; border-top:2px solid var(--line); border-bottom:0; background:var(--surface-2)}}
  .picks{{display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:.8rem}}
  .pick{{margin:0; display:flex; flex-direction:column; gap:.35rem; border-top:3px solid var(--hue); padding-top:.6rem}}
  .pick .ex{{display:flex; flex-direction:column; gap:.35rem}}
  .pick figcaption b{{font-size:.8rem}}
  @media(max-width:860px){{ .picks{{grid-template-columns:repeat(2,minmax(0,1fr))}} .two{{grid-template-columns:1fr}} .kpis{{grid-template-columns:1fr 1fr 1fr}} td.c{{max-width:none}} }}
  @media(max-width:520px){{ .kpis{{grid-template-columns:1fr}} .picks{{grid-template-columns:1fr 1fr}} }}
</style>
</head>
<body>
<main class="wrap">
  <div class="eyebrow">Picsart Social · Executive summary</div>
  <h1 style="margin-top:.6rem">Social automation at Picsart</h1>
  <p class="dek">Five AI-run brands, Oct 3 to {NOW:%b %-d}. Numbers from Instagram, TikTok and Pinterest, pulled {as_of} Yerevan.</p>

  <div class="kpis">
    <div class="kpi"><div class="n">{k(tot_views)}</div><div class="k">Views</div></div>
    <div class="kpi"><div class="n">{tot_fol:,}</div><div class="k">Followers</div></div>
    <div class="kpi"><div class="n">{tot_posts:,}</div><div class="k">Posts published</div></div>
  </div>

  <div class="two">
    <div class="card"><h3>What we are doing</h3><p>{E(WHAT)}</p></div>
    <div class="card"><h3>The goal</h3><p>{E(GOAL)}</p></div>
  </div>

  <div class="sec-label">Dashboard</div>
  <div class="card dash"><div style="overflow-x:auto"><table class="dash-t">
    <colgroup><col class="w-brand"><col class="w-concept"><col class="w-plat"><col class="w-views"><col class="w-fol"><col class="w-eng"><col class="w-cr"></colgroup>
    <thead><tr><th>Brand</th><th>Concept</th><th>Platforms</th><th class="r">Views</th><th class="r">Followers</th><th class="r">Saves + shares</th><th class="r">Credits, all-in</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
  <p class="note" style="padding:0 .6rem">Views = Instagram + TikTok video views on posts from Oct 3; Pinterest impressions shown beside Dwell. One video on two platforms counts on each.
    Credits are all-in: every reroll, remake, test and unposted asset included. Click a platform to open the account.</p></div>

  <div class="sec-label">What worked best · one post per brand</div>
  <div class="card"><div class="picks">{best}</div></div>

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
