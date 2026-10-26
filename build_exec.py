#!/usr/bin/env python3
"""Executive summary page (executive-summary/index.html), same style as the brand report. One screen:
what we are doing, why, the goal, the five brands, results for the period, link to the best-examples page.
Numbers are a dated snapshot; edit the constants below and rebuild. The summary pages are not touched.

Run: python3 onepagers/build_exec.py
"""
from __future__ import annotations

from pathlib import Path

from build_brand_summary import CSS, E, NOW

HERE = Path(__file__).resolve().parent
AS_OF = "2026-10-26"
PERIOD = "Oct 3 to Oct 26"

WHAT = ("Five social media brands run entirely on Picsart GenAI: an automated pipeline writes, generates, quality-checks "
        "and publishes four to eight posts a day on Instagram, TikTok and Pinterest, every one labelled \"made with Picsart\". "
        "One person reviews and approves; no production team. Running since Oct 3.")
WHY = ("To grow social channels to millions of engagements without manual work, and to prove at scale what Picsart's premium "
       "models (Seedance 2.5, Gemini 3 Pro Image, Nano Banana Pro) can produce: five concepts tested side by side show which "
       "formats earn reach, which earn engagement, and what each costs.")
GOAL = ("Grow these channels to millions of engagements and convert that audience into Picsart users: every post is labelled "
        "\"made with Picsart\", and keyword posts send viewers the exact Picsart steps by DM. The system should run itself, with "
        "human work under 30 minutes a day. Each concept gets a scale-or-stop decision after 12 posts, on fixed dates "
        "(Nov 21, Nov 28, Dec 5).")
RESULTS = ("254K views and 294 followers in three weeks, up 3.6× in the last week. Four fifths of the reach comes from one brand, "
           "Reelo's cartoons (202K views in nine days); Microdramas brings the engagement (the most saves and shares, the fastest "
           "follower growth); the other three are still at the new-account floor. Credits are all-in, every reroll and test included.")

BRANDS = [  # brand, concept, platforms, live since, cadence
    ("Reelo", "15-second Pixar-style family cartoons: a toddler, a parent and a pet, no dialogue", "Instagram, TikTok", "Oct 17", "4 a day"),
    ("Microdramas", "Serialized AI drama, 30 to 60-second episodes with spoken dialogue, 8 to 9 parts per series", "Instagram, TikTok", "Oct 13", "1 to 4 a day"),
    ("Dwell", "Luxury interiors: before/afters, room tours and trend carousels for people collecting ideas", "Instagram, TikTok, Pinterest", "Oct 12 (Pinterest Oct 3)", "2 a day + 5 pins"),
    ("Faceless", "\"Price Tag\" reels: one of our finished videos, what buyers pay for it, and the receipt of tools and credits", "Instagram", "Oct 5", "1 a day"),
    ("Listed", "Product photos for online sellers: a phone photo fixed in Picsart, then the tutorial", "Instagram", "Oct 5", "1 a day"),
]
NUMBERS = [  # brand, views, followers, saves+shares, credits all-in, credits per 1K views
    ("Reelo (cartoons since Oct 17)", "202K", "104", "192", "~4,600", "~23"),
    ("Microdramas", "34K", "149", "306", "80,297", "~2,400"),
    ("Dwell (Instagram + TikTok; Pinterest 880 impressions)", "13K", "33", "174", "5,434", "~420"),
    ("Faceless", "0.6K", "4", "not synced", "525", "~870"),
    ("Listed", "0.9K", "4", "9", "137", "~160"),
    ("All five", "254K", "294", "680+", "~100,900", "~400"),
]


def rows(data, bold_last=False):
    out = ""
    for i, r in enumerate(data):
        cells = [f"<td>{E(r[0])}</td>"] + [f'<td class="r">{E(c)}</td>' if c[:1].isdigit() or c[:1] in "~0" or c == "not synced" else f"<td>{E(c)}</td>" for c in r[1:]]
        if bold_last and i == len(data) - 1:
            cells = [c.replace("<td", "<td style=\"font-weight:700\"", 1) for c in cells]
        out += "<tr>" + "".join(cells) + "</tr>"
    return out


def main() -> None:
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Executive Summary · Picsart Social</title>
<meta name="description" content="Social automation at Picsart: what we are doing, why, the goal, the five brands and the results for {PERIOD}.">
<style>{CSS}
  .sec-label{{margin-top:2.2rem}}
  p.body{{color:var(--ink); font-size:1rem; line-height:1.6; margin:0; max-width:72ch}}
</style>
</head>
<body>
<main class="wrap">
  <div class="eyebrow">Picsart Social · Executive summary</div>
  <h1 style="margin-top:.6rem">Social automation at Picsart</h1>
  <p class="dek">Status as of {AS_OF}.</p>

  <div class="sec-label">What we are doing</div>
  <p class="body">{E(WHAT)}</p>

  <div class="sec-label">Why</div>
  <p class="body">{E(WHY)}</p>

  <div class="sec-label">The goal</div>
  <p class="body">{E(GOAL)}</p>

  <div class="sec-label">What we have</div>
  <div class="card"><div style="overflow-x:auto"><table>
    <thead><tr><th>Brand</th><th>Concept</th><th>Platforms</th><th>Live since</th><th>Cadence</th></tr></thead>
    <tbody>{rows(BRANDS)}</tbody>
  </table></div></div>

  <div class="sec-label">Results, {PERIOD}</div>
  <p class="body"><b>{E(RESULTS.split(',', 1)[0])}</b>,{E(RESULTS.split(',', 1)[1])}</p>
  <div class="card" style="margin-top:1rem"><div style="overflow-x:auto"><table>
    <thead><tr><th>Brand</th><th class="r">Views</th><th class="r">Followers</th><th class="r">Saves + shares</th><th class="r">Credits spent (all-in)</th><th class="r">Credits per 1K views</th></tr></thead>
    <tbody>{rows(NUMBERS, bold_last=True)}</tbody>
  </table></div></div>

  <div class="sec-label">More detail</div>
  <p class="body">The best-performing post of each brand, with its numbers: <a href="../best/" style="color:var(--accent-ink)">Best examples →</a></p>

  <footer>Views are Instagram and TikTok video views; Pinterest reports impressions and is kept apart. Credits are all-in: every reroll,
    remake, test and unposted asset included. Snapshot of {AS_OF}, built {NOW:%Y-%m-%d %H:%M} Yerevan. Picsart Social automation project · made with Picsart</footer>
</main>
</body>
</html>
"""
    out = HERE / "executive-summary/index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page)
    print("executive-summary/index.html written")


if __name__ == "__main__":
    main()
