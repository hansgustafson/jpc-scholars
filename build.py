#!/usr/bin/env python3
"""Build the JPC Scholars site into _site/.

    python build.py            # the public site (GitHub Pages runs this)
    python build.py --preview  # a copy for previewing as a single artifact

Content lives in site.yml, content/, and cohorts/. Photos go in
assets/images/people/<slug>.jpg (or .png / .webp); anyone without a photo
gets initials instead.
"""
import hashlib
import html
import re
import shutil
import sys
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).parent
OUT = ROOT / "_site"
PREVIEW = "--preview" in sys.argv

SITE = yaml.safe_load((ROOT / "site.yml").read_text(encoding="utf-8"))
HOME = yaml.safe_load((ROOT / "content/home.yml").read_text(encoding="utf-8"))
FAQ = yaml.safe_load((ROOT / "content/faq.yml").read_text(encoding="utf-8"))
COHORTS = sorted(
    (yaml.safe_load(p.read_text(encoding="utf-8")) for p in (ROOT / "cohorts").glob("*.yml")),
    key=lambda c: c["year"],
    reverse=True,
)
BY_YEAR = {c["year"]: c for c in COHORTS}
CSS = (ROOT / "assets/site.css").read_text(encoding="utf-8")

NAV = [("fellowship/", "The Fellowship"), ("apply/", "Apply"), ("scholars/", "Scholars"), ("about/", "About")]
CURRENT = ' aria-current="page"'
EMAIL_RE = re.compile(r"(?<![\w.@/\"':])([\w.+-]+@[\w-]+\.[\w.]+\w)")


def esc(s):
    return html.escape(str(s or ""), quote=True)


def years(y):
    return y.replace("-", "–")


def md(text):
    return markdown.markdown(text or "", extensions=["md_in_html", "attr_list", "sane_lists"])


# Changes whenever any asset changes, so browsers fetch fresh styles and images.
VERSION = hashlib.sha1(b"".join(p.read_bytes() for p in sorted((ROOT / "assets").rglob("*")) if p.is_file())).hexdigest()[:8]


def link(path, depth):
    """Relative link from a page `depth` folders deep to site path `path`."""
    rel = "../" * depth + path
    if path.startswith("assets/"):
        return rel + "?v=" + VERSION
    if PREVIEW and (rel.endswith("/") or rel == ""):
        rel += "index.html"
    return rel or "./"


def front_matter(path):
    raw = (ROOT / path).read_text(encoding="utf-8")
    _, fm, body = raw.split("---", 2)
    return yaml.safe_load(fm), body


# ---------- people ----------

def initials(name):
    words = [w for w in name.split(",")[0].replace(".", " ").split() if w[0].isupper() and len(w) > 1]
    return (words[0][0] + words[-1][0]) if len(words) > 1 else name[:2].upper()


def photo(slug, name, depth, size="lg"):
    for ext in ("jpg", "jpeg", "png", "webp"):
        if (ROOT / f"assets/images/people/{slug}.{ext}").exists():
            src = link(f"assets/images/people/{slug}.{ext}", depth)
            return f'<img class="avatar avatar-{size}" src="{src}" alt="Portrait of {esc(name.split(",")[0])}" width="600" height="600" loading="lazy">'
    return f'<span class="avatar avatar-{size} monogram" aria-hidden="true">{esc(initials(name))}</span>'


def person_block(p, depth):
    parts = [f'<article class="person" id="{esc(p["slug"])}">', photo(p["slug"], p["name"], depth),
             '<div class="person-body">', f'<h3>{esc(p["name"])}</h3>']
    if p.get("position"):
        parts.append(f'<p class="position">{esc(p["position"])}</p>')
    if p.get("quote"):
        parts.append(f'<blockquote class="voice"><p>“{esc(p["quote"].strip())}”</p></blockquote>')
    bio = p.get("bio") or []
    for para in bio:
        parts.append(f"<p>{esc(para)}</p>")
    if not bio:
        parts.append('<p class="muted">Full biography coming soon.</p>')
    facts = []
    if p.get("education"):
        facts.append("<dt>Education</dt>" + "".join(f"<dd>{esc(e)}</dd>" for e in p["education"]))
    if p.get("expertise"):
        facts.append(f"<dt>Fields of expertise</dt><dd>{esc(p['expertise'])}</dd>")
    if facts:
        parts.append('<dl class="facts">' + "".join(facts) + "</dl>")
    parts.append(f'<a class="anchor-link" href="#{esc(p["slug"])}">Link to this profile</a>')
    parts.append("</div></article>")
    return "\n".join(parts)


def names(people):
    return [p["name"].split(",")[0] for p in people]


def join_names(ns):
    return ns[0] if len(ns) == 1 else ", ".join(ns[:-1]) + " and " + ns[-1]


# ---------- call box ----------

def call_box(depth, where="home"):
    call = SITE["call"]
    cohort = BY_YEAR.get(call["cohort"], {})
    ss = cohort.get("senior_scholars") or []
    y = years(call["cohort"])
    status = call.get("status", "upcoming")
    dates = call.get("dates") or []
    rows = "".join(f'<li><span>{esc(d["label"])}</span><span>{esc(d["date"])}</span></li>' for d in dates)
    date_html = f'<ul class="dates">{rows}</ul>' if rows else '<p class="muted">Dates will be posted when the call opens.</p>'
    ss_line = ""
    if ss:
        role = "Senior Scholars-in-Residence" if len(ss) > 1 else "Senior Scholar-in-Residence"
        verb = "will serve" if status != "closed" else "will serve"
        ss_line = f"<p>{esc(join_names(names(ss)))} {verb} as {role} for {y}.</p>"
    if status == "open" and call.get("form_url"):
        head = f"Applications are open for the {y} cohort"
        cta = f'<a class="button" href="{esc(call["form_url"])}">Open the application form</a>'
    elif status == "closed":
        head = f"Applications for {y} are closed"
        cta = '<p class="muted">Selected scholars will be announced on the Scholars page.</p>'
    else:
        head = f"The {y} cohort"
        cta = "<p>The call for applications will be posted here.</p>"
    if where == "home":
        cta += f' <a class="text-link" href="{link("apply/", depth)}">Eligibility and how to apply</a>'
    return f'<section class="callbox" aria-labelledby="call-h"><p class="eyebrow">Next cohort</p><h2 id="call-h">{esc(head)}</h2>{ss_line}{date_html}<div class="callbox-cta">{cta}</div></section>'


# ---------- layout ----------

def page(title, body, depth, active=None, lede=None, hero=None, main_class=""):
    nav = "".join(
        f'<a href="{link(p, depth)}"{CURRENT if p == active else ""}>{esc(t)}</a>' for p, t in NAV
    )
    full_title = SITE["title"] if title is None else f'{title} | {SITE["short_title"]}'
    if PREVIEW and title is None:
        full_title = "JPC Scholars Website"
    head_html = f"""<title>{esc(full_title)}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<meta name="description" content="{esc(SITE['tagline'])}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,400;0,700;1,400&family=Lora:ital,wght@0,500;0,600;1,500&display=swap">
"""
    head_html += f"<style>{CSS}</style>" if PREVIEW else f'<link rel="stylesheet" href="{link("assets/site.css", depth)}">'
    lede_html = f'<p class="lede">{esc(lede)}</p>' if lede else ""
    if hero is None:
        hero = f'<header class="pagehead"><div class="wrap"><h1>{esc(title)}</h1>{lede_html}</div></header>'
    c = SITE["contact"]
    body_html = f"""<a class="skip" href="#main">Skip to content</a>
<div class="masthead"><div class="wrap masthead-row">
<a class="brand" href="{link('', depth)}"><img class="brand-logo" src="{link('assets/images/logos/jpc-st-thomas.png', depth)}" alt="The Jay Phillips Center for Interreligious Studies, University of St. Thomas" width="1280" height="174"><span class="brand-name">Scholars in Interreligious Studies</span></a>
<nav aria-label="Main">{nav}</nav>
</div></div>
{hero}
<main id="main" class="wrap {main_class}">
{body}
</main>
<footer class="sitefoot"><div class="wrap foot-grid">
<div><a href="{esc(c['jpc_url'])}"><img class="foot-logo" src="{link('assets/images/logos/jpc-st-thomas.png', depth)}" alt="The Jay Phillips Center for Interreligious Studies, University of St. Thomas" width="1280" height="174"></a><p>St. Paul, Minnesota</p></div>
<div><p>Director: {esc(c['director_name'])}</p><p>{esc(c['program_email'])}</p><p><a href="{esc(c['jpc_url'])}">stthomas.edu/jpc</a></p></div>
<div><p>In collaboration with the <a href="{esc(c['aiis_url'])}">Association for Interreligious/Interfaith Studies</a></p></div>
</div></footer>"""
    if not PREVIEW:
        body_html = EMAIL_RE.sub(r'<a href="mailto:\1">\1</a>', body_html)
    if PREVIEW and depth == 0 and title is None:
        return head_html + body_html  # the artifact host adds the document skeleton
    return f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n{head_html}</head>\n<body>\n{body_html}\n</body>\n</html>\n'


def write(path, text):
    out = OUT / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def fill_photos(body, depth):
    return re.sub(
        r'<div class="person-photo" data-slug="([^"]+)" data-name="([^"]+)"></div>',
        lambda m: photo(m.group(1), m.group(2), depth),
        body,
    )


# ---------- pages ----------

def build_home():
    d = 0
    cur = BY_YEAR[SITE["current_cohort"]]
    y = years(cur["year"])
    c = SITE["contact"]
    hero = f"""<header class="hero"><div class="wrap">
<p class="eyebrow">University of St. Thomas · St. Paul, Minnesota</p>
<h1>{esc(SITE['title'])}</h1>
<p class="lede">{esc(SITE['tagline'])}</p>
<div class="hero-cta"><a class="button button-light" href="{link('fellowship/', d)}">About the fellowship</a><a class="text-link light" href="{link('apply/', d)}">How to apply</a></div>
</div></header>"""
    gath = "".join(
        f'''<figure class="gathering"><img src="{link('assets/images/photos/' + g['image'], d)}" alt="{esc(g['alt'])}" loading="lazy"><figcaption><h3>{esc(g["title"])}</h3><p>{esc(g["text"])}</p></figcaption></figure>'''
        for g in HOME["gatherings"]
    )
    def card(p):
        return (f'<li><a href="{link("scholars/" + cur["year"] + "/", d)}#{esc(p["slug"])}">{photo(p["slug"], p["name"], d, "sm")}'
                f'<span><strong>{esc(p["name"].split(",")[0])}</strong><span class="muted">{esc(p["position"].split("|")[0].strip())}</span></span></a></li>')
    ss = cur.get("senior_scholars", [])
    body = f"""
<div class="home-grid">
<section class="intro"><h2>A cohort for the field</h2><p>{esc(HOME['intro'])}</p>
<p><a class="text-link" href="{link('fellowship/', d)}">What scholars receive and commit to</a></p></section>
{call_box(d)}
</div>
<section aria-labelledby="g-h"><h2 id="g-h" class="section-title">One year, three gatherings</h2>
<div class="gatherings">{gath}</div></section>
<section class="current" aria-labelledby="cur-h">
<div class="section-head"><h2 id="cur-h">The {y} cohort</h2></div>
<h3 class="roster-label">{esc(cur['senior_scholars_heading'])}</h3>
<ul class="roster roster-senior">{"".join(card(p) for p in ss)}</ul>
<h3 class="roster-label">Scholars</h3>
<ul class="roster">{"".join(card(f) for f in cur.get("fellows", []))}</ul>
<p><a class="text-link" href="{link('scholars/' + cur['year'] + '/', d)}">Read their full profiles</a></p>
</section>
<section class="leader" aria-labelledby="l-h">
{photo("hans-gustafson", "Hans Gustafson", d)}
<div><h2 id="l-h">Program leadership</h2>
<p>{esc(HOME['leadership'])}</p>
<p><a class="text-link" href="{link('about/', d)}#hans-gustafson">About Dr. Gustafson</a></p></div>
</section>
<section class="partners" aria-label="Partners">
<p class="eyebrow">In collaboration with</p>
<div class="partner-logos">
<a href="{esc(c['aiis_url'])}"><img src="{link('assets/images/logos/aiis.jpg', d)}" alt="Association for Interreligious/Interfaith Studies" width="963" height="408"></a>
<a href="{esc(c['jirs_url'])}"><img src="{link('assets/images/logos/jirs.jpg', d)}" alt="Journal of Interreligious Studies" width="640" height="238"></a>
</div></section>
"""
    write("index.html", page(None, body, d, hero=hero))


def build_md_page(src, path, active, extra_top="", extra_bottom=""):
    d = path.count("/")
    fm, body = front_matter(src)
    content = fill_photos(md(body.replace("{{root}}", "../" * d)), d)
    write(path + "index.html", page(fm["title"], extra_top + f'<div class="prose">{content}</div>' + extra_bottom, d, active=active, lede=fm.get("lede")))


def build_apply():
    call = SITE["call"]
    d = 1
    form = ""
    if call.get("status") == "open" and call.get("form_url"):
        form = f'<p><a class="button" href="{esc(call["form_url"])}">Open the application form</a></p>'
    else:
        form = '<p class="muted">The application form will be linked here when the call opens.</p>'
    faq = "".join(f'<details><summary>{esc(item["q"])}</summary><div class="answer">{md(item["a"])}</div></details>' for item in FAQ)
    bottom = f'<section class="faq" aria-labelledby="faq-h"><h2 id="faq-h">Frequently asked questions</h2>{faq}</section>'
    fm, body = front_matter("content/apply.md")
    html_body = md(body).replace("<h3>Questions about your application?</h3>", form + "<h3>Questions about your application?</h3>")
    write("apply/index.html", page(fm["title"], call_box(d, "apply") + f'<div class="prose">{html_body}</div>' + bottom, d, active="apply/", lede=fm.get("lede")))


def cohort_status(year):
    if year == SITE["current_cohort"]:
        return "Current cohort"
    return "Next cohort" if year > SITE["current_cohort"] else "Alumni cohort"


def build_scholars_index():
    d = 1
    cards = []
    for c in COHORTS:
        y = c["year"]
        ss = names(c.get("senior_scholars", []))
        fellows = c.get("fellows", [])
        flist = (
            "<ul class='namelist'>" + "".join(f'<li><a href="{link("scholars/" + y + "/", d)}#{esc(f["slug"])}">{esc(f["name"])}</a></li>' for f in fellows) + "</ul>"
            if fellows else f'<p class="muted">{esc(c.get("fellows_note", ""))}</p>'
        )
        status = cohort_status(y)
        cards.append(f"""<article class="cohort-card{' is-current' if y == SITE['current_cohort'] else ''}">
<p class="tag">{status}</p>
<h2><a href="{link('scholars/' + y + '/', d)}">{years(y)}</a></h2>
<p class="position">{esc(c['senior_scholars_heading'])}: {esc(join_names(ss))}</p>
{flist}
<a class="text-link" href="{link('scholars/' + y + '/', d)}">View the {years(y)} cohort</a>
</article>""")
    body = '<div class="cohort-list">' + "".join(cards) + "</div>"
    write("scholars/index.html", page("Scholars", body, d, active="scholars/",
          lede="Each year’s Senior Scholars-in-Residence and fellows. Every cohort keeps its own page."))


def build_cohort(c):
    y = c["year"]
    d = 2
    others = " ".join(
        f'<a href="{link("scholars/" + o["year"] + "/", d)}"{CURRENT if o["year"] == y else ""}>{years(o["year"])}</a>' for o in COHORTS
    )
    parts = [f'<nav class="yearnav" aria-label="Cohort years"><span>Cohorts:</span> {others}</nav>']
    parts.append(f'<section aria-labelledby="ss-h"><h2 id="ss-h">{esc(c["senior_scholars_heading"])}</h2>')
    parts += [person_block(p, d) for p in c.get("senior_scholars", [])]
    if c.get("senior_scholars_quote"):
        q = c["senior_scholars_quote"]
        parts.append(f'<blockquote class="pull"><p>“{esc(q["text"].strip())}”</p><cite>{esc(q["attribution"])}</cite></blockquote>')
    if c.get("senior_scholars_why"):
        w = c["senior_scholars_why"]
        parts.append(f'<div class="why"><h3>{esc(w["heading"])}</h3><ul>' + "".join(f"<li>{esc(x)}</li>" for x in w["points"]) + "</ul></div>")
    parts.append("</section>")
    parts.append(f'<section aria-labelledby="f-h"><h2 id="f-h">{esc(c.get("fellows_heading", "Scholars"))}</h2>')
    if c.get("fellows"):
        jump = " ".join(f'<a href="#{esc(f["slug"])}">{esc(f["name"])}</a>' for f in c["fellows"])
        parts.append(f'<nav class="jump" aria-label="Scholars in this cohort">{jump}</nav>')
        parts += [person_block(f, d) for f in c["fellows"]]
    else:
        parts.append(f'<p class="muted">{esc(c.get("fellows_note", ""))}</p>')
    parts.append("</section>")
    write(f"scholars/{y}/index.html", page(f"{years(y)} Cohort", "\n".join(parts), d, active="scholars/",
          lede=f'{cohort_status(y)} · {c.get("label", "")}'.strip(" ·")))


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "assets", OUT / "assets")
    build_home()
    build_md_page("content/fellowship.md", "fellowship/", "fellowship/")
    build_apply()
    build_md_page("content/about.md", "about/", "about/")
    build_scholars_index()
    for c in COHORTS:
        build_cohort(c)
    (OUT / ".nojekyll").write_text("")
    print("Built", sum(1 for _ in OUT.rglob("*.html")), "pages into", OUT)


if __name__ == "__main__":
    main()
