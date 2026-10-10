# Collaborator Directory sync

Airtable (view "SciComms Freelance Database (Shared)") -> `collaborator-directory/index.html` + `photos/`.

Files
- `build.py`       pulls the view, keeps awardees only, copies headshots, writes the page
- `template.html`  the design (SciComms look, Poppins embedded). Edit this to change how it looks
- `fonts/`         Poppins woff2 files embedded into the page

One-time setup
1. Copy `tools/` and `.github/` into the repo root.
2. Airtable: create a personal access token with scope `data.records:read`, limited to the SciComms Awards Program base.
3. GitHub repo -> Settings -> Secrets and variables -> Actions -> new secret `AIRTABLE_TOKEN`.
4. GitHub repo -> Settings -> Actions -> General -> Workflow permissions -> "Read and write".
5. Actions tab -> "Sync collaborator directory" -> Run workflow. Check the run log, then the live page.

Day to day
- Edit Airtable. The page updates within a day, or on demand via "Run workflow".
- The "You should work with X if" box comes from that column in Airtable. A blank cell just hides the box (the run log lists who's missing).
- People whose Freelance Offers is only "Not freelancing" are never listed, even if the view includes them.
- If Airtable returns under 70% of the people on the live page, the run fails instead of publishing.

Optional: near-instant updates
Airtable automation, trigger "When record matches conditions" (or updated) on the shared view, action "Run script":

    await fetch("https://api.github.com/repos/Brittaguilar/Brittaguilar.github.io/dispatches", {
      method: "POST",
      headers: { "Authorization": "Bearer GITHUB_TOKEN_HERE", "Accept": "application/vnd.github+json" },
      body: JSON.stringify({ event_type: "airtable-update" })
    });

The GitHub token should be fine-grained, limited to this one repo, with Contents: read and write. Treat the script as sensitive, since the token sits in it.

Test locally without Airtable: `python tools/directory/build.py --from-json saved.json --no-photos --out /tmp/test`
