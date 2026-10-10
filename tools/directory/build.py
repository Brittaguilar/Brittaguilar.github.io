#!/usr/bin/env python3
"""
Build the SciComm Collaborator Directory from Airtable.

  python tools/directory/build.py                  # normal run (needs AIRTABLE_TOKEN)
  python tools/directory/build.py --from-json x    # offline test from a saved API response
  python tools/directory/build.py --no-photos      # skip headshot downloads

Reads the shared view, keeps awardees only, copies headshots into
collaborator-directory/photos/, and writes one self-contained index.html.
Standard library + Pillow only.
"""
import argparse, base64, io, json, os, re, sys, unicodedata
import urllib.parse, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

BASE_ID  = "appHwYjDaI4ti8B6e"
TABLE_ID = "tblD4tzUE1azQx9yC"                 # People
VIEW_ID  = "viw1O0BYk8ZGmXMJ0"                 # SciComms Freelance Database (Shared)

F = {
    "name": "fldcE0FbBQrLWkQ2C", "first": "fldNy4IZ290IeDIUy", "last": "fldUCFwnlXen1HpBi",
    "title": "fldEEdwQv4Q3m3Ami", "year": "fldSI9dpM9cXeYaEG", "category": "fldVqNzOnbpNdSDYx",
    "bio": "fldApHABsrHrDALvw", "city": "fldYJxUmvATPzdmSQ", "country": "fld60YJJrN84rg1Mg",
    "headshot": "fldeRtbeOLOkE0R2p", "linkedin": "fldCIDC3pQp7h2pnh", "website": "fldT5CUuvv1JZP71q",
    "jobs": "fld05YkfimaX5wg2N", "topics": "fldXjacn8cAA7mlLe", "services": "fldZSfchKE2rJsRZ7",
    "fit": "fldfezvNWriufQzpv",          # "You should work with X if"
}
# Shown on every card, so not useful as a "current job" tag.
DROP_JOBS = {"Science Communicator"}
PHOTO_PX = 240
NOT_FREELANCING = "Not freelancing"   # a Freelance Offers option; never list these people
MIN_KEEP_RATIO = 0.7   # refuse to publish if the new list is under 70% of the old one


# ---------- helpers ----------
def slugify(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def norm(name):
    return slugify(name)

def sort_key(rec):
    f = rec["fields"]
    strip = lambda s: unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().casefold()
    return (strip(f.get(F["last"])), strip(f.get(F["first"])), strip(f.get(F["name"])))

def as_list(v):
    if v is None: return []
    return v if isinstance(v, list) else [v]

def read_people_from_html(path):
    """Pull the PEOPLE array out of a previously built index.html (old or new format)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    m = re.search(r"const PEOPLE\s*=\s*(\[.*?\n?\])\s*;", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


# ---------- Airtable ----------
def fetch_records(token):
    records, offset = [], None
    while True:
        params = [("view", VIEW_ID), ("returnFieldsByFieldId", "true"), ("pageSize", "100")]
        params += [("fields[]", fid) for fid in F.values()]   # only what the page needs
        if offset: params.append(("offset", offset))
        url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
        records += data.get("records", [])
        offset = data.get("offset")
        if not offset: return records


# ---------- photos ----------
def square_crop(img):
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = int((h - side) * 0.15)          # bias toward the top so faces aren't cut off
    return img.crop((left, top, left + side, top + side))

def save_photo(att, dest):
    from PIL import Image
    thumbs = att.get("thumbnails") or {}
    url = (thumbs.get("large") or thumbs.get("full") or {}).get("url") or att["url"]
    with urllib.request.urlopen(url, timeout=60) as r:
        img = Image.open(io.BytesIO(r.read()))
    img = square_crop(img.convert("RGB")).resize((PHOTO_PX, PHOTO_PX), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=82, optimize=True, progressive=True)


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "collaborator-directory"))
    ap.add_argument("--from-json", help="saved Airtable response ({'records': [...]}) for offline testing")
    ap.add_argument("--no-photos", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    index = out / "index.html"
    photos_dir = out / "photos"
    state_file = photos_dir / ".sources.json"      # slug -> attachment id, so unchanged photos aren't re-downloaded

    old_people = read_people_from_html(index)

    # 1. records
    if args.from_json:
        records = json.loads(Path(args.from_json).read_text())["records"]
    else:
        token = os.environ.get("AIRTABLE_TOKEN")
        if not token: sys.exit("AIRTABLE_TOKEN is not set.")
        records = fetch_records(token)

    # 2. awardees only (belt and braces: the Airtable view should already do this)
    def listed(r):
        f = r["fields"]
        offers = [o for o in as_list(f.get(F["services"])) if o != NOT_FREELANCING]
        return bool(f.get(F["year"]) and f.get(F["name"]) and offers)
    records = [r for r in records if listed(r)]
    records.sort(key=sort_key)

    # 4. guard against a bad pull wiping the site
    if old_people and len(records) < MIN_KEEP_RATIO * len(old_people):
        sys.exit(f"Refusing to publish: {len(records)} records vs {len(old_people)} on the live page.")
    if not records:
        sys.exit("No awardee records returned.")

    # 5. build people + photos
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    people, used, missing_fit, missing_photo = [], set(), [], []
    for r in records:
        f = r["fields"]
        name = f[F["name"]].strip()
        slug = slugify(name)
        rel = f"photos/{slug}.jpg"
        dest = out / rel
        atts = f.get(F["headshot"]) or []
        photo = None
        if atts and not args.no_photos:
            att = atts[0]
            if not (dest.exists() and state.get(slug) == att["id"]):
                try:
                    save_photo(att, dest); state[slug] = att["id"]
                except Exception as e:
                    print(f"  photo failed for {name}: {e}", file=sys.stderr)
        if dest.exists():
            photo = rel; used.add(dest.name)
        else:
            missing_photo.append(name)

        country = (as_list(f.get(F["country"])) or [""])[0]
        person = {
            "name": name,
            "title": (f.get(F["title"]) or "").strip(),
            "city": (f.get(F["city"]) or "").strip(),
            "country": str(country).strip(),
            "category": f.get(F["category"]) or "",
            "jobs": [j for j in as_list(f.get(F["jobs"])) if j not in DROP_JOBS],
            "year": str(f.get(F["year"]) or ""),
            "services": [o for o in as_list(f.get(F["services"])) if o != NOT_FREELANCING],
            "topics": as_list(f.get(F["topics"])),
            "website": f.get(F["website"]) or "",
            "linkedin": f.get(F["linkedin"]) or "",
            "bio": (f.get(F["bio"]) or "").strip(),
            "fit": (f.get(F["fit"]) or "").strip(),
            "photo": photo,
        }
        if not person["fit"]: missing_fit.append(name)
        people.append(person)

    # 6. tidy photos nobody references any more
    if photos_dir.exists():
        for p in photos_dir.glob("*.jpg"):
            if p.name not in used: p.unlink()
        for s in list(state):
            if f"{s}.jpg" not in used: state.pop(s)
    if not args.no_photos:
        photos_dir.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n")

    # 7. render
    fonts = "".join(
        '@font-face{font-family:"Poppins";font-style:normal;font-weight:%d;font-display:swap;'
        'src:url(data:font/woff2;base64,%s) format("woff2")}\n'
        % (w, base64.b64encode((HERE / "fonts" / f"poppins-latin-{w}-normal.woff2").read_bytes()).decode())
        for w in (300, 400, 700))
    data = json.dumps(people, indent=1, ensure_ascii=False).replace("</", "<\\/")
    html = (HERE / "template.html").read_text(encoding="utf-8").replace("/*FONTS*/", fonts).replace("/*DATA*/", data)
    out.mkdir(parents=True, exist_ok=True)
    new_bytes = html.encode("utf-8")
    if not index.exists() or index.read_bytes() != new_bytes:
        index.write_bytes(new_bytes)
        print(f"Wrote {index} ({len(people)} people).")
    else:
        print("No changes.")

    if missing_fit:
        print(f"\n{len(missing_fit)} without a 'fit' line (fill in the 'You should work with X if' column in Airtable): "
              + ", ".join(missing_fit[:12]) + (" ..." if len(missing_fit) > 12 else ""))
    if missing_photo:
        print(f"{len(missing_photo)} without a headshot (initials shown): " + ", ".join(missing_photo[:12]))


if __name__ == "__main__":
    main()
