# Brittaguilar.github.io: Artifact Hub

Interactive pages made with Claude for Science Communications at Schmidt Sciences. One repo, one folder per artifact, one dashboard.

## Layout

```
/artifacts.json          manifest: one entry per artifact (the dashboard reads this)
/dashboard/index.html    the Artifact Hub dashboard
/robots.txt              asks search engines not to crawl
/<slug>/index.html       one self-contained page per artifact
```

Live links look like `https://brittaguilar.github.io/<slug>/`. Keep slugs lowercase with hyphens and never rename one after sharing it, since the slug is the link.

## Rules for every artifact

1. One file: `/<slug>/index.html`, with all CSS and JS inline (Google Fonts are fine).
2. Include `<meta name="robots" content="noindex, nofollow">` in the head.
3. Public repo, so nothing private goes in. No contact details, budgets, unreleased names or tokens.
4. Anything internal stays a Claude artifact or goes in a private repo. Do not list it in `artifacts.json`.

## Add a new artifact

1. Create `/<slug>/index.html`.
2. Add an entry to `artifacts.json` (fields below) with `status` `live`, `created` and `updated` set to today.
3. Commit with the message `Add <slug>`.

## Update an existing artifact

1. Replace `/<slug>/index.html`.
2. Set that entry's `updated` to today in `artifacts.json`.
3. Commit with the message `Update <slug>: <what changed>`.

## Manifest fields

| Field | Meaning |
|---|---|
| `slug` | Folder name and link ending |
| `title` | Card title |
| `description` | One sentence |
| `tags` | Short project labels, such as SciComms or Training |
| `status` | `live` (in this repo) or `queued` (still elsewhere, give a `url`) |
| `created`, `updated` | `YYYY-MM-DD` |
| `url` | Only for `queued` items: where it lives now |

## Retire an artifact

Delete the folder and its manifest entry. The old version stays in git history.
# Brittaguilar.github.io
Static sites for the Schmidt Sciences science communications portfolio
