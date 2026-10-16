#!/usr/bin/env python3
"""Build the two brand showcase pages: microdramas/index.html and dwell/index.html.

Inputs (read only, nothing generated here):
  ../out/microdrama/<series>/schedule.json, ../out/dwell/<batch>/schedule.json  -> status + dates
  <brand>/stats.json  -> per-post Instagram + TikTok numbers (bin/showcase_stats.py writes it)
  <brand>/assets/     -> 720p mp4s, posters, carousel slides, key art, profile pictures

Refresh:  bin/with-env python3 bin/showcase_stats.py && python3 onepagers/build_showcase.py
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE.parent / "out"
YEREVAN = timezone(timedelta(hours=4))
NOW = datetime.now(YEREVAN)
PLAT = {"instagram": "Instagram", "tiktok": "TikTok"}


def sched(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def when_of(entry):
    if not entry:
        return None
    dt = datetime.fromisoformat(entry["when"])
    return (dt if dt.tzinfo else dt.replace(tzinfo=YEREVAN)).astimezone(YEREVAN)


def fmt(dt):
    return dt.strftime("%b %-d · %H:%M")


def n(v):
    return "–" if v in (None, "") else f"{int(v):,}"


def status(ig, tt):
    w = when_of(ig) or when_of(tt)
    if w is None:
        return "made", "Made, not scheduled yet"
    plat = " + ".join(p for p, e in (("Instagram", ig), ("TikTok", tt)) if e)
    return ("live", f"Live · {plat} · {fmt(w)}") if w <= NOW else ("soon", f"Scheduled · {plat} · {fmt(w)}")


def stat_rows(stats, ig, tt):
    rows = ""
    for name, e in (("instagram", ig), ("tiktok", tt)):
        s = stats.get(e["postId"]) if e else None
        if not s or s.get("views") is None:
            continue
        link = f'<a href="{s["url"]}" target="_blank" rel="noopener">open</a>' if s.get("url") else ""
        rows += (f'<div class="stat"><i>{PLAT[name]}</i><b>{n(s["views"])}</b> views · <b>{n(s["likes"])}</b> likes · '
                 f'<b>{n(s["saves"])}</b> saves · <b>{n(s["shares"])}</b> shares · <b>{n(s["comments"])}</b> comments {link}</div>')
    return f'<div class="stats">{rows}</div>' if rows else ""


def video_card(asset, label, title, desc, st, stats, ig, tt):
    return f"""      <article class="post">
        <video src="assets/{asset}.mp4" poster="assets/{asset}.jpg" controls playsinline preload="none"></video>
        <span class="t">{label}</span>
        <span class="h">{title}</span>
        <span class="d">{desc}</span>
        <span class="st {st[0]}">{st[1]}</span>
{stat_rows(stats, ig, tt)}      </article>
"""


def carousel_card(prefix, slides, label, title, desc, st, stats, ig, tt):
    imgs = "".join(f'<img src="assets/{prefix}-slide{i}.jpg" alt="" loading="lazy">' for i in range(1, slides + 1))
    return f"""      <article class="post">
        <div class="car">{imgs}</div>
        <span class="t">{label} · {slides} slides · swipe</span>
        <span class="h">{title}</span>
        <span class="d">{desc}</span>
        <span class="st {st[0]}">{st[1]}</span>
{stat_rows(stats, ig, tt)}      </article>
"""


def totals(stats, keys_platforms):
    """Sum views/likes/saves/shares per platform over the given (postId) list."""
    t = {"instagram": {"views": 0, "likes": 0, "saves": 0, "shares": 0, "posts": 0},
         "tiktok": {"views": 0, "likes": 0, "saves": 0, "shares": 0, "posts": 0}}
    for pid in keys_platforms:
        s = stats.get(pid)
        if not s or s.get("views") is None:
            continue
        p = t[s["platform"]]
        p["posts"] += 1
        for k in ("views", "likes", "saves", "shares"):
            p[k] += int(s.get(k) or 0)
    return t


CSS = """
  @font-face{font-family:"Gilroy";font-weight:400;src:url("https://pastatic.picsart.com/cms-pastatic/d018cb40-40a8-4efa-a202-947285ae8329.woff2") format("woff2");font-display:swap}
  @font-face{font-family:"Gilroy";font-weight:600;src:url("https://pastatic.picsart.com/cms-pastatic/eae6e1ea-9319-406c-a3de-00431f8f03f4.woff2") format("woff2");font-display:swap}
  @font-face{font-family:"Gilroy";font-weight:700;src:url("https://pastatic.picsart.com/cms-pastatic/0ea441d6-d0d4-4236-b649-67a987887865.woff2") format("woff2");font-display:swap}
  :root{--ink:#141414;--paper:#f7f4ee;--muted:#6b6b70;--line:#e3ded5;--card:#fff;--accent:#5C4636;--ok:#1d6b3a;--okbg:#e7f3ea;--warn:#8a5a00;--warnbg:#fbf1dc;--off:#555;--offbg:#ebe8e2}
  *{box-sizing:border-box}
  body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 "Gilroy",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
  a{color:var(--accent)}
  .wrap{max-width:1160px;margin:0 auto;padding:0 20px}
  header{padding:44px 0 28px}
  .profile{display:grid;grid-template-columns:112px 1fr auto;gap:24px;align-items:start;background:var(--card);border:1px solid var(--line);border-radius:18px;padding:24px}
  .profile img{width:112px;height:112px;border-radius:50%;display:block;object-fit:cover}
  .profile h1{margin:0;font-size:30px;line-height:1.1;letter-spacing:-.02em}
  .handle{font-weight:600;color:var(--muted);margin-top:4px}
  .bio{margin:10px 0 0;font-size:15px}
  .who{margin:8px 0 0;color:var(--muted);font-size:14.5px;max-width:640px}
  .status{display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:700;padding:4px 10px;border-radius:999px;margin-left:8px;vertical-align:middle;color:var(--ok);background:var(--okbg)}
  .status::before{content:"";width:8px;height:8px;border-radius:50%;background:currentColor}
  .actions{display:flex;flex-direction:column;gap:8px}
  .btn{display:inline-block;text-align:center;font-weight:700;font-size:14px;text-decoration:none;padding:10px 16px;border-radius:10px;white-space:nowrap}
  .btn.primary{background:var(--ink);color:#fff}
  .btn.ghost{border:1px solid var(--line);color:var(--ink);background:var(--card)}
  .kpis{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:14px}
  .kpi{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
  .kpi h3{margin:0 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
  .kpi .row{display:grid;grid-template-columns:repeat(5,1fr);gap:8px}
  .kpi .row div b{display:block;font-size:22px;line-height:1.1;letter-spacing:-.01em}
  .kpi .row div span{font-size:11.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;font-weight:600}
  .summary{color:var(--muted);font-size:14.5px;margin:14px 0 0}
  .series{margin-top:44px;padding-top:36px;border-top:1px solid var(--line)}
  .show{display:grid;grid-template-columns:300px 1fr;gap:28px;align-items:start}
  .show img{width:100%;border-radius:14px;display:block;border:1px solid var(--line)}
  .show h2{margin:0;font-size:30px;letter-spacing:-.02em;line-height:1.05}
  .show .meta{color:var(--muted);font-size:14px;margin:6px 0 0}
  .show .brief{margin:14px 0 0;font-size:16px;max-width:700px}
  .show .counts{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
  .show .counts span{font-size:13px;font-weight:700;padding:5px 11px;border-radius:999px}
  .posts{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:22px}
  .post{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:10px;display:flex;flex-direction:column;gap:7px}
  .post video{width:100%;aspect-ratio:9/16;border-radius:10px;display:block;background:#111;object-fit:cover}
  .car{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;gap:6px;border-radius:10px;aspect-ratio:4/5;background:#111;scrollbar-width:none}
  .car::-webkit-scrollbar{display:none}
  .car img{flex:0 0 100%;width:100%;height:100%;object-fit:cover;scroll-snap-align:start;border-radius:10px}
  .post .t{font-size:12px;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.06em;margin-top:2px}
  .post .h{font-weight:700;font-size:15px;line-height:1.3}
  .post .d{font-size:13px;color:var(--muted)}
  .post .st{font-size:12px;font-weight:700;padding:3px 8px;border-radius:999px;align-self:start;margin-top:auto}
  .live{color:var(--ok);background:var(--okbg)}
  .soon{color:var(--warn);background:var(--warnbg)}
  .made{color:var(--off);background:var(--offbg)}
  .stats{display:flex;flex-direction:column;gap:4px;font-size:12.5px;color:var(--muted);border-top:1px solid var(--line);padding-top:8px}
  .stat i{font-style:normal;font-weight:700;color:var(--ink);display:inline-block;min-width:66px}
  .stat b{color:var(--ink)}
  .stat a{margin-left:4px;font-weight:600}
  .note{color:var(--muted);font-size:14px;margin-top:36px}
  footer{border-top:1px solid var(--line);padding:18px 0 48px;color:var(--muted);font-size:13.5px}
  @media (max-width:980px){.posts{grid-template-columns:repeat(3,1fr)}.show{grid-template-columns:220px 1fr}}
  @media (max-width:760px){
    .profile{grid-template-columns:72px 1fr}.profile img{width:72px;height:72px}
    .actions{grid-column:1/-1;flex-direction:row;flex-wrap:wrap}
    .kpis{grid-template-columns:1fr}.kpi .row{grid-template-columns:repeat(3,1fr)}
    .show{grid-template-columns:1fr}.show img{max-width:320px}
    .posts{grid-template-columns:1fr 1fr}
  }
  @media (max-width:460px){.posts{grid-template-columns:1fr}}
"""


def kpi_block(name, followers, t):
    return f"""    <div class="kpi"><h3>{name}</h3><div class="row">
      <div><b>{n(followers)}</b><span>followers</span></div>
      <div><b>{t['posts']}</b><span>posts live</span></div>
      <div><b>{n(t['views'])}</b><span>views</span></div>
      <div><b>{n(t['likes'])}</b><span>likes</span></div>
      <div><b>{n(t['saves'])}</b><span>saves</span></div>
    </div></div>
"""


def page(title, desc, body, synced):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<style>{CSS}</style>
</head>
<body>
<main><div class="wrap">
{body}
  <p class="note">Numbers come from the broker's analytics for each post (Instagram and TikTok), last synced {synced} UTC, follower counts from {NOW.strftime("%b %-d")}. Statuses and dates come from the scheduling ledgers. Every post is labelled as AI on the platform and every caption ends with "made with Picsart". Back to <a href="../">the concept pages</a>.</p>
</div></main>
<footer><div class="wrap">Picsart Social automation project · October 2026 · made with Picsart</div></footer>
</body>
</html>
"""


def microdrama_series() -> list[dict]:
    """The four microdrama series and their episodes (asset slug, label, tease, description)."""
    return [
        dict(slug="speak-now", title="SPEAK NOW", genre="Romance · 1990s Manhattan", art="keyart-speak-now",
             brief="At a 1990s Manhattan church wedding the bride objects to her own marriage, and every guest has a secret about why. One rainy afternoon and the morning after, in eight parts: hidden letters, a husband nobody mentioned, a sister nobody knew about, and a ring bought forty years ago.",
             key=lambda i: f"speak-now-part-{i}", total=8, episodes=[
                 ("speak-now-1", "Part 1 · 28 s", "Everyone looked at the wrong woman.", "A church wedding. The bride objects to her own marriage, a soaked stranger walks in, and the groom's mother says one word: \"Finally.\""),
                 ("speak-now-2", "Part 2 · The Letters · 26 s", "Twelve letters. Not one arrived.", "Luca wrote every month for a year. Claire never got a single letter. Her bridesmaid goes pale."),
                 ("speak-now-3", "Part 3 · Second Time · 28 s", "Second time's the charm… if she says yes.", "The letters were hidden by the bridesmaid who loves the groom. Claire leaves with Luca; Julian walks into the rain toward Vivienne."),
                 ("speak-now-4", "Part 4 · Tomorrow · 29 s", "She said ask me tomorrow. She didn't say what he'd find.", "A thirteenth letter, hidden a year ago. Julian kneels on Vivienne's stoop. Across the street a man says: \"You're still my wife.\""),
                 ("speak-now-5", "Part 5 · The Husband · 28 s", "He waited all night. She waited a whole year.", "Mateo crosses the street. Vivienne's letter is finally read. He will let her go on one condition: \"Say you never loved me.\""),
                 ("speak-now-6", "Part 6 · The Sister · 26 s", "Everyone has a secret. Hers was in the same family all along.", "Vivienne can't say it. Rosalind tells Claire why she helped: \"Because I'm your sister.\" That night, the ring disappears."),
                 ("speak-now-7", "Part 7 · The Ring · 29 s", "Forty years ago he bought a ring. She said no. He never asked again.", "Sloane returns the ring to the priest. It was never Julian's: Harold bought it for Eleanor forty years ago. Mateo signs the papers."),
                 ("speak-now-8", "Part 8 · Speak Now. Again. · 30 s", "Forty years ago she said no. Today he asked again.", "Season finale. Same church, a new wedding, \"If anyone objects…\" Eleanor stands, turns to Harold: \"Ask me again.\""),
             ]),
        dict(slug="the-last-bite", title="THE LAST BITE", genre="Gothic romance · a modern city at night", art="keyart-last-bite",
             brief="A young woman survives a vampire attack and starts remembering murders from eight centuries before her birth. The immortal who protects her, the friend who swears she is still human and the Regent who hunts her are all afraid of the same thing: what she remembers next.",
             key=lambda i: f"last-bite-part-{i}", total=8, episodes=[
                 ("last-bite-1", "Part 1 · The Reflection · 45 s", "She survived the attack. Her reflection didn't.", "Elara washes pink water from her face. Her reflection keeps staring after she turns away. The phone: \"Don't let them see your eyes.\""),
                 ("last-bite-2", "Part 2 · Someone Else's Death · 39 s", "The knock didn't come from the door.", "One drop of blood and she is running through a candlelit castle as a terrified woman, eight centuries ago. The dead woman's face is hers."),
                 ("last-bite-3", "Part 3 · The Man Who Knows Her · 52 s", "He caught the blade with his bare hand. And the cut closed.", "Damian under the streetlamp names the attacker and offers to teach her. \"How do you know my name?\" \"Because I watched you die the first time.\""),
                 ("last-bite-4", "Part 4 · The Council · 57 s", "An entire council of immortals just knelt to her. And she doesn't know why.", "Damian brings her to the candlelit hall. The Regent's ring drops and rings on the marble; every vampire kneels. \"The first mother has returned.\""),
                 ("last-bite-5", "Part 5 · The Missing Years · 53 s", "The warning on the back of the photograph is in her best friend's handwriting.", "Mara's photograph has changed: a new woman stands beside Elara's mother, the woman from the visions. Mara locks the door and picks up the phone: \"She's remembering. What do I do now?\""),
                 ("last-bite-6", "Part 6 · The First Betrayal · 46 s", "He put a blade through her heart. She remembers asking him to.", "Damian confesses he helped imprison the woman Elara used to be. She takes his hand and sees it: his blade, her heart. \"If you remember why, you'll beg me to do it again.\""),
             ]),
        dict(slug="family-portrait", title="FAMILY PORTRAIT", genre="Family drama · Connecticut, autumn 1995", art="keyart-family-portrait",
             brief="A lakeside house, a perfect family, and a seven-year-old who keeps drawing a fifth figure outside the garden gate: a lady with yellow hair who waves at his little sister. She is the children's mother, declared drowned five years ago by the grandmother who paid her to disappear. The wife who raised them has known for three years.",
             key=lambda i: f"family-portrait-p{i}:instagram", total=8, episodes=[
                 ("family-portrait-1", "Part 1 · The Drawing · 49 s", "Every family portrait has someone standing just outside the frame.", "Sunday breakfast. Oliver's drawing has a fifth figure. Rosie waves at the empty gate; a green ribbon on the post. In the car Constance unfolds the drawing: \"She came back.\""),
                 ("family-portrait-2", "Part 2 · The School Gate · 40 s", "Rosie knows the lady at the gate. Margot doesn't. Yet.", "A blonde in a camel coat across the street at pickup. That night in the study: the wedding album, one page torn out, a photograph of Theo with another woman and a newborn."),
                 ("family-portrait-3", "Part 3 · The First Wife · 40 s", "Her name was Laurel. They never found her. So who is standing at the gate?", "The dock at dusk. Theo: \"She drowned the autumn Rosie was born.\" At the gate, in the rain, Margot and Laurel face to face: \"You have my ribbon.\""),
                 ("family-portrait-4", "Part 4 · Sunday Lunch · 38 s", "Sunday lunch at Constance's. Candles, pearls, the perfect family. Then the door opens.", "Laurel walks in. Rosie: \"The lady!\" Constance's glass stops halfway. \"It's been five years, Constance.\" Theo stands: \"Mother. What did you do?\""),
                 ("family-portrait-5", "Part 5 · The Deal · 42 s", "\"A dead mother can't leave twice.\"", "The terrace, the same night. Constance finally tells the truth: the coat on the dock, the boat adrift, the clinic in Switzerland, the money. Margot, listening at the French doors, closes her eyes. She is not surprised."),
                 ("family-portrait-6", "Part 6 · The Letter · 39 s", "\"I let you love me.\"", "The next night, Margot's turn: a letter came from Switzerland three years ago. She read it. She burned it. Rosie at the bedroom door: \"Mommy, is the lady my other mommy?\""),
             ]),
        dict(slug="remember-me", title="REMEMBER ME?", genre="Glow-up revenge · Newport, 1996", art="keyart-remember-me",
             brief="Carmela Vane, the plain heiress everyone laughed at, vanishes after a cruel bet at a charity ball and returns a year later with a new face and a new name. The man who laughed loudest falls for her, his fiancée who bullied her starts to suspect, and the only person who recognises her is the one who was kind.",
             key=lambda i: f"remember-me-p{i}:instagram", total=8, episodes=[
                 ("remember-me-1", "Part 1 · The Bet · 39 s", "He danced with her for a hundred dollars.", "Dorian asks Carmela to dance; mid-waltz he lets go of her hand and the room laughs. Bianca hands him the banknote. In the rain, Gabriel puts his jacket on her shoulders without a word."),
                 ("remember-me-2", "Part 2 · The Mirror · 41 s", "She asked for a new face. She got a new name.", "The clinic. Weeks pass in cuts. The bandages come off and Dr Ash holds up the hand mirror. \"What is your name now?\" \"Carmen.\""),
                 ("remember-me-3", "Part 3 · The Return · 38 s", "One year later. Same ball. Nobody knows her. One man looks at the pearls.", "Carmen enters in oxblood velvet; every head turns; Dorian abandons Bianca mid-sentence. Across the room Gabriel looks not at her face but at the pearls."),
                 ("remember-me-4", "Part 4 · The Dinner · 43 s", "He told her the funniest story he knew. She let him pour.", "Dorian brags about \"a girl at a ball once, a bet, you should have seen her\". Carmen smiles. Under the table her hand is shaking; she steadies it on the pearls."),
                 ("remember-me-5", "Part 5 · The Photograph · 43 s", "He never asked who she was. She never had to tell him.", "Bianca digs through the society pages and finds the 1994 photo: a plain girl in the same two-strand pearls. On the terrace Carmen tells Gabriel: \"Someone gave me a jacket once.\" He says nothing. He knows."),
                 ("remember-me-6", "Part 6 · The Ring · 44 s", "He asked in front of everyone. One man left the table.", "At the Whitlock family dinner Dorian breaks with Bianca and proposes to Carmen in front of everyone. She says yes. Gabriel leaves the table. Bianca, at the door, is holding the photo."),
             ]),
    ]


# =====================================================================================
# MICRODRAMAS
# =====================================================================================
def build_microdramas():
    stats = json.loads((HERE / "microdramas/stats.json").read_text())
    fol = stats.pop("_followers", {})
    led = {s: sched(OUT / f"microdrama/{s}/schedule.json") for s in ("speak-now", "the-last-bite", "family-portrait", "remember-me")}

    SERIES = microdrama_series()

    all_ids, sections = [], ""
    grand = {"live": 0, "soon": 0, "made": 0, "eps": 0}
    for s in SERIES:
        L = led[s["slug"]]
        cards, counts = "", {"live": 0, "soon": 0, "made": 0}
        for i, (asset, label, tease, desc) in enumerate(s["episodes"], start=1):
            k = s["key"](i)
            ig = L.get(k)
            tt = L.get(k.replace(":instagram", "") + ":tiktok")
            st = status(ig, tt)
            counts[st[0]] += 1
            for e in (ig, tt):
                if e:
                    all_ids.append(e["postId"])
            cards += video_card(asset, label, tease, desc, st, stats, ig, tt)
        for k_ in counts:
            grand[k_] += counts[k_]
        grand["eps"] += len(s["episodes"])
        made = len(s["episodes"])
        pills = (f'<span class="live">{counts["live"]} live</span>'
                 + (f'<span class="soon">{counts["soon"]} scheduled</span>' if counts["soon"] else "")
                 + (f'<span class="made">{counts["made"]} made, not scheduled</span>' if counts["made"] else ""))
        sections += f"""
  <section class="series" id="{s['slug']}">
    <div class="show">
      <img src="assets/{s['art']}.jpg" alt="{s['title']} key art">
      <div>
        <h2>{s['title']}</h2>
        <p class="meta">{s['genre']} · {made} of {s['total']} parts made{' · season complete' if made == s['total'] else ''}</p>
        <p class="brief">{s['brief']}</p>
        <div class="counts">{pills}</div>
      </div>
    </div>
    <div class="posts">
{cards}    </div>
  </section>
"""

    t = totals(stats, all_ids)
    synced = max((s.get("lastUpdated") or "" for s in stats.values()), default="n/a")
    body = f"""<header>
  <div class="profile">
    <img src="assets/logo-microdramas.jpg" alt="microdramas.ai profile picture">
    <div>
      <h1>Microdramas · AI love stories <span class="status">Live on Instagram + TikTok</span></h1>
      <div class="handle">@microdramas.ai</div>
      <p class="bio">Tiny love stories, big 90s drama 🎬&nbsp; New part every week. An official Picsart channel, made with Picsart AI.</p>
      <p class="who">Serialized AI microdramas shot like a 1990s film: one scene, one twist, 30 to 60 seconds per part. Four series so far, each with its own cast. Every part goes to Instagram and TikTok at the same time.</p>
    </div>
    <div class="actions">
      <a class="btn primary" href="https://www.instagram.com/microdramas.ai/" target="_blank" rel="noopener">Open on Instagram</a>
      <a class="btn ghost" href="https://www.tiktok.com/@microdramas.ai" target="_blank" rel="noopener">Open on TikTok</a>
    </div>
  </div>
  <div class="kpis">
{kpi_block("Instagram", fol.get("instagram"), t["instagram"])}{kpi_block("TikTok", fol.get("tiktok"), t["tiktok"])}  </div>
  <p class="summary">4 series · {grand['eps']} parts made · {grand['live']} live · {grand['soon']} scheduled · {grand['made']} made but not scheduled yet. Channel opened Oct 13.</p>
</header>
{sections}"""
    (HERE / "microdramas/index.html").write_text(page(
        "Microdramas", "@microdramas.ai: four AI microdrama series, every part with its status and Instagram + TikTok numbers.", body, synced))
    print(f"microdramas: {grand}, IG {t['instagram']}, TT {t['tiktok']}")


# =====================================================================================
# DWELL
# =====================================================================================
def dwell_posts() -> list[tuple]:
    """Dwell IG + TikTok posts: (ledger, key, asset, kind, slides, label, hook, description)."""
    w42, w43 = sched(OUT / "dwell/2026-W42/schedule.json"), sched(OUT / "dwell/2026-W43/schedule.json")
    cp, pm = sched(OUT / "dwell/colour-pairs-2026-10-14/schedule.json"), sched(OUT / "dwell/power-of-moulding-2026-10-14/schedule.json")
    return [
        (w42, "01-parisian-salon", "dwell-W42-01-parisian-salon", "reel", 0, "Before / after · 19 s", "Some rooms never go out of style.", "Raw plaster to a Parisian salon on one match cut: same walls, same light."),
        (w42, "02-old-world-house", "dwell-W42-02-old-world-house", "reel", 0, "Statement tour · 17 s", "The best homes look collected, not decorated.", "Old books, older paintings and a fire that's always lit."),
        (w42, "03-bedroom-trends-2027", "dwell-W42-03-bedroom-trends-2027", "car", 7, "Trend carousel", "5 bedroom trends we're betting on for 2027.", "Limewash walls, upholstered walls, burgundy accents, sculptural lighting, canopy alcoves."),
        (cp, ".", "dwell-colour-pairs", "reel", 0, "Colour pairs · 21 s", "Same room, 5 colour pairs. Which one would you live with?", "Navy + brass, sage + travertine, bordeaux + bouclé, ivory + black marble, mocha + Calacatta."),
        (pm, ".", "dwell-power-of-moulding", "reel", 0, "Mouldings · 23 s", "The power of moulding. Same rooms, same paint, a completely different level.", "Coffered ceilings, picture-frame panels, fluted pilasters, a marble mantel, Parisian boiserie."),
        (w42, "04-ivory-closet-reveal", "dwell-W42-04-ivory-closet-reveal", "reel", 0, "Walkthrough reveal · 19 s", "Wait for the closet.", "Ivory bouclé, warm brass and a walk-in that glows."),
        (w42, "05-japandi-headboard-swap", "dwell-W42-05-japandi-headboard-swap", "reel", 0, "Variation swap · 15 s", "Same bed, 12 walls. Which one would you choose?", "Oak, stone, clay, walnut: one Japandi bedroom, twelve headboard walls."),
        (w42, "06-mediterranean-villa-set", "dwell-W42-06-mediterranean-villa-set", "car", 8, "Photo-set carousel", "Limewash, travertine and one very old olive tree.", "One Mediterranean villa at golden hour, room by room."),
        (w42, "07-night-penthouse", "dwell-W42-07-night-penthouse", "reel", 0, "Statement tour · 20 s", "This is what quiet money looks like.", "Walnut, black marble and a city that never quite sleeps."),
        (w43, "01-wabi-sabi-spa-bath", "dwell-W43-01-wabi-sabi-spa-bath", "reel", 0, "Before / after · 19 s", "Slow mornings start in the right room.", "A bare bathroom becomes a warm wabi-sabi spa on the beat."),
        (w43, "02-kitchen-trends-2027", "dwell-W43-02-kitchen-trends-2027", "car", 7, "Trend carousel", "5 kitchen trends we're betting on for 2027.", "Five warm kitchens, one trend each."),
        (w43, "03-alpine-chalet", "dwell-W43-03-alpine-chalet", "reel", 0, "Statement tour · 23 s", "Winter is just an excuse to stay in.", "A warm alpine chalet: timber, wool, fire and snow outside."),
        (w43, "04-scandi-fireplace-swap", "dwell-W43-04-scandi-fireplace-swap", "reel", 0, "Variation swap · 15 s", "Same room, 12 fireplaces. Which one would you choose?", "One Scandinavian living room, twelve fireplaces."),
        (w43, "05-midcentury-conversation-pit", "dwell-W43-05-midcentury-conversation-pit", "reel", 0, "Walkthrough reveal · 19 s", "Wait for the step down.", "A mid-century home that ends in a sunken conversation pit."),
        (w43, "06-desert-adobe-set", "dwell-W43-06-desert-adobe-set", "car", 8, "Photo-set carousel", "Rammed earth, warm steel and a sunset every single night.", "One desert adobe home, room by room."),
        (w43, "07-industrial-loft", "dwell-W43-07-industrial-loft", "reel", 0, "Before / after · 18 s", "Every great home starts as a shell.", "A concrete shell becomes a warm industrial loft."),
        (w43, "08-coastal-beach-house", "dwell-W43-08-coastal-beach-house", "reel", 0, "Statement tour · 23 s", "Salt air, linen, nowhere to be.", "A warm coastal beach house, open to the sea."),
        (w43, "09-dining-chandelier-swap", "dwell-W43-09-dining-chandelier-swap", "reel", 0, "Variation swap · 15 s", "Same dining room, 12 chandeliers. Which one would you hang?", "One classic dining room, twelve chandeliers."),
        (w43, "10-living-room-trends-2027", "dwell-W43-10-living-room-trends-2027", "car", 7, "Trend carousel", "5 living room trends we're betting on for 2027.", "Five warm living rooms, one trend each."),
        (w43, "11-tuscan-farmhouse-kitchen", "dwell-W43-11-tuscan-farmhouse-kitchen", "reel", 0, "Before / after · 19 s", "Every kitchen should feel like Sunday.", "A bare room becomes a Tuscan farmhouse kitchen."),
        (w43, "12-art-deco-apartment", "dwell-W43-12-art-deco-apartment", "reel", 0, "Walkthrough reveal · 19 s", "Wait for the living room.", "An art deco apartment, hallway to the big reveal."),
        (w43, "13-attic-bedroom", "dwell-W43-13-attic-bedroom", "reel", 0, "Before / after · 19 s", "Every house has a secret room.", "A dusty attic becomes a cosy bedroom under the roof."),
        (w43, "14-moroccan-riad-set", "dwell-W43-14-moroccan-riad-set", "car", 8, "Photo-set carousel", "Cedar, tadelakt and a courtyard full of light.", "One Moroccan riad, room by room."),
    ]


def build_dwell():
    stats = json.loads((HERE / "dwell/stats.json").read_text())
    fol = stats.pop("_followers", {})
    POSTS = dwell_posts()
    rows = []
    for ledger, key, asset, kind, slides, label, hook, desc in POSTS:
        ig, tt = ledger.get(f"{key}:instagram"), ledger.get(f"{key}:tiktok")
        rows.append((when_of(ig) or NOW + timedelta(days=365), asset, kind, slides, label, hook, desc, ig, tt))
    rows.sort(key=lambda r: r[0])
    cards, counts, ids = "", {"live": 0, "soon": 0, "made": 0}, []
    for _, asset, kind, slides, label, hook, desc, ig, tt in rows:
        st = status(ig, tt)
        counts[st[0]] += 1
        ids += [e["postId"] for e in (ig, tt) if e]
        cards += (video_card if kind == "reel" else lambda a, l, h, d, s, S, i, t_: carousel_card(a, slides, l, h, d, s, S, i, t_))(asset, label, hook, desc, st, stats, ig, tt)
    t = totals(stats, ids)
    synced = max((s.get("lastUpdated") or "" for s in stats.values()), default="n/a")
    body = f"""<header>
  <div class="profile">
    <img src="assets/logo-dwell.jpg" alt="Dwell profile picture">
    <div>
      <h1>Dwell <span class="status">Live on Instagram + TikTok</span></h1>
      <div class="handle">@dwell.rooms · @dwellrooms</div>
      <p class="bio">Empty room → dream room ✨ AI makeovers daily. An official Picsart channel, made with Picsart AI.</p>
      <p class="who">Interiors, decoded. Two posts a day at 18:00 and 21:00 Yerevan on Instagram and TikTok: before/after match cuts, statement tours, walkthrough reveals, variation swaps, colour pairs and trend carousels. Every room is made with Picsart.</p>
    </div>
    <div class="actions">
      <a class="btn primary" href="https://www.instagram.com/dwell.rooms/" target="_blank" rel="noopener">Open on Instagram</a>
      <a class="btn ghost" href="https://www.tiktok.com/@dwellrooms" target="_blank" rel="noopener">Open on TikTok</a>
    </div>
  </div>
  <div class="kpis">
{kpi_block("Instagram", fol.get("instagram"), t["instagram"])}{kpi_block("TikTok", fol.get("tiktok"), t["tiktok"])}  </div>
  <p class="summary">{len(POSTS)} posts built · {counts['live']} live · {counts['soon']} scheduled through Oct 22. Instagram and TikTok restarted Oct 12.</p>
</header>
  <section class="series">
    <h2 style="margin:0;font-size:24px;letter-spacing:-.01em">All posts, in posting order</h2>
    <div class="posts">
{cards}    </div>
  </section>
"""
    (HERE / "dwell/index.html").write_text(page(
        "Dwell", "@dwell.rooms: every Instagram and TikTok post with its status and numbers.", body, synced))
    print(f"dwell: {counts}, IG {t['instagram']}, TT {t['tiktok']}")


if __name__ == "__main__":
    build_microdramas()
    build_dwell()
