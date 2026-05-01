"""Helper to add film candidates to data/films/candidates.json.

Two modes:
  --interactive: prompt for fields one at a time
  --from-wikipedia <YEAR>: pull "List of American films of YYYY" wikitext and
    surface candidate wide releases (user still verifies + adds ground truth)

Wide-release filtering is heuristic — by default we keep films released by major
distributors (Disney, Warner, Universal, Sony, Paramount, Lionsgate, A24,
Focus, Searchlight, Neon, etc.).

After adding, populate `actual_opening_weekend_usd` from Box Office Mojo:
  https://www.boxofficemojo.com/release/{tt-id}
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path


CANDIDATES_PATH = Path("data/films/candidates.json")
WIDE_DISTRIBUTORS = {
    "Walt Disney Studios", "Walt Disney Pictures",
    "Warner Bros. Pictures", "Warner Bros.",
    "Universal Pictures",
    "Sony Pictures Releasing", "Sony Pictures", "Columbia Pictures",
    "Paramount Pictures",
    "Lionsgate Films", "Lionsgate",
    "20th Century Studios",
    "A24",
    "Focus Features",
    "Searchlight Pictures",
    "Neon",
    "Bleecker Street",
    "United Artists Releasing",
    "Apple Original Films", "Apple TV+",
    "Amazon MGM Studios", "Amazon MGM",
    "STX Films", "STXfilms",
    "Open Road Films",
    "Roadside Attractions",
    "MGM",
}


def load_candidates() -> dict:
    if not CANDIDATES_PATH.exists():
        return {"_metadata": {}, "films": []}
    with CANDIDATES_PATH.open() as f:
        return json.load(f)


def save_candidates(d: dict) -> None:
    CANDIDATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CANDIDATES_PATH.open("w") as f:
        json.dump(d, f, indent=2)


def fetch_wikipedia_wikitext(title: str) -> str:
    """Return the wikitext source of a Wikipedia article."""
    url = (
        f"https://en.wikipedia.org/w/api.php"
        f"?action=parse&page={urllib.parse.quote(title)}"
        f"&prop=wikitext&format=json&formatversion=2"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "worldclone/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    return data["parse"]["wikitext"]


WIDE_RELEASE_ROW_RE = re.compile(
    r"\|\s*\{\{film date\|(?P<date>[^\|}]+)\|.*?\}\}\s*\|\s*\{\{nowrap\|''\[\[(?P<title>[^\]\|]+).*?\]\]''\}\}\s*\|\s*(?P<rest>[^\n]+)",
    re.IGNORECASE,
)


def parse_wikipedia_film_table(wikitext: str) -> list[dict]:
    """Extract simple {date, title, distributor, director, cast} rows from
    a "List of American films of YYYY" wikitext.

    The Wikipedia film table format is messy and varies year to year — this
    is best-effort. User should hand-verify all entries.
    """
    rows = []
    # Match table lines that start with a film date template
    for m in WIDE_RELEASE_ROW_RE.finditer(wikitext):
        date = m.group("date").strip()
        title = m.group("title").strip()
        rest = m.group("rest")
        # Crude distributor extraction: text between `[[` and `]]` in `rest`
        distrib = ""
        for distrib_match in re.finditer(r"\[\[([^\]\|]+?)\]\]", rest):
            cand = distrib_match.group(1).strip()
            if any(d.lower() in cand.lower() or cand.lower() in d.lower() for d in WIDE_DISTRIBUTORS):
                distrib = cand
                break
        rows.append({
            "release_date": date,
            "title": title,
            "distributor": distrib,
            "raw_rest": rest[:300],
        })
    return rows


def slugify(title: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
    return s[:60]


def add_film_via_wikipedia(wiki_title: str, *, override_id: str | None = None,
                            sequel_number: int | None = None) -> dict | None:
    """Fetch metadata from Wikipedia, build a Film dict, append to candidates.json.

    Returns the inserted entry, or None on failure.
    """
    # Lazy import so this script still runs without uv-installed deps for read-only modes
    from worldclone.boxoffice.metadata import fetch_film_metadata, fetch_franchise_prior_films

    md = fetch_film_metadata(wiki_title)
    if not md:
        print(f"Could not fetch metadata for {wiki_title!r}", file=sys.stderr)
        return None

    # Slug-based ID derived from title + release year
    rd = md.get("release_date", "")
    year_suffix = rd[:4] if rd else "tba"
    base_id = override_id or f"{slugify(md.get('title', wiki_title))}-{year_suffix}"

    franchise_priors = []
    if md.get("franchise"):
        priors = fetch_franchise_prior_films(md["franchise"], exclude_titles=[md["title"]])
        franchise_priors = priors[:5]

    entry = {
        "id": base_id,
        "title": md.get("title", wiki_title),
        "release_date": md.get("release_date", ""),
        "distributor": md.get("distributor", ""),
        "studio": md.get("studio", ""),
        "director": md.get("director", ""),
        "cast": md.get("cast", []),
        "genre": [],  # TODO: pull from categories
        "rating": None,
        "runtime_minutes": md.get("runtime_minutes"),
        "franchise": md.get("franchise"),
        "sequel_number": sequel_number,
        "budget_usd": md.get("budget_usd"),
        "opening_theater_count": None,
        "rotten_tomatoes_score": None,
        "metacritic_score": None,
        "notes": f"Auto-imported from {md.get('source_url', '')}",
        "plot_summary": md.get("plot_summary", ""),
        "franchise_priors": franchise_priors,
        "actual_opening_weekend_usd": None,
        "actual_opening_theaters": None,
        "actual_opening_per_theater_avg": None,
        "actual_first_week_usd": None,
        "actual_per_day": {},
    }

    cur = load_candidates()
    cur.setdefault("films", [])
    # Replace if already present
    cur["films"] = [f for f in cur["films"] if f["id"] != entry["id"]]
    cur["films"].append(entry)
    save_candidates(cur)
    print(f"Added: {entry['id']}  release={entry['release_date']}  cast={entry['cast'][:3]}...",
          file=sys.stderr)
    return entry


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--add", help="Wikipedia title to fetch and add (e.g. 'The Super Mario Galaxy Movie')")
    p.add_argument("--override-id", help="Use this slug instead of auto-derived")
    p.add_argument("--sequel-number", type=int, help="Set the sequel_number field (1=original, 2=first sequel, ...)")
    p.add_argument("--from-wikipedia", help="Year, e.g. 2026 — pulls List_of_American_films_of_YYYY")
    p.add_argument("--filter-month", help="Only show films from MM-YYYY (e.g. 04-2026)")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.add:
        entry = add_film_via_wikipedia(
            args.add,
            override_id=args.override_id,
            sequel_number=args.sequel_number,
        )
        return 0 if entry else 1

    if args.from_wikipedia:
        title = f"List of American films of {args.from_wikipedia}"
        print(f"Fetching {title}...", file=sys.stderr)
        try:
            wt = fetch_wikipedia_wikitext(title)
        except Exception as e:
            print(f"Failed: {e}", file=sys.stderr)
            return 1
        rows = parse_wikipedia_film_table(wt)
        print(f"Parsed {len(rows)} rows", file=sys.stderr)
        wide = [r for r in rows if r["distributor"]]
        print(f"  with major distributor: {len(wide)}", file=sys.stderr)
        for r in wide:
            print(json.dumps(r, indent=2))
        return 0

    print("Use --add 'Wikipedia Title' to fetch a film, or --from-wikipedia YYYY for the year list,")
    print("or hand-edit data/films/candidates.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
