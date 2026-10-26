#!/usr/bin/env python3
"""One-pager: the best-working examples of each Picsart Social brand, with their numbers.

Reads the brand summary pages (summary/<brand>/index.html, built by build_brand_summary.py) for the best-post
tiles (video, poster, title, numbers, link) and writes best/index.html in the same style. The summary pages
themselves are not touched. Headline numbers per brand are the since-takeover figures as of the build date.

Run: python3 onepagers/build_best.py
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from build_brand_summary import CSS, E, NOW

HERE = Path(__file__).resolve().parent
AS_OF = "2026-10-26"

BRANDS = [
    dict(slug="reelo", name="Reelo", handle="@reelo.hq · @reelostudio", logo="../reelo/assets/logo-reelo.jpg",
         pages=[("Instagram", "https://www.instagram.com/reelo.hq/"), ("TikTok", "https://www.tiktok.com/@reelostudio")],
         since="Oct 17", posts="35 reels on each platform", views="202K", fol="104", eng="192", cost="110–220",
         concept="15-second Pixar-style stories about a toddler, a parent and a pet, told with faces and sound effects, no "
                 "dialogue. Four reels a day on Instagram and TikTok, the same file on both. Median reel 2,400 views on "
                 "Instagram and 340 on TikTok; followers from 21 to 104 in nine days. One keyframe on Gemini 3 Pro Image, "
                 "one 15-second Seedance 2.5 take with native sound.",
         picks=[("instagram", 0), ("instagram", 1), ("instagram", 2)],
         share="One visible gag in the first two seconds, a child's face reacting, and a caption that asks for a one-word comment."),
    dict(slug="microdramas", name="Microdramas", handle="@microdramas.ai", logo="../microdramas/assets/logo-microdramas.jpg",
         pages=[("Instagram", "https://www.instagram.com/microdramas.ai/"), ("TikTok", "https://www.tiktok.com/@microdramas.ai")],
         since="Oct 13", posts="36 episodes on each platform", views="34K", fol="149", eng="306", cost="1,100–2,700",
         concept="Serialized AI drama: 30 to 60-second episodes with spoken dialogue, 8 to 9 parts per series, every part "
                 "ending on a question. Five series live. The most engaged audience of the five brands: 179 saves and 127 "
                 "shares. The realistic TV-drama style used since Oct 21 (ONE YEAR, NO LOVE) averages 2,300 views per episode "
                 "on Instagram with 26 seconds of watch time, against about 200 views and 8 seconds for the earlier series.",
         picks=[("instagram", 0), ("instagram", 1), ("instagram", 2)],
         share="The premise is said out loud in the first five seconds, subtitles on every line, and a cliffhanger that makes the next part the obvious click."),
    dict(slug="dwell", name="Dwell", handle="@dwell.rooms · @dwellrooms", logo="../dwell/assets/logo-dwell.jpg",
         pages=[("Instagram", "https://www.instagram.com/dwell.rooms/"), ("TikTok", "https://www.tiktok.com/@dwellrooms"),
                ("Pinterest", "https://www.pinterest.com/dwellrooms/")],
         since="Oct 12 · Pinterest Oct 3", posts="32 posts on each platform + 105 pins", views="13K", fol="33", eng="174", cost="40–190 · pins 5",
         concept="Empty rooms turned into modern, old-money and chic luxury interiors: before/after match cuts, room tours, "
                 "variation swaps and trend carousels, two a day on Instagram and TikTok, plus five editorial room photos a day "
                 "on Pinterest. The highest saves per view of the five brands; Pinterest returns little so far (880 impressions "
                 "on 401 pins). A design review on Oct 23 set the next fixes: readable titles, a font per style, same-room "
                 "before/afters, more realistic video.",
         picks=[("instagram", 0), ("instagram", 1), ("tiktok", 0)],
         share="A named style people search for (old money, quiet luxury) and a reveal in the first three seconds."),
    dict(slug="faceless", name="Faceless", handle="@faceless_monetization", logo="../faceless/assets/logo-faceless.jpg",
         pages=[("Instagram", "https://www.instagram.com/faceless_monetization/")],
         since="Oct 5", posts="21", views="0.6K", fol="4", eng="not synced", cost="0–67",
         concept="\"Price Tag\" reels: one of our finished videos, what buyers pay for that kind of video, and the receipt of "
                 "tools and credits. Instagram only, one post a day. Still at the new-account floor; from Oct 26 every post "
                 "reuses the other brands' best videos, so a post costs 0 extra credits.",
         picks=[("instagram", 0), ("instagram", 1), ("instagram", 2)],
         share="A finished video first (a character skit, a trailer). How-to and price breakdowns on their own stay under 100 views."),
    dict(slug="listed", name="Listed", handle="@listed.hq", logo="../listed/assets/logo-listed.jpg",
         pages=[("Instagram", "https://www.instagram.com/listed.hq/")],
         since="Oct 5", posts="21 · nine products", views="0.9K", fol="4", eng="9", cost="5–28 per product",
         concept="Product photos for online sellers: an everyday phone photo of a product, fixed in Picsart, then the "
                 "tutorial with the exact path, and a Sunday carousel of the week. Instagram only, one post a day; median "
                 "26 views. Scale-or-stop call at its 12-post read.",
         picks=[("instagram", 0), ("instagram", 1), ("instagram", 2)],
         share="A product photo turned into a short video ad does best; static before/afters and tutorials stay under 60 views."),
]

COMMON = [
    "The best post of every brand shows a finished result in the first two to five seconds; explanation comes after, or not at all.",
    "Short and silent travels furthest (cartoons: about 23 credits per 1,000 views). Dialogue and story travel less far but are saved and shared (drama: 306 saves and shares on 34K views).",
    "Styles and words people already search for (old money, quiet luxury, \"which one would you pick\") outperform invented ones.",
    "Each file is posted on Instagram and TikTok at the same time; Instagram carries most of the views on every brand.",
]


def tiles_from_summary(slug: str) -> dict[str, list[str]]:
    """Best-post tiles per platform card, re-pathed for best/ (one level up from summary/<brand>/)."""
    h = (HERE / f"summary/{slug}/index.html").read_text()
    out: dict[str, list[str]] = {}
    for plat, card in re.findall(r'<article class="card" id="(\w+)">(.*?)</article>', h, re.S):
        best = re.search(r'<div class="best">(.*?)</div>\s*<div class="sub">Cost', card, re.S)
        if not best:
            continue
        exs = re.findall(r'<div class="ex">.*?</div>', best.group(1), re.S)
        out[plat] = [ex.replace('../../', '../') for ex in exs]
    return out


def brand_section(b: dict) -> str:
    tiles = tiles_from_summary(b["slug"])
    picked = []
    for plat, i in b["picks"]:
        lst = tiles.get(plat, [])
        if i < len(lst):
            picked.append(lst[i])
    counts = "".join(
        f'<div class="cnt"><div class="n">{E(v)}</div><div class="k">{E(k)}</div></div>'
        for k, v in [("Live since", b["since"]), ("Views", b["views"]), ("Followers", b["fol"]),
                     ("Saves + shares", b["eng"]), ("Credits per post", b["cost"])])
    visits = "".join(
        f'<a class="visit" href="{u}" target="_blank" rel="noopener"><span class="plat">{E(n)}</span> {E(b["handle"].split(" · ")[min(j, b["handle"].count(" · "))])} →</a>'
        for j, (n, u) in enumerate(b["pages"]))
    return f"""
  <article class="card" id="{b['slug']}">
    <div class="card-top">
      <div class="hero" style="margin-top:0">
        <img src="{b['logo']}" alt="{E(b['name'])} profile picture" style="width:52px;height:52px">
        <div><div class="brand">{E(b['name'])}<span class="niche">{E(b['posts'])}</span></div>
        <div class="handle">{E(b['handle'])}</div></div>
      </div>
      <span class="pill"><span class="dot"></span>Live</span>
    </div>
    <p class="pconcept">{E(b['concept'])}</p>
    <div class="counts">{counts}</div>
    <div class="sub">Best posts</div>
    <div class="best">{''.join(picked)}</div>
    <p class="note">What the winners share: {E(b['share'])}</p>
    <div class="visits">{visits}</div>
  </article>"""


def glance_rows() -> str:
    rows = ""
    for b in BRANDS:
        pages = " · ".join(f'<a href="{u}" target="_blank" rel="noopener" style="color:var(--accent-ink)">{E(n)}</a>' for n, u in b["pages"])
        rows += (f'<tr><td><a href="#{b["slug"]}"><b>{E(b["name"])}</b></a></td><td>{pages}</td><td>{E(b["since"])}</td>'
                 f'<td class="r">{E(b["views"])}</td><td class="r">{E(b["fol"])}</td><td class="r">{E(b["eng"])}</td></tr>')
    return rows


def main() -> None:
    sections = "".join(brand_section(b) for b in BRANDS)
    common = "".join(f"<li>{E(c)}</li>" for c in COMMON)
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Best Examples · Picsart Social</title>
<meta name="description" content="The best-working posts of each Picsart Social brand, with their numbers: Reelo, Microdramas, Dwell, Faceless, Listed.">
<style>{CSS}
  ul.common{{margin:.6rem 0 0; padding-left:1.2rem; color:var(--muted); font-size:.95rem}}
  ul.common li{{margin:.35rem 0}}
</style>
</head>
<body>
<main class="wrap">
  <div class="eyebrow">Picsart Social · Best examples</div>
  <h1 style="margin-top:.6rem">What works, brand by brand</h1>
  <p class="dek">Five AI-run brands, 254K views and 294 followers since the Oct 3 takeover. For each brand: its pages, its key
    numbers and the posts that worked best, with the platform's own counts. Numbers as of {AS_OF}.</p>

  <div class="sec-label">At a glance</div>
  <div class="card">
    <div style="overflow-x:auto"><table>
      <thead><tr><th>Brand</th><th>Pages</th><th>Live since</th><th class="r">Views</th><th class="r">Followers</th><th class="r">Saves + shares</th></tr></thead>
      <tbody>{glance_rows()}</tbody>
    </table></div>
    <p class="note">Views are Instagram and TikTok video views since the takeover (Pinterest reports impressions, kept apart: 880 on 401
      pins). One video posted on both platforms counts on each. Credits per post are all-in, rerolls included.</p>
  </div>

  <div class="sec-label">Brand by brand</div>
  {sections}

  <div class="sec-label">What the examples have in common</div>
  <div class="card">
    <ul class="common">{common}</ul>
    <p class="note">Full numbers per brand and platform, refreshed every Friday:
      <a href="../summary/" style="color:var(--accent-ink)">Picsart Social brands report →</a></p>
  </div>

  <footer>Views, likes, saves and shares come from Instagram, TikTok and Pinterest; followers and the newest reels are read from the
    public profiles. Snapshot of {AS_OF}, built {NOW:%Y-%m-%d %H:%M} Yerevan. Picsart Social automation project · made with Picsart</footer>
</main>
</body>
</html>
"""
    out = HERE / "best/index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page)
    refs = set(re.findall(r'(?:src|poster)="([^"]+)"', page))
    missing = [u for u in refs if not u.startswith("http") and not (out.parent / u).resolve().exists()]
    print(f"best/index.html written · {len(refs)} local media refs · missing: {missing or 'none'}")


if __name__ == "__main__":
    main()
