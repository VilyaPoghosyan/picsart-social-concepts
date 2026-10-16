#!/usr/bin/env python3
"""Build one-brand summary pages in the style of the network executive summary.

One page per brand: key concept, overall numbers, then one card per live platform with that
platform's numbers, its 3 best posts (by views) and the production cost per post.

Inputs (read only): the same ledgers + stats.json + assets the showcase pages use
(see build_showcase.py), plus the per-episode credit log below.

Output: summary/<brand>/index.html
Refresh:  bin/with-env python3 bin/showcase_stats.py && python3 onepagers/build_brand_summary.py
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timedelta, timezone
from statistics import mean, median

from build_showcase import HERE, NOW, OUT, YEREVAN, dwell_posts, microdrama_series, sched, when_of

# Credits per episode, everything spent to get the posted cut (casting, keyframes, voices, takes,
# retakes and any discarded first version). Source: each episode's run.json + the production chat.
#   calls = Picsart's own price for every call we fired, summed (preflight / call price)
#   drop  = account balance before -> after the run (None when the pool was topped up mid-run)
#   basis = "exact"  : quiet account, balance drop == our calls, so the number is the real charge
#           "calls"  : shared account, other people spent in the same window; drop is an upper bound
#           "split"  : two episodes logged together; total split evenly
MICRO_COST = {
    "speak-now-1": dict(calls=1442, drop=1442, basis="exact", note="v1 454 (9,984→9,552 + 22 fix) + remake 988 (9,552→8,564); posted cut = remake"),
    "speak-now-2": dict(calls=1085, drop=None, basis="split", note="Parts 2+3 logged together: 2,170 by call prices; balance drop 4,064 for both"),
    "speak-now-3": dict(calls=1085, drop=None, basis="split", note="Parts 2+3 logged together: 2,170 by call prices; balance drop 4,064 for both"),
    "speak-now-4": dict(calls=1590, drop=2032, basis="calls", note="6 keyframes + 2 lip-sync redone"),
    "speak-now-5": dict(calls=1179, drop=1179, basis="exact", note="balance 18,557→17,378"),
    "speak-now-6": dict(calls=1103, drop=1103, basis="exact", note="balance 17,378→16,275"),
    "speak-now-7": dict(calls=1200, drop=2128, basis="calls", note="drop includes ~930 from other users"),
    "speak-now-8": dict(calls=2000, drop=2136, basis="calls", note="includes the ~280 Seedance vs Veo voice test"),
    "last-bite-1": dict(calls=2692, drop=None, basis="calls", note="v1 ~1,210 (discarded) + v2 ~1,482 (recast, proof, keyframes, takes)"),
    "last-bite-2": dict(calls=2000, drop=None, basis="calls", note="incl. 4 wasted takes"),
    "last-bite-3": dict(calls=1506, drop=1506, basis="exact", note="1,275 (2,494→1,219) + fix 231 (1,450→1,219)"),
    "last-bite-4": dict(calls=1310, drop=4876, basis="calls", note="drop mostly other users"),
    "last-bite-5": dict(calls=1330, drop=None, basis="calls", note="pool topped up mid-run"),
    "last-bite-6": dict(calls=1320, drop=4123, basis="calls", note="incl. 3 retakes"),
    "last-bite-7": dict(calls=1040, drop=3918, basis="calls", note="incl. 1 retake"),
    "family-portrait-1": dict(calls=2266, drop=3074, basis="calls", note="incl. proof takes 324"),
    "family-portrait-2": dict(calls=1886, drop=2012, basis="calls", note=""),
    "family-portrait-3": dict(calls=1915, drop=None, basis="calls", note=""),
    "family-portrait-4": dict(calls=1642, drop=3649, basis="calls", note="~2,000 of the drop from other users"),
    "family-portrait-5": dict(calls=1425, drop=None, basis="calls", note="pool topped up mid-run"),
    "family-portrait-6": dict(calls=1414, drop=None, basis="calls", note=""),
    "family-portrait-7": dict(calls=2119, drop=None, basis="calls", note=""),
    "remember-me-1": dict(calls=1109, drop=1109, basis="exact", note="balance 1,163→54"),
    "remember-me-2": dict(calls=1124, drop=1124, basis="exact", note="balance 10,039→8,915"),
    "remember-me-3": dict(calls=1131, drop=1131, basis="exact", note="balance 8,915→7,784"),
    "remember-me-4": dict(calls=1875, drop=4899, basis="calls", note="v1 1,101 + v2 re-shoot"),
    "remember-me-5": dict(calls=1271, drop=None, basis="calls", note="pool topped up mid-run"),
    "remember-me-6": dict(calls=1535, drop=3485, basis="calls", note="incl. 4 re-shoots"),
}

PLATFORM = {
    "instagram": dict(name="Instagram", fmt="Reels", url="https://www.instagram.com/microdramas.ai/",
                      concept="The home feed. Every part is a 9:16 Reel with a burned-in \"PART N\" title and a "
                              "cliffhanger caption that sends viewers to the profile for the previous parts. "
                              "Shares and saves are the signal we watch: people send the scene to someone."),
    "tiktok": dict(name="TikTok", fmt="Video", url="https://www.tiktok.com/@microdramas.ai",
                   concept="The same cut, cross-posted the same day, so it costs no extra credits. TikTok's For You "
                           "feed decides reach on watch time, so the first line of dialogue lands in the first "
                           "two seconds and every part ends on an unanswered question."),
}

E = html.escape


def n(v) -> str:
    return f"{int(v):,}"


def secs(ms) -> str:
    return f"{ms / 1000:.1f} s" if ms else "n/a"


def micro_posts():
    """Every ledger entry for the brand as dicts: platform, postId, when, episode metadata."""
    out = []
    for s in microdrama_series():
        L = sched(OUT / f"microdrama/{s['slug']}/schedule.json")
        for i, (asset, label, tease, _desc) in enumerate(s["episodes"], start=1):
            k = s["key"](i)
            for plat, key in (("instagram", k), ("tiktok", k.replace(":instagram", "") + ":tiktok")):
                e = L.get(key)
                if e:
                    out.append(dict(platform=plat, postId=e["postId"], when=when_of(e), asset=asset,
                                    series=s["title"], label=label, tease=tease))
    return out


CSS = """
  :root{
    --bg:#F7F7F9; --surface:#FFFFFF; --surface-2:#FBFAFC;
    --ink:#16151B; --muted:#6A6875; --faint:#9A98A5; --line:#EAEAEF;
    --accent:#C40F6B; --accent-ink:#A50C59; --accent-soft:#FBE9F2;
    --good:#0E8A54; --good-soft:#E6F4EC;
    --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
    --mono:ui-monospace,"SF Mono","SFMono-Regular",Menlo,Consolas,monospace;
    --shadow:0 1px 2px rgba(20,18,28,.05),0 12px 34px rgba(20,18,28,.06);
  }
  @media (prefers-color-scheme:dark){
    :root:not([data-theme="light"]){
      --bg:#101015; --surface:#18181F; --surface-2:#1E1E26;
      --ink:#F3F2F7; --muted:#A19FAD; --faint:#6C6A78; --line:#28282F;
      --accent:#F45FA6; --accent-ink:#F888BE; --accent-soft:#2A1420;
      --good:#37C98A; --good-soft:#122720;
      --shadow:0 1px 2px rgba(0,0,0,.3),0 14px 40px rgba(0,0,0,.4);
    }
  }
  :root[data-theme="dark"]{
    --bg:#101015; --surface:#18181F; --surface-2:#1E1E26; --ink:#F3F2F7; --muted:#A19FAD; --faint:#6C6A78;
    --line:#28282F; --accent:#F45FA6; --accent-ink:#F888BE; --accent-soft:#2A1420;
    --good:#37C98A; --good-soft:#122720; --shadow:0 1px 2px rgba(0,0,0,.3),0 14px 40px rgba(0,0,0,.4);
  }
  *{box-sizing:border-box}
  body{margin:0; background:var(--bg); color:var(--ink); font-family:var(--sans); font-size:16px; line-height:1.6; -webkit-font-smoothing:antialiased}
  .wrap{max-width:840px; margin:0 auto; padding:clamp(40px,7vw,80px) clamp(16px,5vw,40px) 72px}
  a{color:inherit; text-decoration:none}
  :focus-visible{outline:2px solid var(--accent); outline-offset:3px; border-radius:6px}
  .eyebrow{font-family:var(--mono); font-size:.72rem; letter-spacing:.2em; text-transform:uppercase; color:var(--accent-ink); font-weight:600}
  .hero{display:flex; gap:1.3rem; align-items:center; margin-top:.9rem}
  .hero img{width:76px; height:76px; border-radius:50%; object-fit:cover; flex:none; border:1px solid var(--line)}
  h1{font-size:clamp(2rem,6vw,3.1rem); line-height:1.03; letter-spacing:-.03em; font-weight:800; margin:0; text-wrap:balance}
  .handle{font-family:var(--mono); font-size:.8rem; color:var(--muted); margin-top:.35rem}
  .dek{font-size:clamp(1.02rem,2.3vw,1.2rem); color:var(--muted); margin:1.2rem 0 0; max-width:60ch; line-height:1.5}
  .sec-label{font-family:var(--mono); font-size:.7rem; letter-spacing:.14em; text-transform:uppercase; color:var(--faint); font-weight:600; margin:3rem 0 1rem; display:flex; align-items:center; gap:.7rem}
  .sec-label::after{content:""; flex:1; height:1px; background:var(--line)}
  .card{background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:1.3rem 1.4rem 1.4rem; box-shadow:var(--shadow); margin-bottom:1rem}
  .card-top{display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; flex-wrap:wrap}
  .brand{font-size:1.22rem; font-weight:800; letter-spacing:-.01em}
  .brand .niche{font-weight:500; color:var(--faint); font-size:.86rem; margin-left:.5rem}
  .pill{display:inline-flex; align-items:center; gap:.4em; font-family:var(--mono); font-size:.64rem; font-weight:600; letter-spacing:.04em; text-transform:uppercase; padding:.3em .65em; border-radius:999px; white-space:nowrap; color:var(--good); background:var(--good-soft)}
  .pill .dot{width:.5em; height:.5em; border-radius:50%; background:currentColor}
  .concept{display:grid; grid-template-columns:repeat(3,1fr); gap:.8rem; margin-top:1.1rem}
  .concept div{background:var(--surface-2); border:1px solid var(--line); border-radius:12px; padding:.8rem .9rem}
  .concept b{display:block; font-family:var(--mono); font-size:.63rem; letter-spacing:.08em; text-transform:uppercase; color:var(--accent-ink); margin-bottom:.3rem}
  .concept span{font-size:.92rem; color:var(--muted); line-height:1.45; display:block}
  .counts{display:grid; grid-template-columns:repeat(auto-fit,minmax(92px,1fr)); gap:.55rem; margin-top:1rem}
  .cnt{background:var(--surface-2); border:1px solid var(--line); border-radius:11px; padding:.75rem .6rem; text-align:center}
  .cnt .n{font-size:1.4rem; font-weight:800; letter-spacing:-.02em; font-variant-numeric:tabular-nums; line-height:1}
  .cnt .k{font-family:var(--mono); font-size:.6rem; letter-spacing:.05em; text-transform:uppercase; color:var(--faint); margin-top:.45rem}
  .note{font-family:var(--mono); font-size:.68rem; color:var(--faint); margin-top:.8rem; line-height:1.55}
  .pconcept{color:var(--muted); font-size:.95rem; margin:.7rem 0 0; max-width:66ch}
  .sub{font-family:var(--mono); font-size:.66rem; letter-spacing:.1em; text-transform:uppercase; color:var(--faint); font-weight:600; margin:1.4rem 0 .6rem}
  .best{display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.7rem}
  .ex{display:flex; flex-direction:column; gap:.35rem}
  .ex video{width:100%; aspect-ratio:9/16; border-radius:10px; display:block; background:#111; object-fit:cover; border:1px solid var(--line)}
  .ex .rank{font-family:var(--mono); font-size:.62rem; color:var(--accent-ink); font-weight:700; letter-spacing:.06em; text-transform:uppercase}
  .ex .h{font-weight:700; font-size:.88rem; line-height:1.3}
  .ex .m{font-family:var(--mono); font-size:.66rem; color:var(--muted); line-height:1.5}
  .ex .m a{color:var(--accent-ink)}
  .cost{display:grid; grid-template-columns:repeat(3,1fr); gap:.55rem; margin-top:.2rem}
  .cost .cnt{background:var(--accent-soft); border-color:transparent}
  .cost .cnt .n{color:var(--accent-ink)}
  .visits{display:flex; flex-wrap:wrap; gap:.55rem; margin-top:1.1rem}
  .visit{display:inline-flex; align-items:center; gap:.5rem; font-family:var(--mono); font-size:.75rem; font-weight:600; padding:.5rem .85rem; border:1px solid var(--line); border-radius:999px; color:var(--accent-ink); background:var(--surface-2)}
  .visit:hover{border-color:var(--accent); background:var(--accent-soft)}
  .visit .plat{color:var(--faint)}
  table{width:100%; border-collapse:collapse; font-size:.86rem; margin-top:.3rem}
  th,td{text-align:left; padding:.45rem .3rem; border-bottom:1px solid var(--line); font-variant-numeric:tabular-nums}
  th{font-family:var(--mono); font-size:.62rem; letter-spacing:.06em; text-transform:uppercase; color:var(--faint); font-weight:600}
  td.r,th.r{text-align:right}
  footer{font-family:var(--mono); font-size:.68rem; color:var(--faint); margin-top:3rem; line-height:1.6}
  @media(max-width:640px){
    .concept{grid-template-columns:1fr}
    .best{grid-template-columns:repeat(3,minmax(0,1fr)); gap:.45rem}
    .ex .h{font-size:.78rem}
    .cost{grid-template-columns:1fr 1fr}
    .hero img{width:60px; height:60px}
  }
"""


def tiles(items) -> str:
    return "".join(f'<div class="cnt"><div class="n">{v}</div><div class="k">{k}</div></div>' for k, v in items)




def rng(vals, f=None) -> str:
    f = f or n
    return f"{f(min(vals))}–{f(max(vals))}" if vals else "n/a"


def build_microdramas():
    stats = json.loads((HERE / "microdramas/stats.json").read_text())
    fol = stats.pop("_followers", {})
    posts = micro_posts()
    A = "../../microdramas/assets"
    mature_cut = NOW - timedelta(hours=24)

    plat_cards, overall = "", dict(pub=0, sched=0, views=0, likes=0, comments=0, shares=0, saves=0)
    live_eps = set()

    for plat, P in PLATFORM.items():
        mine = [p for p in posts if p["platform"] == plat]
        live = [p for p in mine if p["when"] and p["when"] <= NOW]
        soon = [p for p in mine if p["when"] and p["when"] > NOW]
        live_eps |= {p["asset"] for p in live}
        num = [(p, stats[p["postId"]]) for p in live if (stats.get(p["postId"]) or {}).get("views") is not None]
        tot = {k: sum(int(s.get(k) or 0) for _, s in num) for k in ("views", "likes", "comments", "shares", "saves")}
        overall["pub"] += len(live)
        overall["sched"] += len(soon)
        for k in tot:
            overall[k] += tot[k]
        eng = (tot["likes"] + tot["comments"] + tot["shares"] + tot["saves"]) / tot["views"] if tot["views"] else 0

        # per-post ranges only over posts live for 24 h+, so fresh posts don't drag the floor to 0
        mat = [s for p, s in num if p["when"] <= mature_cut]
        v = [int(s["views"]) for s in mat]
        lk = [int(s.get("likes") or 0) for s in mat]
        er = [(int(s.get("likes") or 0) + int(s.get("comments") or 0) + int(s.get("shares") or 0)
               + int(s.get("saves") or 0)) / s["views"] for s in mat if s["views"]]
        wt = [s["avgWatchMs"] for s in mat if s.get("avgWatchMs")]

        lows = [p for p, s in num if p["when"] <= mature_cut and int(s["views"]) < 20]
        low = (f'<p class="note">Below 20 views after 24 h+: ' + ", ".join(
            f"{E(p['series'])} {E(p['label'].split(' · ')[0])} ({n(stats[p['postId']]['views'])})" for p in lows)
            + f". These are {P['name']}'s own numbers; the posts most likely had their reach held back.</p>") if lows else ""
        best = sorted(num, key=lambda ps: (ps[1].get("views") or 0, ps[1].get("likes") or 0), reverse=True)[:3]
        ex = ""
        for r, (p, s) in enumerate(best, start=1):
            link = f' · <a href="{E(s["url"].split("?")[0])}" target="_blank" rel="noopener">watch on {P["name"]} →</a>' if s.get("url") else ""
            ex += f"""<div class="ex">
          <video src="{A}/{p['asset']}.mp4" poster="{A}/{p['asset']}.jpg" controls playsinline preload="none"></video>
          <span class="rank">#{r} · {E(p['series'])} · {E(p['label'].split(' · ')[0])}</span>
          <span class="h">{E(p['tease'])}</span>
          <span class="m">{n(s['views'])} views · {n(s.get('likes') or 0)} likes · {n(s.get('shares') or 0)} shares · {n(s.get('saves') or 0)} saves · {n(MICRO_COST[p['asset']]['calls'])} credits{link}</span>
        </div>"""

        c = [MICRO_COST[p["asset"]]["calls"] for p in live]
        cpk = sum(c) / (tot["views"] / 1000) if tot["views"] else 0
        plat_cards += f"""
  <article class="card" id="{plat}">
    <div class="card-top">
      <div class="brand">{P['name']}<span class="niche">{P['fmt']} · @microdramas.ai</span></div>
      <span class="pill"><span class="dot"></span>Live</span>
    </div>
    <p class="pconcept">{E(P['concept'])}</p>
    <div class="counts">{tiles([("Published", n(len(live))), ("Scheduled", n(len(soon))), ("Followers", n(fol.get(plat, 0))),
                                ("Views", n(tot['views'])), ("Likes", n(tot['likes'])), ("Comments", n(tot['comments'])),
                                ("Shares", n(tot['shares'])), ("Saves", n(tot['saves'])), ("Engagement", f"{eng:.1%}")])}</div>
    <div class="sub">Per post · {len(mat)} posts live 24 h or more</div>
    <div class="counts">{tiles([("Views range", rng(v)), ("Median views", n(median(v)) if v else "n/a"),
                                ("Likes range", rng(lk)), ("Engagement range", rng(er, lambda x: f"{x:.1%}")),
                                ("Avg watch range", rng(wt, secs))])}</div>
    <div class="sub">3 best posts on {P['name']} · by views</div>
    {low}<div class="best">{ex}</div>
    <div class="sub">Cost per post · {len(c)} live posts</div>
    <div class="cost">{tiles([("Credits / post, avg", n(mean(c))), ("Median", n(median(c))), ("Range", rng(c)),
                              ("Credits / 1K views", n(cpk))])}</div>
    <p class="note">Same file on both platforms, so posting it here as well adds 0 credits. Credits / 1K views = full cost of the
      {len(c)} live episodes ÷ {P['name']} views alone (if {P['name']} carried the whole cost).</p>
    <div class="visits"><a class="visit" href="{P['url']}" target="_blank" rel="noopener"><span class="plat">{P['name']}</span> @microdramas.ai →</a></div>
  </article>"""

    eng_all = ((overall["likes"] + overall["comments"] + overall["shares"] + overall["saves"]) / overall["views"]
               if overall["views"] else 0)
    live_c = [MICRO_COST[a]["calls"] for a in live_eps]
    cpk_all = sum(live_c) / (overall["views"] / 1000) if overall["views"] else 0

    series = microdrama_series()
    synced = max((s.get("lastUpdated") or "" for s in stats.values()), default="")[:16]

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Microdramas Brand Summary</title>
<meta name="description" content="Microdramas (@microdramas.ai): concept, live platforms, numbers, best posts and cost per post.">
<style>{CSS}
</style>
</head>
<body>
<main class="wrap">
  <div class="eyebrow">Picsart Social · brand summary</div>
  <div class="hero">
    <img src="{A}/logo-microdramas.jpg" alt="microdramas.ai profile picture">
    <div>
      <h1>Microdramas</h1>
      <div class="handle">@microdramas.ai · Instagram + TikTok</div>
    </div>
  </div>
  <p class="dek">Serialized AI love stories shot like a 1990s Hollywood film: 26–57 second episodes with spoken dialogue
    and cliffhanger endings, new parts most days. Every frame, voice and cut is made with Picsart AI.</p>

  <div class="sec-label">Key concept</div>
  <div class="card">
    <div class="concept">
      <div><b>Format</b><span>Vertical 9:16 episodes of 8-part series. Each part ends on a question, so viewers come back for the next one.</span></div>
      <div><b>Look</b><span>35 mm film, candlelight, satin and tuxedos, rainy streets. A recurring cast with fixed faces and voices per series.</span></div>
      <div><b>Engine</b><span>Keyframes on Nano Banana Pro and Seedream, continuous takes with native dialogue on Seedance 2.5, finished with the Picsart end card.</span></div>
    </div>
    <p class="note">Series so far: {" · ".join(E(s['title']) for s in series)}. {len(live_eps)} episodes live, one season (SPEAK NOW) complete.</p>
  </div>

  <div class="sec-label">Overall</div>
  <div class="card">
    <div class="counts">{tiles([("Platforms", "2"), ("Published", n(overall['pub'])), ("Scheduled", n(overall['sched'])),
                                ("Views", n(overall['views'])), ("Likes", n(overall['likes'])), ("Comments", n(overall['comments'])),
                                ("Shares", n(overall['shares'])), ("Saves", n(overall['saves'])), ("Engagement", f"{eng_all:.1%}")])}</div>
    <div class="sub">Cost · {len(live_eps)} live episodes</div>
    <div class="cost">{tiles([("Credits spent", n(sum(live_c))), ("Avg / episode", n(mean(live_c))),
                              ("Range", rng(live_c)), ("Credits / 1K views", n(cpk_all))])}</div>
    <p class="note">Published counts posts (one episode on two platforms = 2 posts). Engagement = (likes + comments + shares + saves) / views.
      Credits / 1K views = credits for the live episodes ÷ views on both platforms.</p>
  </div>

  <div class="sec-label">Platforms, by the numbers</div>
{plat_cards}

  <footer>Views, likes and the rest come from Instagram and TikTok through the publishing rail, pulled {NOW:%Y-%m-%d %H:%M} Yerevan
    (platform data last synced {E(synced)} UTC). Posts published in the last few hours still show low numbers. Picsart Social automation project · made with Picsart</footer>
</main>
</body>
</html>
"""
    out = HERE / "summary/microdramas/index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"microdramas summary: live eps {len(live_eps)} {sorted(live_eps)} · {overall} · live credits {sum(live_c)}")


# Dwell IG + TikTok credits per post. W42: per-post logs whose sum (822) equals the batch's balance
# drop 2,043 -> 1,221, so each is exact. W43: per-post logs (1,586) vs batch balance drop 1,597.
# Colour pairs and mouldings: call prices (the account was shared during those runs).
DWELL_COST = {
    "dwell-W42-01-parisian-salon": 143, "dwell-W42-02-old-world-house": 175, "dwell-W42-03-bedroom-trends-2027": 77,
    "dwell-W42-04-ivory-closet-reveal": 131, "dwell-W42-05-japandi-headboard-swap": 67,
    "dwell-W42-06-mediterranean-villa-set": 45, "dwell-W42-07-night-penthouse": 184,
    "dwell-colour-pairs": 440, "dwell-power-of-moulding": 180,
    "dwell-W43-01-wabi-sabi-spa-bath": 150, "dwell-W43-02-kitchen-trends-2027": 65, "dwell-W43-03-alpine-chalet": 174,
    "dwell-W43-04-scandi-fireplace-swap": 75, "dwell-W43-05-midcentury-conversation-pit": 173,
    "dwell-W43-06-desert-adobe-set": 40, "dwell-W43-07-industrial-loft": 140, "dwell-W43-08-coastal-beach-house": 175,
    "dwell-W43-09-dining-chandelier-swap": 67, "dwell-W43-10-living-room-trends-2027": 77,
    "dwell-W43-11-tuscan-farmhouse-kitchen": 139, "dwell-W43-12-art-deco-apartment": 131,
    "dwell-W43-13-attic-bedroom": 140, "dwell-W43-14-moroccan-riad-set": 40,
}
# Pinterest: our two pin runs on 2026-10-02 (dwell-content-runs.md): 70 pins, 185 + 180 = 365 credits,
# confirmed by the balance (5,730 -> 5,545 -> 5,365). 5 credits per image; 3 pins needed one reroll (10).
PIN_RUNS = dict(pins=70, credits=365, per_pin=[5] * 67 + [10] * 3, since="2026-10-03")

DWELL_PLATFORM = {
    "instagram": dict(name="Instagram", fmt="Reels + carousels", handle="@dwell.rooms",
                      url="https://www.instagram.com/dwell.rooms/",
                      concept="Two posts a day at 18:00 and 21:00 Yerevan: before/after match cuts, statement tours, walkthrough "
                              "reveals, variation swaps, colour pairs and trend carousels. Saves are the signal: designers keep "
                              "the room for later."),
    "tiktok": dict(name="TikTok", fmt="Videos + photo carousels", handle="@dwellrooms",
                   url="https://www.tiktok.com/@dwellrooms",
                   concept="The same posts at the same times, cross-posted, so they cost no extra credits. The reveal has to "
                           "land early, because the For You feed decides reach on watch time."),
    "pinterest": dict(name="Pinterest", fmt="Image pins", handle="@dwellrooms",
                      url="https://www.pinterest.com/dwellrooms/",
                      concept="Pinterest is a search engine, so each pin is a 2:3 editorial room photo titled like a search "
                              "(\"Midcentury living ideas\"), filed on a room board, with a link to Picsart. Five pins a day. "
                              "Pins keep getting found for months, so older pins still collect impressions."),
}


def card(plat, P, counts, per_post_label, per_post, low, best, cost, cost_note):
    return f"""
  <article class="card" id="{plat}">
    <div class="card-top">
      <div class="brand">{P['name']}<span class="niche">{P['fmt']} · {P['handle']}</span></div>
      <span class="pill"><span class="dot"></span>Live</span>
    </div>
    <p class="pconcept">{E(P['concept'])}</p>
    <div class="counts">{tiles(counts)}</div>
    <div class="sub">{per_post_label}</div>
    <div class="counts">{tiles(per_post)}</div>
    <div class="sub">3 best posts on {P['name']} · {'by impressions' if plat == 'pinterest' else 'by views'}</div>
    {low}<div class="best">{best}</div>
    <div class="sub">Cost per post</div>
    <div class="cost">{tiles(cost)}</div>
    <p class="note">{cost_note}</p>
    <div class="visits"><a class="visit" href="{P['url']}" target="_blank" rel="noopener"><span class="plat">{P['name']}</span> {P['handle']} →</a></div>
  </article>"""


def build_dwell():
    stats = json.loads((HERE / "dwell/stats.json").read_text())
    fol = stats.pop("_followers", {})
    pin = json.loads((HERE / "dwell/pinterest.json").read_text())
    A = "../../dwell/assets"
    mature_cut = NOW - timedelta(hours=24)

    posts = []
    for ledger, key, asset, kind, slides, label, hook, _desc in dwell_posts():
        for plat in ("instagram", "tiktok"):
            e = ledger.get(f"{key}:{plat}")
            if e:
                posts.append(dict(platform=plat, postId=e["postId"], when=when_of(e), asset=asset, kind=kind,
                                  label=label, hook=hook))

    cards, overall = "", dict(pub=0, sched=0, eng=0)
    reach_views = 0
    for plat in ("instagram", "tiktok"):
        P = DWELL_PLATFORM[plat]
        mine = [p for p in posts if p["platform"] == plat]
        live = [p for p in mine if p["when"] and p["when"] <= NOW]
        soon = [p for p in mine if p["when"] and p["when"] > NOW]
        num = [(p, stats[p["postId"]]) for p in live if (stats.get(p["postId"]) or {}).get("views") is not None]
        tot = {k: sum(int(s.get(k) or 0) for _, s in num) for k in ("views", "likes", "comments", "shares", "saves")}
        acts = tot["likes"] + tot["comments"] + tot["shares"] + tot["saves"]
        overall["pub"] += len(live)
        overall["sched"] += len(soon)
        overall["eng"] += acts
        reach_views += tot["views"]
        mat = [s for p, s in num if p["when"] <= mature_cut]
        v = [int(s["views"]) for s in mat]
        lk = [int(s.get("likes") or 0) for s in mat]
        sv = [int(s.get("saves") or 0) for s in mat]
        er = [(int(s.get("likes") or 0) + int(s.get("comments") or 0) + int(s.get("shares") or 0)
               + int(s.get("saves") or 0)) / s["views"] for s in mat if s["views"]]
        best = ""
        for r, (p, s) in enumerate(sorted(num, key=lambda ps: (ps[1].get("views") or 0, ps[1].get("likes") or 0),
                                          reverse=True)[:3], start=1):
            media = (f'<video src="{A}/{p["asset"]}.mp4" poster="{A}/{p["asset"]}.jpg" controls playsinline preload="none"></video>'
                     if p["kind"] == "reel" else f'<img class="pv" src="{A}/{p["asset"]}-slide1.jpg" alt="" loading="lazy">')
            link = f' · <a href="{E(s["url"].split("?")[0])}" target="_blank" rel="noopener">open on {P["name"]} →</a>' if s.get("url") else ""
            best += f"""<div class="ex">
          {media}
          <span class="rank">#{r} · {E(p['label'])}</span>
          <span class="h">{E(p['hook'])}</span>
          <span class="m">{n(s['views'])} views · {n(s.get('likes') or 0)} likes · {n(s.get('shares') or 0)} shares · {n(s.get('saves') or 0)} saves · {n(DWELL_COST[p['asset']])} credits{link}</span>
        </div>"""
        c = [DWELL_COST[p["asset"]] for p in live]
        cpk = sum(c) / (tot["views"] / 1000) if tot["views"] else 0
        cards += card(plat, P,
                      [("Published", n(len(live))), ("Scheduled", n(len(soon))), ("Followers", n(fol.get(plat, 0))),
                       ("Views", n(tot["views"])), ("Likes", n(tot["likes"])), ("Comments", n(tot["comments"])),
                       ("Shares", n(tot["shares"])), ("Saves", n(tot["saves"])),
                       ("Engagement", f"{acts / tot['views']:.1%}" if tot["views"] else "n/a")],
                      f"Per post · {len(mat)} posts live 24 h or more",
                      [("Views range", rng(v)), ("Median views", n(median(v)) if v else "n/a"), ("Likes range", rng(lk)),
                       ("Saves range", rng(sv)), ("Engagement range", rng(er, lambda x: f"{x:.1%}"))],
                      "", best,
                      [("Credits / post, avg", n(mean(c))), ("Median", n(median(c))), ("Range", rng(c)),
                       ("Credits / 1K views", n(cpk))],
                      f"Same file on both Instagram and TikTok, so posting it here as well adds 0 credits. Reels cost more than "
                      f"carousels (one frame per slide, no video). Credits / 1K views = full cost of the {len(c)} live posts ÷ "
                      f"{P['name']} views alone.")

    # Pinterest
    P = DWELL_PLATFORM["pinterest"]
    pins = pin["pins"]
    imp = sum(p["impressions"] for p in pins)
    saves = sum(p["saves"] for p in pins)
    clicks = sum(p["clicks"] for p in pins)
    mat = [p for p in pins if p["publishedAt"] and p["publishedAt"] <= mature_cut.astimezone(timezone.utc).isoformat()]
    pi = [p["impressions"] for p in mat]
    seen = sum(1 for p in pins if p["impressions"])
    ours = [p for p in pins if p["publishedAt"] >= PIN_RUNS["since"]]
    first = min(p["publishedAt"] for p in pins)[:10]
    best = ""
    for r, p in enumerate(sorted(pins, key=lambda p: (p["impressions"], p["saves"], p["clicks"]), reverse=True)[:3], start=1):
        posted = datetime.fromisoformat(p["publishedAt"].replace("Z", "+00:00")).astimezone(YEREVAN)
        best += f"""<div class="ex">
          <a href="{E(p['url'])}" target="_blank" rel="noopener"><img class="pv pin" src="{A}/{p['asset']}" alt="{E(p['title'])}" loading="lazy"></a>
          <span class="rank">#{r} · pin · {posted:%b %-d}</span>
          <span class="h">{E(p['title'])}</span>
          <span class="m">{n(p['impressions'])} impressions · {n(p['saves'])} saves · {n(p['clicks'])} clicks · <a href="{E(p['url'])}" target="_blank" rel="noopener">open on Pinterest →</a></span>
        </div>"""
    pc = PIN_RUNS["per_pin"]
    cards += card("pinterest", P,
                  [("Published", n(len(pins))), ("Scheduled", n(pin["scheduled"])), ("Followers", n(pin["followers"])),
                   ("Impressions", n(imp)), ("Saves", n(saves)), ("Clicks", n(clicks)),
                   ("Engagement", f"{(saves + clicks) / imp:.1%}" if imp else "n/a")],
                  f"Per pin · {len(mat)} pins live 24 h or more",
                  [("Impressions range", rng(pi)), ("Median impressions", n(median(pi)) if pi else "n/a"),
                   ("Pins with 1+ impression", f"{seen} of {len(pins)}"), ("Avg impressions", f"{mean(pi):.1f}" if pi else "n/a")],
                  f'<p class="note">For pins the publishing rail gets impressions, saves and clicks from Pinterest; there are no views, likes or comments. '
                  f'Live since {first}: {len(ours)} of the {len(pins)} pins went out from Oct 3, after our team took over.</p>',
                  best,
                  [("Credits / pin, avg", f"{PIN_RUNS['credits'] / PIN_RUNS['pins']:.1f}"), ("Median", n(median(pc))),
                   ("Range", rng(pc)), ("Credits / 1K impr.", n(PIN_RUNS["credits"] / (sum(p["impressions"] for p in ours) / 1000))
                    if any(p["impressions"] for p in ours) else "n/a")],
                  f"Exact: the {PIN_RUNS['pins']} pins made for Oct 3 onward cost {n(PIN_RUNS['credits'])} credits, confirmed by "
                  f"the account balance. One pin is one Gemini 3 Pro Image at 2K (5 credits); 3 pins needed one reroll (10). "
                  f"Pins posted before Oct 3 came from the earlier pipeline and are not in our cost logs, so they are left out "
                  f"of the cost. Credits / 1K impr. = {n(PIN_RUNS['credits'])} ÷ impressions on those {len(ours)} pins.")

    live_c = [DWELL_COST[a] for a in {p["asset"] for p in posts if p["when"] and p["when"] <= NOW}]
    synced = max((s.get("lastUpdated") or "" for s in stats.values()), default="")[:16]
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dwell Brand Summary</title>
<meta name="description" content="Dwell: concept, live platforms (Instagram, TikTok, Pinterest), numbers, best posts and credits per post.">
<style>{CSS}
  .ex img.pv{{width:100%; aspect-ratio:4/5; object-fit:cover; border-radius:10px; display:block; border:1px solid var(--line)}}
  .ex img.pv.pin{{aspect-ratio:2/3}}
</style>
</head>
<body>
<main class="wrap">
  <div class="eyebrow">Picsart Social · brand summary</div>
  <div class="hero">
    <img src="{A}/logo-dwell.jpg" alt="Dwell profile picture">
    <div>
      <h1>Dwell</h1>
      <div class="handle">@dwell.rooms · @dwellrooms · Instagram + TikTok + Pinterest</div>
    </div>
  </div>
  <p class="dek">Interiors, decoded. Empty rooms turned into modern, old-money and chic luxury interiors for designers and
    people collecting ideas. Every room is made with Picsart AI.</p>

  <div class="sec-label">Key concept</div>
  <div class="card">
    <div class="concept">
      <div><b>Format</b><span>15–23 s reels and 7–8 slide carousels on Instagram and TikTok; 2:3 room photos on Pinterest.</span></div>
      <div><b>Look</b><span>Marble, plaster, lacquer, travertine and brass, warm-neutral light, one palette per post, small spaced Gilroy capitals.</span></div>
      <div><b>Engine</b><span>Rooms on Gemini 3 Pro Image, camera moves on MiniMax and Kling V3, beat-synced ElevenLabs music, the linen and walnut Picsart end card.</span></div>
    </div>
    <p class="note">Live on 3 of Dwell's 4 platforms; the X account is not posting and is left out.</p>
  </div>

  <div class="sec-label">Overall</div>
  <div class="card">
    <div class="counts">{tiles([("Platforms", "3"), ("Published", n(overall['pub'] + len(pins))),
                                ("Scheduled", n(overall['sched'] + pin['scheduled'])),
                                ("IG + TikTok views", n(reach_views)), ("Pinterest impr.", n(imp)),
                                ("Followers", n(sum(fol.values()) + pin['followers']))])}</div>
    <div class="sub">Cost · {len(live_c)} live Instagram + TikTok posts, {PIN_RUNS['pins']} pins</div>
    <div class="cost">{tiles([("Credits, IG + TikTok", n(sum(live_c))), ("Credits, pins", n(PIN_RUNS['credits'])),
                              ("Avg / IG + TikTok post", n(mean(live_c))), ("Avg / pin", f"{PIN_RUNS['credits'] / PIN_RUNS['pins']:.1f}")])}</div>
    <p class="note">Published counts posts (one Instagram + TikTok post = 2). Views and impressions are kept apart: Pinterest
      only reports impressions.</p>
  </div>

  <div class="sec-label">Platforms, by the numbers</div>
{cards}

  <footer>Numbers come from Instagram, TikTok and Pinterest through the publishing rail, pulled {E(pin['pulledAt'])} Yerevan
    (platform data last synced {E(synced)} UTC). Posts published in the last few hours still show low numbers.
    Picsart Social automation project · made with Picsart</footer>
</main>
</body>
</html>
"""
    out = HERE / "summary/dwell/index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"dwell summary: IG/TT live {overall['pub']} sched {overall['sched']} views {reach_views} · pins {len(pins)} impr {imp}")


if __name__ == "__main__":
    build_microdramas()
    build_dwell()
