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
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
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
    "remember-me-7": dict(calls=2743, drop=None, basis="calls", note="incl. T1/T2/T6/T7 re-fires"),
    "remember-me-8": dict(calls=1073, drop=None, basis="calls", note="logged total in run.json"),
    "last-bite-8": dict(calls=1300, drop=2958, basis="calls", note="call list ~1,300; drop includes other users"),
    "family-portrait-8": dict(calls=1617, drop=None, basis="calls", note="logged total in run.json"),
    "one-year-no-love-1": dict(calls=1450, drop=1380, basis="calls", note="v2 THE DEAL incl. the re-made opening"),
    "one-year-no-love-2": dict(calls=1754, drop=None, basis="calls", note="v2 THE WEDDING 1,600 + hand-kiss fix 154"),
    "one-year-no-love-3": dict(calls=1636, drop=1636, basis="exact", note="v2 SEPARATE ROOMS (3,073 -> 1,437)"),
    "one-year-no-love-4": dict(calls=1260, drop=1260, basis="exact", note="v2 THE INTERVIEW 1,102 + glass-door ending re-made 158"),
    # made 2026-10-23, not scheduled yet (waiting for a credit top-up): counted in ALL_IN["microdramas"]["unposted"]
    # v2 P5 THE VISIT ~2,550 (balance 15,147 -> 12,598), P6 THE EX ~1,850, P7 OPENING NIGHT ~1,513, P8 THE FILE 2,690 (max-based)
}

# ALL-IN credits per brand (audited 2026-10-23 from every run log, run.json and balance drop, including work
# that was never posted). Per-post figures quote the TOP of the range (Vilya 2026-10-23: never the minimum).
# Each run counts its own logged credits (rerolls, retries, fixes included). Balance drops from runs while the
# account was shared are NOT used: they include other brands' work. Microdramas max per episode: highest
# logged 2,743 (REMEMBER ME P7), quoted as up to 3,200 for unlogged retries (Vilya 2026-10-23).
ALL_IN = {
    "microdramas": dict(total=80297, waste=16123, unposted=8603, per_max=3200, unit="episode",
        waste_note="discarded, redone and deleted episodes, standalone tests and remakes never posted, casting and look tests",
        unposted_note="ONE YEAR, NO LOVE parts 5–8, made Oct 23 and waiting for a credit top-up before they are scheduled"),
    "dwell": dict(total=5434, waste=302, unposted=0, per_max=440, unit="reel or carousel",
        waste_note="format test reel never posted (132) and the Oct 23 realism proof, a before/after of one real-looking room made for the design review (170)",
        extra="pins up to 10 each; 545 credits on 105 pins"),
    "reelo": dict(total=14516, waste=3755, unposted=220, per_max=230, unit="cartoon reel",
        waste_note="7 tiny-world videos built and never posted (2,977), cartoon format test, cast sheets, a rejected reel, a failed render, loop tests, unlogged retries in the Oct 23 batch of 30 (139)",
        unposted_note="one Halloween-week reel (Weekend with Max) held for garbled lettering",
        extra="the older tiny-world videos cost up to 436 each"),
    "faceless": dict(total=524.5, waste=0, unposted=0, per_max=67, unit="post",
        waste_note="no remakes logged; Price Tag posts reuse other brands' videos (0 extra)"),
    "listed": dict(total=137, waste=11, unposted=0, per_max=28, unit="product",
        waste_note="tests and redone steps"),
}


def allin_card(slug):
    a = ALL_IN[slug]
    t = [("All-in credits spent", f"{a['total']:,.0f}"), ("On remakes, fixes, tests", f"{a['waste']:,.0f}"),
         (f"Max per {a['unit']}", f"{a['per_max']:,}")]
    if a.get("unposted"):
        t.insert(2, ("Made, not posted yet", f"{a['unposted']:,}"))
    note = (f"All-in = every credit this brand has used, posted or not. Remakes, fixes and tests: {a['waste_note']}."
            + (f" {a['extra'][0].upper() + a['extra'][1:]}." if a.get("extra") else "")
            + " Each run counts its own logged credits with every reroll, retry and fix; the max per post is rounded up.")
    return (f'<div class="sec-label">Cost · all in</div>\n  <div class="card">\n    <div class="cost">{tiles(t)}</div>\n'
            f'    <p class="note">{E(note)}</p>\n  </div>\n\n  ')


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
    """Every ledger entry for the brand as dicts: platform, postId, when, episode metadata.

    Episodes on the hand-written series lists (build_showcase.microdrama_series) come first; any other
    ledger entry (a new episode or a new series) is picked up from schedule.json + schedule_plan.json."""
    out, used = [], set()
    series = {s["slug"]: s for s in microdrama_series()}
    for s in series.values():
        L = sched(OUT / f"microdrama/{s['slug']}/schedule.json")
        for i, (asset, label, tease, _desc) in enumerate(s["episodes"], start=1):
            k = s["key"](i)
            for plat, key in (("instagram", k), ("tiktok", k.replace(":instagram", "") + ":tiktok")):
                e = L.get(key)
                if e:
                    used.add((s["slug"], key))
                    out.append(dict(platform=plat, postId=e["postId"], when=when_of(e), asset=asset,
                                    series=s["title"], label=label, tease=tease, src=None))
    for led in sorted((OUT / "microdrama").glob("*/schedule.json")):
        d = led.parent
        plan = sched(d / "schedule_plan.json").get("items", [])
        by_slug = {it["slug"]: it for it in plan}
        for key, e in json.loads(led.read_text()).items():
            if (d.name, key) in used or not e.get("postId") or e.get("status") == "deleted":
                continue
            slug, _, plat = key.partition(":")
            plat = plat or "instagram"
            m = re.search(r"(?:part-|p)(\d+)$", slug)
            ep = int(m.group(1)) if m else None
            it = by_slug.get(slug, {})
            cap = d / it["caption_file"] if it.get("caption_file") else None
            tease = cap.read_text().strip().split("\n")[0] if cap and cap.exists() else f"Part {ep}"
            title = series[d.name]["title"] if d.name in series else d.name.replace("-", " ").upper()
            prefix = d.name.replace("the-", "", 1) if d.name == "the-last-bite" else d.name
            out.append(dict(platform=plat, postId=e["postId"], when=when_of(e), asset=f"{prefix}-{ep}" if ep else slug,
                            series=title, label=f"Part {ep}" if ep else slug, tease=tease,
                            src=d / it["file"] if it.get("file") else None))
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
  .ex .thumb{position:relative; display:block}
  .ex .thumb.blank{position:relative; display:block; aspect-ratio:9/16; border-radius:10px; border:1px solid var(--line); background:var(--surface-2); background-image:linear-gradient(160deg,var(--accent-soft),var(--surface-2)); font-family:var(--mono); font-size:.62rem; color:var(--accent-ink)}
  .ex .thumb.blank .lbl{position:absolute; left:0; right:0; bottom:12px; text-align:center; padding:0 8px}
  .ex .play{position:absolute; inset:0; display:grid; place-items:center}
  .ex .play::before{content:""; width:40px; height:40px; border-radius:50%; background:rgba(0,0,0,.55)}
  .ex .play::after{content:""; position:absolute; border-style:solid; border-width:8px 0 8px 13px; border-color:transparent transparent transparent #fff; margin-left:3px}
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


def avg(vals, f=None) -> str:
    return (f or n)(mean(vals)) if vals else "n/a"


def med(vals, f=None) -> str:
    return (f or n)(median(vals)) if vals else "n/a"


def known(vals):
    """Drop posts whose cost is not logged (None) before averaging."""
    return [v for v in vals if v is not None]


def cr_txt(v, f=None) -> str:
    return f"{(f or n)(v)} credits" if v is not None else "credits not logged"


# Live Instagram views (bin/live_views.py reads the public reels grid; the rail lags by hours).
LIVE = sched(HERE / "live_views.json")


def live_ig(url):
    m = re.search(r"/(?:reel|p)/([^/?#]+)", url or "")
    return LIVE.get("instagram", {}).get(m.group(1)) if m else None


def apply_live(rows):
    """Replace rail numbers with live ones: Instagram views (public grid), TikTok plays/likes/... (video page)."""
    for row in rows:
        if not isinstance(row, dict):
            continue
        url = row.get("url") or ""
        if "instagram.com" in url:
            v = live_ig(url)
            if v is not None:
                row["views"] = v
                row["live"] = True
        elif "tiktok.com" in url:
            m = re.search(r"/(?:video|photo)/(\d+)", url)
            t = LIVE.get("tiktok", {}).get(m.group(1)) if m else None
            if t:
                row.update(t)
                row["live"] = True


def live_fol(platform, handle, fallback):
    """Followers: the higher of the public profile count and the rail's count (the public Instagram page can be
    served from a cache, the rail can lag; a count only drops on unfollows, so the higher one is the fresher)."""
    live = LIVE.get("followers", {}).get(platform, {}).get(handle)
    vals = [v for v in (live, fallback) if v is not None]
    return max(vals) if vals else None


def live_note():
    return (f"Followers, TikTok numbers and the newest Instagram reels' views are read live from the public profiles "
            f"({LIVE['pulledAt']} Yerevan); the rest comes from the publishing rail." if LIVE.get("pulledAt") else "")


# Things a weekly run could not fill in by itself; printed by build_all for the run report.
GAPS: list[str] = []


def gap(msg):
    if msg not in GAPS:
        GAPS.append(msg)


def make_asset(src: Path, dest: Path, kind: str) -> bool:
    """720p mp4 + poster (video) or a 720 px jpg (image) from a source file. Returns True when dest exists."""
    if kind == "video":
        if dest.with_suffix(".mp4").exists():
            return True
        if not src or not Path(src).exists():
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", "scale=720:-2", "-c:v", "libx264",
                        "-crf", "28", "-preset", "veryfast", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart",
                        str(dest.with_suffix(".mp4"))], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1.5", "-i", str(src), "-frames:v", "1", "-vf",
                        "scale=720:-2", "-q:v", "4", str(dest.with_suffix(".jpg"))], check=True)
        return True
    if dest.with_suffix(".jpg").exists():
        return True
    if not src or not Path(src).exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", "scale=720:-2", "-q:v", "4",
                    str(dest.with_suffix(".jpg"))], check=True)
    return True


def media_tile(brand, asset, url="", kind="video", src=None, platform="Instagram") -> str:
    """The preview for a best-post tile: the local video/image (made from src if missing), else a link tile."""
    A = f"../../{brand}/assets"
    if asset and make_asset(src, HERE / brand / "assets" / asset, kind):
        if kind == "video":
            return f'<video src="{A}/{asset}.mp4" poster="{A}/{asset}.jpg" controls playsinline preload="none"></video>'
        return f'<img class="pv" src="{A}/{asset}.jpg" alt="" loading="lazy">'
    gap(f"{brand}: no preview file for {asset or url} (link tile shown)")
    return (f'<a class="thumb blank" href="{E(url)}" target="_blank" rel="noopener"><span class="play"></span>'
            f'<span class="lbl">Preview not available · open on {platform}</span></a>')


def micro_cr(asset):
    x = MICRO_COST.get(asset)
    if not x:
        gap(f"microdramas: no credit entry for {asset} (add it to MICRO_COST from its run.json)")
    return x["calls"] if x else None


def build_microdramas():
    stats = json.loads((HERE / "microdramas/stats.json").read_text())
    fol = stats.pop("_followers", {})
    fol = {"instagram": live_fol("instagram", "microdramas.ai", fol.get("instagram")),
           "tiktok": live_fol("tiktok", "microdramas.ai", fol.get("tiktok"))}
    apply_live(stats.values())
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
          {media_tile("microdramas", p["asset"], (s.get("url") or "").split("?")[0], "video", p.get("src"), P["name"])}
          <span class="rank">#{r} · {E(p['series'])} · {E(p['label'].split(' · ')[0])}</span>
          <span class="h">{E(p['tease'])}</span>
          <span class="m">{n(s['views'])} views · {n(s.get('likes') or 0)} likes · {n(s.get('shares') or 0)} shares · {n(s.get('saves') or 0)} saves · {cr_txt(micro_cr(p['asset']))}{link}</span>
        </div>"""

        c = known([micro_cr(p["asset"]) for p in live])
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
    <div class="cost">{tiles([("Credits / post, avg", avg(c)), ("Median", med(c)), ("Range", rng(c)),
                              ("Credits / 1K views", n(cpk))])}</div>
    <p class="note">Same file on both platforms, so posting it here as well adds 0 credits. Credits / 1K views = full cost of the
      {len(c)} live episodes ÷ {P['name']} views alone (if {P['name']} carried the whole cost).</p>
    <div class="visits"><a class="visit" href="{P['url']}" target="_blank" rel="noopener"><span class="plat">{P['name']}</span> @microdramas.ai →</a></div>
  </article>"""

    eng_all = ((overall["likes"] + overall["comments"] + overall["shares"] + overall["saves"]) / overall["views"]
               if overall["views"] else 0)
    live_c = known([micro_cr(a) for a in live_eps])
    cpk_all = sum(live_c) / (overall["views"] / 1000) if overall["views"] else 0

    series = microdrama_series()
    _mp = sorted(micro_posts(), key=lambda p: str(p["when"]))
    series_titles = list(dict.fromkeys(p["series"] for p in _mp))
    _eps = {}
    for p in _mp:
        _eps.setdefault(p["series"], set()).add(p["asset"])
    complete = [t for t in series_titles if len(_eps[t]) >= 8]
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
  <div class="eyebrow"><a href="../">← All brands</a> · Picsart Social · brand summary</div>
  <div class="hero">
    <img src="{A}/logo-microdramas.jpg" alt="microdramas.ai profile picture">
    <div>
      <h1>Microdramas</h1>
      <div class="handle">@microdramas.ai · Instagram + TikTok</div>
    </div>
  </div>
  <p class="dek">Serialized AI drama: 26–57 second episodes with spoken dialogue and cliffhanger endings, new parts most days.
    The first four series were shot like a 1990s Hollywood film; since Oct 21 (ONE YEAR, NO LOVE) a glossy, realistic TV-drama look
    with subtitles on every line. Every frame, voice and cut is made with Picsart AI.</p>

  <div class="sec-label">Key concept</div>
  <div class="card">
    <div class="concept">
      <div><b>Format</b><span>Vertical 9:16 episodes of 8-part series. Each part ends on a question, so viewers come back for the next one.</span></div>
      <div><b>Look</b><span>Series 1–4: 35 mm film, candlelight, satin and tuxedos, rainy streets. Since Oct 21: prime-time TV-drama realism, tight close-ups, burned-in subtitles. Each series has its own cast with fixed faces and voices.</span></div>
      <div><b>Engine</b><span>Keyframes on Nano Banana Pro and Seedream, continuous takes with native dialogue on Seedance 2.5, finished with the Picsart end card.</span></div>
    </div>
    <p class="note">Series so far: {" · ".join(E(t) for t in series_titles)}. {len(live_eps)} episodes live; {len(complete)} series complete ({" · ".join(E(t) for t in complete)}).</p>
  </div>

  <div class="sec-label">Overall</div>
  <div class="card">
    <div class="counts">{tiles([("Platforms", "2"), ("Published", n(overall['pub'])), ("Scheduled", n(overall['sched'])),
                                ("Views", n(overall['views'])), ("Likes", n(overall['likes'])), ("Comments", n(overall['comments'])),
                                ("Shares", n(overall['shares'])), ("Saves", n(overall['saves'])), ("Engagement", f"{eng_all:.1%}")])}</div>
    <div class="sub">Cost · {len(live_eps)} live episodes</div>
    <div class="cost">{tiles([("Credits spent", n(sum(live_c))), ("Avg / episode", avg(live_c)),
                              ("Range", rng(live_c)), ("Credits / 1K views", n(cpk_all))])}</div>
    <p class="note">Published counts posts (one episode on two platforms = 2 posts). Engagement = (likes + comments + shares + saves) / views.
      Credits / 1K views = credits for the live episodes ÷ views on both platforms.</p>
  </div>

  <div class="sec-label">Platforms, by the numbers</div>
{plat_cards}

  <footer>Views, likes and the rest come from Instagram and TikTok through the publishing rail, pulled {NOW:%Y-%m-%d %H:%M} Yerevan
    (platform data last synced {E(synced)} UTC). Posts published in the last few hours still show low numbers. {live_note()} Picsart Social automation project · made with Picsart</footer>
</main>
</body>
</html>
"""
    out = HERE / "summary/microdramas/index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"microdramas summary: live eps {len(live_eps)} {sorted(live_eps)} · {overall} · live credits {sum(live_c)}")
    return dict(brand="Microdramas", slug="microdramas", what="AI drama series", platforms="Instagram, TikTok",
                pub=overall["pub"], sched=overall["sched"], reach=f"{n(overall['views'])} views",
                fol=sum(fol.values()), unit="episode", per=avg(live_c), per_rng=rng(live_c), spent=n(sum(live_c)))


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
# Pinterest: our three pin runs (2026-10-02 x2, 2026-10-20) (dwell-content-runs.md): 70 pins, 185 + 180 = 365 credits,
# confirmed by the balance (5,730 -> 5,545 -> 5,365). 5 credits per image; 3 pins needed one reroll (10).
PIN_RUNS = dict(pins=105, credits=545, per_pin=[5] * 101 + [10] * 4, since="2026-10-03")  # + 2026-10-20 run: 35 pins, 180 cr, 1 reroll

DWELL_FORMAT = {"A": "Before / after", "B": "Statement tour", "C": "Walkthrough reveal", "D": "Variation swap",
                "E": "Trend carousel", "F": "Photo-set carousel", "G": "Colour pairs", "H": "Mouldings"}

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
    fol = {"instagram": live_fol("instagram", "dwell.rooms", fol.get("instagram")),
           "tiktok": live_fol("tiktok", "dwellrooms", fol.get("tiktok"))}
    apply_live(stats.values())
    pin = json.loads((HERE / "dwell/pinterest.json").read_text())
    A = "../../dwell/assets"
    mature_cut = NOW - timedelta(hours=24)

    posts, seen = [], set()
    for ledger, key, asset, kind, slides, label, hook, _desc in dwell_posts():
        for plat in ("instagram", "tiktok"):
            e = ledger.get(f"{key}:{plat}")
            if e:
                seen.add(e["postId"])
                posts.append(dict(platform=plat, postId=e["postId"], when=when_of(e), asset=asset, kind=kind,
                                  label=label, hook=hook, cr=DWELL_COST.get(asset), src=None))
    # batches not on the hand-written list: plan.json + schedule.json + each post's run.json
    for led in sorted((OUT / "dwell").glob("*/schedule.json")):
        d = led.parent
        items = {it["slug"]: it for it in sched(d / "plan.json").get("items", [])}
        for k, e in json.loads(led.read_text()).items():
            if e.get("postId") in seen or ":" not in k:
                continue
            slug, plat = k.rsplit(":", 1)
            it = items.get(slug, {})
            kind = "car" if it.get("kind") == "carousel" else "reel"
            run = sched(d / slug / "run.json")
            cr = run.get("credits_total", run.get("total_credits"))
            asset = f"dwell-{d.name}-{slug}" + ("-slide1" if kind == "car" else "")
            src = d / slug / (f"{slug}.mp4" if kind == "reel" else "carousel/slide1.jpg")
            posts.append(dict(platform=plat, postId=e["postId"], when=when_of(e), asset=asset, kind=kind,
                              label=DWELL_FORMAT.get(it.get("format"), "Post"), hook=(it.get("caption") or "").split("\n")[0],
                              cr=cr, src=src))
            if cr is None:
                gap(f"dwell: no credit total in {d.name}/{slug}/run.json")

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
            media = media_tile("dwell", p["asset"] if p["kind"] == "reel" or p["asset"].endswith("-slide1")
                               else f'{p["asset"]}-slide1', (s.get("url") or "").split("?")[0],
                               "video" if p["kind"] == "reel" else "image", p["src"], P["name"])
            link = f' · <a href="{E(s["url"].split("?")[0])}" target="_blank" rel="noopener">open on {P["name"]} →</a>' if s.get("url") else ""
            best += f"""<div class="ex">
          {media}
          <span class="rank">#{r} · {E(p['label'])}</span>
          <span class="h">{E(p['hook'])}</span>
          <span class="m">{n(s['views'])} views · {n(s.get('likes') or 0)} likes · {n(s.get('shares') or 0)} shares · {n(s.get('saves') or 0)} saves · {cr_txt(p['cr'])}{link}</span>
        </div>"""
        c = known([p["cr"] for p in live])
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
                      [("Credits / post, avg", avg(c)), ("Median", med(c)), ("Range", rng(c)),
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

    live_c = known(list({p["asset"]: p["cr"] for p in posts if p["when"] and p["when"] <= NOW}.values()))
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
  <div class="eyebrow"><a href="../">← All brands</a> · Picsart Social · brand summary</div>
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
    <p class="note">Live on 3 of Dwell's 4 platforms; the X account is not posting and is left out. Instagram and TikTok posted two a day
      Oct 12–24 (four a day Oct 21–24); the next week of reels (Oct 23–29) is planned but not built, waiting for a credit top-up, so
      nothing is scheduled there after Oct 24. Pinterest keeps five pins a day through Oct 28. A design review on Oct 23 asked for
      readable, higher-contrast titles, a font per style, more realistic video, a clearer logo and before/afters of the same room;
      those fixes go into the next batch.</p>
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
    {live_note()} Picsart Social automation project · made with Picsart</footer>
</main>
</body>
</html>
"""
    out = HERE / "summary/dwell/index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"dwell summary: IG/TT live {overall['pub']} sched {overall['sched']} views {reach_views} · pins {len(pins)} impr {imp}")
    return dict(brand="Dwell", slug="dwell", what="Luxury interiors", platforms="Instagram, TikTok, Pinterest",
                pub=overall["pub"] + len(pins), sched=overall["sched"] + pin["scheduled"],
                reach=f"{n(reach_views)} views<br><span class='nt'>+ {n(imp)} pin impressions</span>", fol=sum(fol.values()) + pin["followers"],
                unit="reel or carousel", per=avg(live_c), per_rng=rng(live_c),
                spent=n(sum(live_c) + PIN_RUNS["credits"]),
                note=f"pins {PIN_RUNS['credits'] / PIN_RUNS['pins']:.1f} each")


# Reelo "tiny worlds" videos we made (Tigran's format, Gemini 3 Pro Image stills + Veo 3.1 + ElevenLabs voice),
# from context/reports/reelo-content-runs.md. Most are balance-confirmed (balance before -> after = the
# logged credits; the six of 2026-10-09 sum to the batch drop 4,724 -> 2,183). Matched to posts by caption.
REELO_COST = {  # slug: (caption keyword, credits)
    "tiny-carousel-restore": ("tiny carousel", 426), "tiny-fire-station-restore": ("fire station", 421),
    "tiny-bicycle-shop-restore": ("bicycle shop", 421), "tiny-bathhouse-restore": ("bathhouse", 426),
    "tiny-gas-station-restore": ("gas station", 421), "tiny-cable-car-restore": ("cable car", 416),
    "tiny-apiary-restore": ("apiary", 421), "tiny-bowling-alley-restore": ("bowling", 436),
    "tiny-ferris-wheel-restore": ("ferris wheel", 426), "tiny-tram-depot-restore": ("tram depot", 416),
    "tiny-laundromat-restore": ("laundromat", 426), "tiny-bell-tower-restore": ("bell tower", 431),
    "tiny-mine-entrance-restore": ("tiny mine", 416), "tiny-puppet-theatre-restore": ("puppet theatre", 426),
}
REELO_SINCE = "2026-10-03"  # our first post; earlier posts came from the earlier pipeline, no cost log here
CARTOON_COST = [110, 110, 110, 120]  # the first four cartoon reels, out/reelo/2026-10-19-*/run.json

REELO_PLATFORM = {
    "instagram": dict(name="Instagram", fmt="Reels", handle="@reelo.hq", url="https://www.instagram.com/reelo.hq/",
                      concept="Cartoon reels since Oct 17: four a day (12:00, 13:30, 18:00, 19:30 Yerevan), two a day Oct 21–22, four a day again since Oct 23; the same files as TikTok. Cartoons: median {c_med} "
                              "views per reel so far, against {t_med} for the tiny-world videos (Oct 3–16)."),
    "tiktok": dict(name="TikTok", fmt="Videos", handle="@reelostudio", url="https://www.tiktok.com/@reelostudio",
                   concept="The same reels at the same times. Cartoons: median {c_med} views per reel so far, against "
                           "{t_med} for the tiny-world videos (Oct 3–16). Each caption asks for a one-word comment."),
}


def clean_title(t):
    for cut in (". A new tiny world", " Follow", " Would you try this?", " #", " Made with Picsart", " Here is how",
                " Step by step", " Comment ", " made with Picsart"):
        t = t.split(cut)[0]
    return t.strip().rstrip(".")


def reelo_slug(title):
    t = title.lower()
    return next((s for s, (kw, _) in REELO_COST.items() if kw in t), None)


REELO_OUT = OUT / "reelo"
CARTOON_SRC: dict[str, Path] = {}


def cartoon_ledger():
    """Scheduled cartoon reels: [(when_utc, slug, credits)] from out/reelo/schedule.json + each run.json."""
    rows = {}
    for e in json.loads((REELO_OUT / "schedule.json").read_text()).values():
        # folders are either out/reelo/<date>-<slug>/ or out/reelo/<series>/<slug>/
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", e["dir"])
        d = REELO_OUT / e["dir"]
        if not d.is_dir():
            d = next((x for x in REELO_OUT.glob(f"*/{e['dir']}") if x.is_dir()), d)
        run = sched(d / "run.json")
        cr = run.get("credits")
        cr = cr.get("total") if isinstance(cr, dict) else cr
        if cr is None:
            cr = run.get("credits_quoted")
        if cr is None:
            gap(f"reelo: no credits in {d.relative_to(REELO_OUT)}/run.json")
        rows[slug] = (when_of(e).astimezone(timezone.utc), slug, cr)
        CARTOON_SRC[f"cartoon-{slug}"] = d / f"{slug}.mp4"
    return list(rows.values())


def reelo_post_info(p, cartoons):
    """(format, asset, credits) for a feed post: our cartoon, our tiny world, or an earlier post (no cost log)."""
    pub = datetime.fromisoformat(p["publishedAt"].replace("Z", "+00:00"))
    for when, slug, cr in cartoons:
        if abs((pub - when).total_seconds()) <= 10 * 60:
            return "cartoon", f"cartoon-{slug}", cr
    slug = reelo_slug(p["title"]) if p["publishedAt"] >= REELO_SINCE else None
    if slug:
        return "tiny world", slug, REELO_COST[slug][1]
    return "earlier", None, None


def build_reelo():
    feed = json.loads((HERE / "reelo/feed.json").read_text())
    apply_live(feed["instagram"]["posts"])
    apply_live(feed["tiktok"]["posts"])
    feed["instagram"]["followers"] = live_fol("instagram", "reelo.hq", feed["instagram"]["followers"])
    feed["tiktok"]["followers"] = live_fol("tiktok", "reelostudio", feed["tiktok"]["followers"])
    A = "../../reelo/assets"
    mature_cut = (NOW - timedelta(hours=24)).astimezone(timezone.utc).isoformat()
    cartoons = cartoon_ledger()
    spent = {}
    cards, ov = "", dict(pub=0, sched=0, views=0, likes=0, comments=0, shares=0, saves=0, fol=0)
    for plat, P in REELO_PLATFORM.items():
        F = feed[plat]
        ps = F["posts"]
        tot = {k: sum(int(p.get(k) or 0) for p in ps) for k in ("views", "likes", "comments", "shares", "saves")}
        acts = tot["likes"] + tot["comments"] + tot["shares"] + tot["saves"]
        ov["pub"] += len(ps)
        ov["sched"] += F["scheduled"]
        ov["fol"] += F["followers"]
        for k in tot:
            ov[k] += tot[k]
        mat = [p for p in ps if (p["publishedAt"] or "") <= mature_cut]
        v = [int(p["views"]) for p in mat]
        lk = [int(p["likes"]) for p in mat]
        er = [(p["likes"] + p["comments"] + p["shares"] + p["saves"]) / p["views"] for p in mat if p["views"]]
        info = {p["url"]: reelo_post_info(p, cartoons) for p in ps}
        cart = [p for p in ps if info[p["url"]][0] == "cartoon"]
        tiny = [p for p in ps if info[p["url"]][0] == "tiny world"]
        cart_m = [p["views"] for p in cart]
        c_med = n(median(cart_m)) if cart_m else "n/a"
        t_med = n(median([p["views"] for p in tiny])) if tiny else "n/a"
        best = ""
        for r, p in enumerate(sorted(ps, key=lambda p: (p["views"], p["likes"]), reverse=True)[:3], start=1):
            fmt_, asset, cr = info[p["url"]]
            posted = datetime.fromisoformat(p["publishedAt"].replace("Z", "+00:00")).astimezone(YEREVAN)
            if asset and make_asset(CARTOON_SRC.get(asset), HERE / "reelo/assets" / asset, "video"):
                media = f'<video src="{A}/{asset}.mp4" poster="{A}/{asset}.jpg" controls playsinline preload="none"></video>'
            elif p.get("asset"):
                media = f'<a class="thumb" href="{E(p["url"])}" target="_blank" rel="noopener"><img class="pv vid" src="{A}/{p["asset"]}" alt="" loading="lazy"><span class="play"></span></a>'
            else:
                media = f'<a class="thumb blank" href="{E(p["url"])}" target="_blank" rel="noopener"><span class="play"></span><span class="lbl">Preview not available · watch on {P["name"]}</span></a>'
            cost = f" · {n(cr)} credits" if cr else ""
            best += f"""<div class="ex">
          {media}
          <span class="rank">#{r} · {fmt_} · {posted:%b %-d}</span>
          <span class="h">{E(clean_title(p['title']))}</span>
          <span class="m">{n(p['views'])} views · {n(p['likes'])} likes · {n(p['shares'])} shares · {n(p['saves'])} saves{cost} · <a href="{E(p['url'])}" target="_blank" rel="noopener">open on {P['name']} →</a></span>
        </div>"""
        cc = known([info[p["url"]][2] for p in cart])
        spent.update({info[p["url"]][1]: info[p["url"]][2] for p in cart + tiny if info[p["url"]][2] is not None})
        tc = known([info[p["url"]][2] for p in tiny])
        cv = sum(int(p["views"]) for p in cart)
        P = dict(P, concept=P["concept"].format(c_med=c_med, t_med=t_med))
        cards += card(plat, P,
                      [("Published", n(len(ps))), ("Scheduled", n(F["scheduled"])), ("Followers", n(F["followers"])),
                       ("Views", n(tot["views"])), ("Likes", n(tot["likes"])), ("Comments", n(tot["comments"])),
                       ("Shares", n(tot["shares"])), ("Saves", n(tot["saves"])),
                       ("Engagement", f"{acts / tot['views']:.1%}" if tot["views"] else "n/a")],
                      f"Per post · {len(mat)} posts live 24 h or more",
                      [("Views range", rng(v)), ("Median views", n(median(v)) if v else "n/a"), ("Likes range", rng(lk)),
                       ("Engagement range", rng(er, lambda x: f"{x:.1%}")),
                       ("Cartoon median (all so far)", c_med), ("Tiny world median", t_med)],
                      "", best,
                      [("Cartoon reel, avg", n(mean(cc)) if cc else "n/a"), ("Cartoon range", rng(cc)),
                       ("Tiny world, avg", n(mean(tc)) if tc else "n/a"),
                       ("Credits / 1K views, cartoons", n(sum(cc) / (cv / 1000)) if cv else "n/a")],
                      f"Cartoon reels: {rng(cc)} credits each by call prices (keyframe 5, plus 5 per reroll, and the 15 s "
                      f"Seedance reel 105); {len(cc)} live here. Tiny-world videos: {rng(tc)} each, {len(tc)} posted Oct 3–16, "
                      f"11 of 14 confirmed by the account balance. Same file on Instagram and TikTok, so the second post adds "
                      f"0 credits. Credits / 1K views = the live cartoons' cost ÷ their {P['name']} views alone. Posts before "
                      f"Oct 3 came from the earlier pipeline and have no cost log here.")

    eng = (ov["likes"] + ov["comments"] + ov["shares"] + ov["saves"]) / ov["views"] if ov["views"] else 0
    first = min(p["publishedAt"] for pl in REELO_PLATFORM for p in feed[pl]["posts"])[:10]
    synced = max((p.get("lastUpdated") or "" for pl in REELO_PLATFORM for p in feed[pl]["posts"]), default="")[:16]
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reelo Brand Summary</title>
<meta name="description" content="Reelo: concept, live platforms (Instagram, TikTok), numbers, best posts and credits per post.">
<style>{CSS}
  .ex .thumb{{position:relative; display:block}}
  .ex img.pv.vid{{width:100%; aspect-ratio:9/16; object-fit:cover; border-radius:10px; display:block; border:1px solid var(--line)}}
  .ex .thumb.blank{{aspect-ratio:9/16; border-radius:10px; border:1px solid var(--line); background:var(--surface-2); background-image:linear-gradient(160deg,var(--accent-soft),var(--surface-2)); font-family:var(--mono); font-size:.62rem; color:var(--accent-ink)}}
  .ex .thumb.blank .lbl{{position:absolute; left:0; right:0; bottom:12px; text-align:center; padding:0 8px}}
  .ex .play{{position:absolute; inset:0; display:grid; place-items:center}}
  .ex .play::before{{content:""; width:40px; height:40px; border-radius:50%; background:rgba(0,0,0,.55)}}
  .ex .play::after{{content:""; position:absolute; border-style:solid; border-width:8px 0 8px 13px; border-color:transparent transparent transparent #fff; margin-left:3px}}
</style>
</head>
<body>
<main class="wrap">
  <div class="eyebrow"><a href="../">← All brands</a> · Picsart Social · brand summary</div>
  <div class="hero">
    <img src="{A}/logo-reelo.jpg" alt="Reelo profile picture">
    <div>
      <h1>Reelo</h1>
      <div class="handle">@reelo.hq · @reelostudio · Instagram + TikTok</div>
    </div>
  </div>
  <p class="dek">15-second Pixar-style family cartoons since Oct 17, four a day (two a day on Oct 21–22). 30 reels for Oct 28 to Nov 11 were built on Oct 23;
    the queue is scheduled through Nov 1. Before that (from {first}): AI-trend
    explainers, then "tiny worlds", a ruined miniature place restored in one video a day.</p>

  <div class="sec-label">Key concept</div>
  <div class="card">
    <div class="concept">
      <div><b>Now · cartoons</b><span>15 s micro-stories about a toddler, a parent and a pet, told with faces and sound effects, no dialogue. A cast of 11, shuffled. Four a day at 12:00, 13:30, 18:00 and 19:30 Yerevan; the queue runs to Nov 1 and the next build needs a credit top-up.</span></div>
      <div><b>Before · tiny worlds</b><span>25–28 s restorations of a ruined miniature with a voiceover, one a day until Oct 16.</span></div>
      <div><b>Engine</b><span>Cartoons: Gemini 3 Pro Image keyframe, Seedance 2.5 with native sound. Tiny worlds: Gemini 3 Pro Image, Veo 3.1, ElevenLabs.</span></div>
    </div>
    <p class="note">Reelo's Pinterest and X accounts are not posting and are left out.</p>
  </div>

  <div class="sec-label">Overall</div>
  <div class="card">
    <div class="counts">{tiles([("Platforms", "2"), ("Published", n(ov['pub'])), ("Scheduled", n(ov['sched'])),
                                ("Views", n(ov['views'])), ("Likes", n(ov['likes'])), ("Comments", n(ov['comments'])),
                                ("Shares", n(ov['shares'])), ("Saves", n(ov['saves'])), ("Engagement", f"{eng:.1%}"),
                                ("Followers", n(ov['fol']))])}</div>
    <p class="note">Published counts posts (one video on two platforms = 2 posts). Engagement = (likes + comments + shares + saves) / views.</p>
  </div>

  <div class="sec-label">Platforms, by the numbers</div>
{cards}

  <footer>Numbers come from Instagram and TikTok through the publishing rail, pulled {E(feed['pulledAt'])} Yerevan
    (platform data last synced {E(synced)} UTC). Posts published in the last few hours still show low numbers.
    {live_note()} Picsart Social automation project · made with Picsart</footer>
</main>
</body>
</html>
"""
    out = HERE / "summary/reelo/index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"reelo summary: {ov}")
    cart_c = [v for k, v in spent.items() if k.startswith("cartoon-")]
    return dict(brand="Reelo", slug="reelo", what="Family cartoons", platforms="Instagram, TikTok",
                pub=ov["pub"], sched=ov["sched"], reach=f"{n(ov['views'])} views", fol=ov["fol"],
                unit="cartoon reel", per=n(mean(cart_c)) if cart_c else "n/a", per_rng=rng(cart_c),
                spent=n(sum(spent.values())), note="tiny-world videos before Oct 17: 416–436 each")


# Faceless (Instagram only). Credits per post from each week's assets/manifest.json, every asset assigned to
# the post that first used it (rerolls included). Week totals: W41 211; W42 128 (balance 5,257 -> 5,130);
# W43 186 (balance 5,130 -> 4,944). Tutorials and "does it pay?" posts reuse earlier assets: 0 extra credits.
FACELESS_COST = {
    "2026-W41/1_mon_persona_gustave": 43, "2026-W41/2_tue_microdrama_ep1": 67, "2026-W41/3_wed_microdrama_tutorial": 0,
    "2026-W41/4_thu_product_ad": 18, "2026-W41/5_fri_mascot_pip": 38, "2026-W41/6_sat_ai_singer_noor": 42,
    "2026-W41/7_sun_money_truth_animals": 3,
    "2026-W42/1_mon_mascot_tutorial": 3, "2026-W42/2_tue_pets_phone_call": 37, "2026-W42/3_wed_pet_tutorial": 0,
    "2026-W42/4_thu_80s_tape_service": 32, "2026-W42/5_fri_halloween_merch": 29.5, "2026-W42/6_sat_merch_tutorial": 0,
    "2026-W42/7_sun_money_truth_sleep": 26,
    "2026-W43/1_mon_ai_model_mara": 50, "2026-W43/2_tue_does_it_pay_ai_models": 8, "2026-W43/3_wed_gord_ep1": 48,
    "2026-W43/4_thu_ai_horror_trailer": 47, "2026-W43/5_fri_trailer_tutorial": 0, "2026-W43/6_sat_one_app_gord_ep2": 33,
    "2026-W43/7_sun_does_it_pay_ai_films": 0,
}
FACELESS_KIND = {"tutorial": "How-to", "money_truth": "Does it pay?", "does_it_pay": "Does it pay?", "one_app": "One app"}


def faceless_kind(slug):
    return next((v for k, v in FACELESS_KIND.items() if k in slug), "Build it")


def build_faceless():
    stats = json.loads((HERE / "faceless/stats.json").read_text())
    fol = stats.pop("_followers", {})
    fol = {"instagram": live_fol("instagram", "faceless_monetization", fol.get("instagram"))}
    apply_live(stats.values())
    A = "../../faceless/assets"
    weeks = OUT.parent / "projects/faceless-lab/weeks"
    posts = []
    for w in sorted(weeks.glob("2026-W*")):
        plan = json.loads((w / "plan.json").read_text())
        led = json.loads((w / "instagram.json").read_text()) if (w / "instagram.json").exists() else {}
        for it in plan["items"]:
            e = next((v for k, v in led.items() if k.split(":")[0] == it["slug"]), None)
            if e:
                car = it.get("pillar") == "carousel"
                posts.append(dict(key=f"{w.name}/{it['slug']}", asset=f"{w.name}-{it['slug']}", when=when_of(e),
                                  postId=e["postId"], caption=it["caption"].split("\n")[0], kind=faceless_kind(it["slug"]),
                                  media="image" if car else "video",
                                  src=w / it["files"][0] if it.get("files") else None,
                                  cr=FACELESS_COST.get(f"{w.name}/{it['slug']}")))
    live = [p for p in posts if p["when"] <= NOW]
    soon = [p for p in posts if p["when"] > NOW]
    num = [(p, stats[p["postId"]]) for p in live if (stats.get(p["postId"]) or {}).get("views") is not None]
    synced_n = len(num)
    for p in live:
        if p["cr"] is None:
            gap(f"faceless: no credit entry for {p['key']} (add it to FACELESS_COST from the week's assets/manifest.json)")
    c = known([p["cr"] for p in live])
    cf = lambda x: f"{x:g}"  # noqa: E731
    paid = [x for x in c if x]

    if num:
        ranked = sorted(num, key=lambda ps: (ps[1].get("views") or 0, ps[1].get("likes") or 0), reverse=True)[:3]
        best_label = "3 best posts on Instagram · by views"
    else:
        ranked = [(p, {}) for p in sorted(live, key=lambda p: p["when"], reverse=True)[:3]]
        best_label = "3 latest posts on Instagram · best-by-views appears once Instagram numbers sync"
    best = ""
    for r, (p, st) in enumerate(ranked, start=1):
        m = ("" if not st else f"{n(st['views'])} views · " if st.get("likes") is None else
             f"{n(st['views'])} views · {n(st.get('likes') or 0)} likes · {n(st.get('saves') or 0)} saves · ")
        link = (f' · <a href="{E(st["url"].split("?")[0])}" target="_blank" rel="noopener">open on Instagram →</a>'
                if st.get("url") else "")
        best += f"""<div class="ex">
          {media_tile("faceless", p["asset"], (st.get("url") or "").split("?")[0], p["media"], p["src"])}
          <span class="rank">{'#' + str(r) + ' · ' if num else ''}{E(p['kind'])} · {p['when']:%b %-d}</span>
          <span class="h">{E(p['caption'])}</span>
          <span class="m">{m}{cr_txt(p['cr'], cf)}{link}</span>
        </div>"""

    eng_known = any(s.get("likes") is not None for _, s in num)
    tot = {k: sum(int(s.get(k) or 0) for _, s in num) for k in ("views", "likes", "comments", "shares", "saves")}
    if num and eng_known:
        nums = [("Views", n(tot["views"])), ("Likes", n(tot["likes"])), ("Comments", n(tot["comments"])),
                ("Shares", n(tot["shares"])), ("Saves", n(tot["saves"]))]
        sync_note = ""
    elif num:
        vv = [int(s["views"]) for _, s in num]
        nums = [("Views", n(tot["views"])), ("Median views", med(vv)), ("Views range", rng(vv)),
                ("Likes", "not synced"), ("Saves", "not synced")]
        sync_note = (f'<p class="note">Views for {len(num)} of the {len(live)} live posts are read live from the public '
                     f'Instagram profile (the newest reels; carousels and older posts are not shown there). Likes and saves '
                     f'have not reached the publishing rail yet, so they are left out rather than shown as 0.</p>')
    else:
        nums = [("Views", "not synced"), ("Likes", "not synced"), ("Saves", "not synced")]
        sync_note = (f'<p class="note">Instagram numbers for this account have not reached the publishing rail yet: '
                     f'it returns "sync pending" for all {len(live)} live posts, so views, likes and saves are shown as '
                     f'not synced rather than as 0.</p>')
    P = dict(name="Instagram", fmt="Reels", handle="@faceless_monetization",
             url="https://www.instagram.com/faceless_monetization/",
             concept="One reel a day at 18:00 Yerevan. From the Oct 26 week every post is a Price Tag reel: one of our "
                     "finished videos, what buyers pay for that kind of video, then the receipt of tools and credits. "
                     "Earlier posts (Oct 5–25) were build-it reels, tutorials and does-it-pay breakdowns. On keyword "
                     "posts, commenting the word sends the exact prompts by DM.")
    cards = card("instagram", P,
                 [("Published", n(len(live))), ("Scheduled", n(len(soon))), ("Followers", n(fol.get("instagram", 0)))] + nums,
                 "Per post", [("Posts with views", f"{synced_n} of {len(live)}")],
                 sync_note, best,
                 [("Credits / post, avg", cf(round(mean(c), 1))), ("Median", cf(median(c))), ("Range", rng(c, cf)),
                  ("Avg, new builds only", cf(round(mean(paid), 1)))],
                 f"From each week's asset log, rerolls included; the logs add up to the account balance drop "
                 f"(W42 128 vs 127, W43 186 vs 186). {len(c) - len(paid)} of the {len(c)} live posts are how-tos or "
                 f"money breakdowns that reuse an earlier post's assets, so they cost 0 extra credits. The receipt card "
                 f"inside a post can be a few credits lower, because it leaves out rerolls.")
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Faceless Brand Summary</title>
<meta name="description" content="Faceless Monetization: concept, live platform (Instagram), numbers, posts and credits per post.">
<style>{CSS}</style>
</head>
<body>
<main class="wrap">
  <div class="eyebrow"><a href="../">← All brands</a> · Picsart Social · brand summary</div>
  <div class="hero">
    <img src="{A}/logo-faceless.jpg" alt="Faceless Monetization profile picture">
    <div>
      <h1>Faceless</h1>
      <div class="handle">@faceless_monetization · Instagram</div>
    </div>
  </div>
  <p class="dek">Price Tag reels: a finished AI video, what people pay for that kind of video, and the receipt of what it
    cost to make in Picsart. Every post since the Oct 26 week; live since Oct 5 with build-it and how-to posts.</p>

  <div class="sec-label">Key concept</div>
  <div class="card">
    <div class="concept">
      <div><b>Price Tag (now)</b><span>Opens on one of our finished videos (a Reelo cartoon, a microdrama episode or a Dwell interior), then a sourced "people pay $X for this", then the receipt: tools and credits. 3 cartoons, 2 dramas, 2 interiors a week.</span></div>
      <div><b>Comment for the prompts</b><span>Three posts a week carry a keyword; commenting it sends the exact steps in Picsart by DM. Prices are public listings with the month, never income promises.</span></div>
      <div><b>Engine</b><span>No new generation: the videos come from the other brands, so a Price Tag post costs 0 extra credits. Before Oct 26: Nano Banana Pro and 2 images, Kling V3 clips, ElevenLabs and Lyria audio.</span></div>
    </div>
    <p class="note">Live on Instagram only; other platforms are not connected yet.</p>
  </div>

  <div class="sec-label">Overall</div>
  <div class="card">
    <div class="counts">{tiles([("Platforms", "1"), ("Published", n(len(live))), ("Scheduled", n(len(soon))),
                                ("Followers", n(fol.get("instagram", 0)))])}</div>
    <div class="sub">Cost · {len(live)} live posts</div>
    <div class="cost">{tiles([("Credits spent", cf(sum(c))), ("Avg / post", cf(round(mean(c), 1))), ("Range", rng(c, cf))])}</div>
  </div>

  <div class="sec-label">Platform, by the numbers</div>
{cards.replace('3 best posts on Instagram · by views', best_label)}

  <footer>Counts and followers come from the publishing rail, pulled {NOW:%Y-%m-%d %H:%M} Yerevan.
    {live_note()} Picsart Social automation project · made with Picsart</footer>
</main>
</body>
</html>
"""
    out = HERE / "summary/faceless/index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"faceless summary: live {len(live)} sched {len(soon)} synced {synced_n} credits {sum(c)}")
    return dict(brand="Faceless", slug="faceless", what="Price Tag reels: what AI videos sell for", platforms="Instagram",
                pub=len(live), sched=len(soon), reach=f"{n(tot['views'])} views" if num else "not synced yet", fol=fol.get("instagram", 0),
                unit="post", per=cf(round(mean(c), 1)), per_rng=rng(c, cf), spent=cf(sum(c)),
                note=f"new builds {cf(round(mean(paid), 1))}")


LISTED = OUT.parent / "projects/listed"
LISTED_PILLAR = {"flip": "Before / after", "tutorial": "Tutorial", "carousel": "Carousel"}


def listed_thread_credits(slug):
    """Sum of the credits each connector call in the thread logged (rejected takes included)."""
    f = LISTED / "threads" / slug / "thread.json"
    return sum(x.get("credits") or 0 for x in json.loads(f.read_text())["credits"]) if f.exists() else 0


def build_listed():
    stats = json.loads((HERE / "listed/stats.json").read_text())
    fol = stats.pop("_followers", {})
    fol = {"instagram": live_fol("instagram", "listed.hq", fol.get("instagram"))}
    apply_live(stats.values())
    A = "../../listed/assets"
    posts = []
    for w in sorted((LISTED / "plans").glob("2026-*")):
        plan = json.loads((w / "plan.json").read_text())
        led = json.loads((w / "instagram.json").read_text()) if (w / "instagram.json").exists() else {}
        for it in plan["items"]:
            e = led.get(f"{it['slug']}:{it['pillar']}")
            if not e:
                continue
            # a thread's credits sit on its before/after post; the tutorial and the carousel reuse those assets
            cr = listed_thread_credits(it["slug"]) if it["pillar"] == "flip" else 0
            asset = (f"{it['slug']}-p1_before_after" if it["pillar"] == "flip" else
                     f"{it['slug']}-p2_tutorial" if it["pillar"] == "tutorial" else f"{it['slug']}-slide1")
            src = (LISTED / "threads" / it["slug"] / "out" / ("p1_before_after.mp4" if it["pillar"] == "flip" else "p2_tutorial.mp4")
                   if it["pillar"] != "carousel" else w / "carousel" / "slide_01.jpg")
            posts.append(dict(slug=it["slug"], pillar=it["pillar"], when=when_of(e), postId=e["postId"], credits=cr, src=src,
                              asset=asset, caption=it["caption"].split(" Comment FIX")[0].split(" The exact path:")[0].split("\n")[0]))
    live = [p for p in posts if p["when"] <= NOW]
    soon = [p for p in posts if p["when"] > NOW]
    num = [(p, stats[p["postId"]]) for p in live if (stats.get(p["postId"]) or {}).get("views") is not None]
    c = [p["credits"] for p in live]
    threads_live = [p["credits"] for p in live if p["pillar"] == "flip"]
    cf = lambda x: f"{x:g}"  # noqa: E731

    if num:
        ranked = sorted(num, key=lambda ps: (ps[1].get("views") or 0, ps[1].get("likes") or 0), reverse=True)[:3]
        best_label = "3 best posts on Instagram · by views"
    else:
        ranked = [(p, {}) for p in sorted(live, key=lambda p: p["when"], reverse=True)[:3]]
        best_label = "3 latest posts on Instagram · best-by-views appears once Instagram numbers sync"
    best = ""
    for r, (p, st) in enumerate(ranked, start=1):
        media = media_tile("listed", p["asset"], (st.get("url") or "").split("?")[0],
                           "image" if p["pillar"] == "carousel" else "video", p["src"])
        m = ("" if not st else f"{n(st['views'])} views · " if st.get("likes") is None else
             f"{n(st['views'])} views · {n(st.get('likes') or 0)} likes · {n(st.get('saves') or 0)} saves · ")
        link = (f' · <a href="{E(st["url"].split("?")[0])}" target="_blank" rel="noopener">open on Instagram →</a>'
                if st.get("url") else "")
        best += f"""<div class="ex">
          {media}
          <span class="rank">{'#' + str(r) + ' · ' if num else ''}{LISTED_PILLAR[p['pillar']]} · {p['when']:%b %-d}</span>
          <span class="h">{E(p['caption'])}</span>
          <span class="m">{m}{cf(p['credits'])} credits{link}</span>
        </div>"""

    eng_known = any(s.get("likes") is not None for _, s in num)
    tot = {k: sum(int(s.get(k) or 0) for _, s in num) for k in ("views", "likes", "comments", "shares", "saves")}
    if num and eng_known:
        nums = [("Views", n(tot["views"])), ("Likes", n(tot["likes"])), ("Comments", n(tot["comments"])),
                ("Shares", n(tot["shares"])), ("Saves", n(tot["saves"]))]
        sync_note = ""
    elif num:
        vv = [int(s["views"]) for _, s in num]
        nums = [("Views", n(tot["views"])), ("Median views", med(vv)), ("Views range", rng(vv)),
                ("Likes", "not synced"), ("Saves", "not synced")]
        sync_note = (f'<p class="note">Views for {len(num)} of the {len(live)} live posts are read live from the public '
                     f'Instagram profile (the newest reels; carousels and older posts are not shown there). Likes and saves '
                     f'have not reached the publishing rail yet, so they are left out rather than shown as 0.</p>')
    else:
        nums = [("Views", "not synced"), ("Likes", "not synced"), ("Saves", "not synced")]
        sync_note = (f'<p class="note">Instagram numbers for this account have not reached the publishing rail yet: '
                     f'it returns "sync pending" for all {len(live)} live posts, so views, likes and saves are shown as '
                     f'not synced rather than as 0.</p>')
    P = dict(name="Instagram", fmt="Reels + carousels", handle="@listed.hq", url="https://www.instagram.com/listed.hq/",
             concept="One post a day at 18:00 Yerevan, in threads: a product's before/after, the next day its tutorial "
                     "with the exact path in Picsart, and a Sunday carousel of the week's three products. Every post ends "
                     "on \"Comment FIX\", and the comment sends the step-by-step by DM with a button to open Picsart.")
    cards = card("instagram", P,
                 [("Published", n(len(live))), ("Scheduled", n(len(soon))), ("Followers", n(fol.get("instagram", 0)))] + nums,
                 "Per post", [("Posts with views", f"{len(num)} of {len(live)}")],
                 sync_note, best,
                 [("Credits / post, avg", cf(round(mean(c), 1))), ("Median", cf(median(c))), ("Range", rng(c, cf)),
                  ("Credits / product", f"{cf(round(mean(threads_live), 1))} avg")],
                 f"From each product thread's call log, rejected takes included. One product = 2 posts: the "
                 f"before/after carries the thread's credits ({rng(threads_live, cf)} per product, {len(threads_live)} "
                 f"products live) and the tutorial reuses the same files; the Sunday carousel reuses all three. The "
                 f"one-off sound kit (54 credits of music and effects shared by every video) is not in the per-post figure.")
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Listed Brand Summary</title>
<meta name="description" content="Listed: concept, live platform (Instagram), numbers, posts and credits per post.">
<style>{CSS}
  .ex img.pv{{width:100%; aspect-ratio:9/16; object-fit:cover; border-radius:10px; display:block; border:1px solid var(--line)}}
</style>
</head>
<body>
<main class="wrap">
  <div class="eyebrow"><a href="../">← All brands</a> · Picsart Social · brand summary</div>
  <div class="hero">
    <img src="{A}/logo-listed.jpg" alt="Listed profile picture">
    <div>
      <h1>Listed</h1>
      <div class="handle">@listed.hq · Instagram</div>
    </div>
  </div>
  <p class="dek">For online sellers: make your next product listing look better, using the photo you already have.
    Every fix is made in Picsart, with the exact path shown. Live since Oct 5.</p>

  <div class="sec-label">Key concept</div>
  <div class="card">
    <div class="concept">
      <div><b>Before / after</b><span>An everyday phone-style photo of a product (AI-made), then the listing photo or short video ad made from it.</span></div>
      <div><b>Tutorial</b><span>Result first, then every step with the exact tool path on picsart.com/create. Sunday: a carousel of the week.</span></div>
      <div><b>Seller jobs</b><span>Fix, Stage, Multiply, Animate, Create: Remove Background, Edit with AI, Relight Studio, AI Replace, AI Playground.</span></div>
    </div>
    <p class="note">Live on Instagram only; other platforms are not connected yet. The daily post ran Oct 5–25 (seven products, three
      weekly carousels); nothing is scheduled after Oct 25 until the next product threads are approved.</p>
  </div>

  <div class="sec-label">Overall</div>
  <div class="card">
    <div class="counts">{tiles([("Platforms", "1"), ("Published", n(len(live))), ("Scheduled", n(len(soon))),
                                ("Followers", n(fol.get("instagram", 0)))])}</div>
    <div class="sub">Cost · {len(live)} live posts, {len(threads_live)} products</div>
    <div class="cost">{tiles([("Credits spent", cf(sum(c))), ("Avg / post", cf(round(mean(c), 1))),
                              ("Avg / product", cf(round(mean(threads_live), 1))), ("Range / product", rng(threads_live, cf))])}</div>
  </div>

  <div class="sec-label">Platform, by the numbers</div>
{cards.replace('3 best posts on Instagram · by views', best_label)}

  <footer>Counts and followers come from the publishing rail, pulled {NOW:%Y-%m-%d %H:%M} Yerevan.
    {live_note()} Picsart Social automation project · made with Picsart</footer>
</main>
</body>
</html>
"""
    out = HERE / "summary/listed/index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"listed summary: live {len(live)} sched {len(soon)} synced {len(num)} credits {sum(c)} threads {threads_live}")
    return dict(brand="Listed", slug="listed", what="Product photos for sellers", platforms="Instagram",
                pub=len(live), sched=len(soon), reach=f"{n(tot['views'])} views" if num else "not synced yet", fol=fol.get("instagram", 0),
                unit="product (2 posts)", per=cf(round(mean(threads_live), 1)), per_rng=rng(threads_live, cf),
                spent=cf(sum(c)))


def build_all():
    order = ["microdramas", "dwell", "reelo", "faceless", "listed"]
    sums = [globals()[f"build_{b}"]() for b in order]
    for x in sums:
        a = ALL_IN.get(x["slug"])
        if not a:
            continue
        x["per"] = f"up to {a['per_max']:,}"
        lo = str(x.get("per_rng", "")).split("–")[0]
        if lo and lo[0].isdigit():
            rest = str(x["per_rng"]).split(" · ", 1)
            x["per_rng"] = f"{lo}–{a['per_max']:,}" + (f" · {rest[1]}" if len(rest) > 1 else "")
        x["spent"] = (f"{a['total']:,.0f}<br><span class='nt'>incl. {a['waste']:,.0f} on remakes, fixes, tests</span>")
        f = HERE / f"summary/{x['slug']}/index.html"
        if f.exists():
            h = f.read_text()
            if "Cost · all in" not in h:
                h = h.replace('<div class="sec-label">Platform', allin_card(x["slug"]) + '<div class="sec-label">Platform', 1)
                f.write_text(h)
    rows, nav = "", ""
    for x in sums:
        nav += f'<a class="visit" href="{x["slug"]}/">{x["brand"]} →</a>'
        rows += (f"<tr><td><a href='{x['slug']}/'><b>{x['brand']} →</b></a><br><span class='nt'>{E(x['what'])}</span></td>"
                 f"<td>{x['platforms']}</td><td class='r'>{n(x['pub'])}</td>"
                 f"<td class='r'>{x['reach']}</td><td class='r'>{n(x['fol'])}</td>"
                 f"<td class='r'><b>{x['per']}</b> per {x['unit']}<br><span class='nt'>range {x['per_rng']}"
                 f"{' · ' + x['note'] if x.get('note') else ''}</span></td><td class='r'>{x['spent']}</td></tr>")
    pub, fol = sum(x["pub"] for x in sums), sum(x["fol"] for x in sums)
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Picsart Social Brands</title>
<meta name="description" content="All Picsart Social brands on one page: concept, live platforms, numbers, best posts and credits per post.">
<style>{CSS}
  .wrap{{max-width:1000px}}
  .tbl{{overflow-x:auto; -webkit-overflow-scrolling:touch}}
  table{{min-width:680px}} th,td{{vertical-align:top}}
  td.r b{{font-weight:700}} td .nt{{color:var(--faint); font-size:.72rem}} td a{{color:var(--accent-ink)}}
  .nav{{display:flex; flex-wrap:wrap; gap:.5rem; margin-top:1.2rem}}
</style>
</head>
<body>
<main class="wrap" id="top">
  <div class="eyebrow">Picsart Social · all brands</div>
  <h1 style="margin-top:.7rem">Picsart Social brands</h1>
  <p class="dek">Five brands, each run as an automated content system made with Picsart AI. For every brand: the concept,
    the platforms it is live on, its numbers, its best posts and what one post costs in credits. Open a brand
    for its full one-pager.</p>
  <div class="nav">{nav}</div>

  <div class="sec-label">Overview</div>
  <div class="card">
    <div class="counts">{tiles([("Brands", "5"), ("Posts published", n(pub)), ("Followers", n(fol))])}</div>
    <div class="tbl"><table>
      <thead><tr><th>Brand</th><th>Live on</th><th class="r">Published</th><th class="r">Reach</th>
        <th class="r">Followers</th><th class="r">Credits per post</th><th class="r">Credits spent</th></tr></thead>
      <tbody>{rows}</tbody>
    </table></div>
    <p class="note">Published counts posts (one video on two platforms = 2 posts). Credits per post = the most one post has
      cost, rerolls included (the same file on a second platform costs 0). Credits spent = everything the brand has used,
      posted or not: remakes, fixes, tests, deleted posts and work never posted included, each run with every reroll,
      retry and fix it logged. Faceless and Listed likes and saves are not synced from
      Instagram yet.</p>
  </div>

  <footer>Numbers come from Instagram, TikTok and Pinterest through the publishing rail, pulled {NOW:%Y-%m-%d %H:%M} Yerevan.
    Posts published in the last few hours still show low numbers. {live_note()} Picsart Social automation project · made with Picsart</footer>
</main>
</body>
</html>
"""
    out = HERE / "summary/index.html"
    out.write_text(page)
    print(f"all brands: {out.relative_to(HERE)} · {pub} posts · {fol} followers")
    for g in GAPS:
        print(f"GAP {g}")
    return GAPS


if __name__ == "__main__":
    import sys
    for b in sys.argv[1:] or ["all"]:
        globals()[f"build_{b}"]()
