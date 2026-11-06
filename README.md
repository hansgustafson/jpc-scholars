# JPC Scholars in Interreligious Studies website

The public site for the Jay Phillips Center Scholars in Interreligious Studies fellowship. Every change pushed to `main` rebuilds and republishes the site automatically through GitHub Pages. You can edit every file below on github.com: open the file, click the pencil, and commit.

## Where things live

| To change | Edit |
|---|---|
| Which cohort is "current", the next call's status, dates, and form link | `site.yml` |
| A cohort's Senior Scholar(s) and fellows | `cohorts/<year>.yml` |
| The Fellowship, Apply, and About pages | `content/fellowship.md`, `content/apply.md`, `content/about.md` |
| The FAQ on the Apply page | `content/faq.yml` |
| The home page intro and the three gatherings | `content/home.yml` |
| Photos | `assets/images/people/<slug>.jpg` |

## Each year

1. **When a Senior Scholar is confirmed**, create `cohorts/<next year>.yml` (copy `cohorts/2027-2028.yml` as a starting point) with their name and bio. Leave `fellows: []`.
2. **When the call opens**, in `site.yml` set `call.cohort` to that year, `call.status: open`, add `call.form_url`, and list the dates.
3. **When the deadline passes**, set `call.status: closed`.
4. **When fellows are selected**, add them to that year's cohort file, then set `current_cohort` to that year when their fellowship year begins.

Past cohorts stay on the Scholars page at their own addresses, such as `/scholars/2026-2027/`. Each person has a direct link, such as `/scholars/2026-2027/#laurel-potter`, that they can use on a CV.

## Photos

Save a square photo, at least 400 × 400 pixels, as `assets/images/people/<slug>.jpg`, where `<slug>` is the person's `slug` in the cohort file (for example `laurel-potter.jpg`). Anyone without a photo shows their initials.

## Building locally (optional)

```
pip install pyyaml markdown
python build.py            # writes the site to _site/
```
