"""Bulk-fetch released films from Wikipedia's "List of American films of YYYY".

For each candidate:
  1. Parse the year-list to find {date, title, studio}
  2. Filter to wide-release distributors and dates in target window
  3. Fetch the film's individual Wikipedia page → metadata
  4. Pull opening-weekend actuals from the page's "Box office" section
  5. Append to candidates.json

Designed for the 2026 batch test where we want to score the forecaster against
real outcomes for as many recent wide releases as possible.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

# Ensure project root is on sys.path so the worldclone module is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from worldclone.boxoffice.metadata import (
    _strip_links,
    _strip_templates_and_refs,
    fetch_film_metadata,
    fetch_summary,
    fetch_wikitext,
)


WIDE_DISTRIBUTORS = {
    "walt disney studios", "walt disney pictures", "disney",
    "warner bros. pictures", "warner bros.", "warner bros",
    "universal pictures", "universal",
    "sony pictures releasing", "sony pictures", "columbia pictures",
    "paramount pictures", "paramount",
    "lionsgate films", "lionsgate",
    "20th century studios", "20th century",
    "a24",
    "focus features",
    "searchlight pictures", "searchlight",
    "neon",
    "bleecker street",
    "united artists releasing",
    "apple original films", "apple tv+",
    "amazon mgm studios", "amazon mgm", "mgm",
    "stx films", "stxfilms",
    "open road films",
    "roadside attractions",
}


def slugify(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")[:60]


MONTH_NUM = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
}


def parse_year_list(year: int) -> list[dict]:
    """Returns {title, release_date, studio, wiki_link_target} from List_of_American_films_of_YYYY.

    Wikipedia's release calendar is organized:
      Quarter section ("January-March") → month rowspan header → day rowspan
      header → per-film row.
    We track current_month and current_day from the rowspan headers and emit
    one entry per film row.
    """
    page_title = f"List of American films of {year}"
    wt = fetch_wikitext(page_title)
    if not wt:
        return []

    rows = []
    current_month: int | None = None
    current_day: int | None = None

    # Process the calendar tables only (skip the box-office summary table at the top)
    # Find all "==Quarter==" sections after "Box office"
    calendar_start = wt.find("== January–March ==")
    if calendar_start < 0:
        calendar_start = 0
    refs_start = wt.find("== References ==")
    if refs_start < 0:
        refs_start = len(wt)
    calendar_text = wt[calendar_start:refs_start]

    # Split by `|-` to get table rows
    raw_rows = re.split(r"\n\|-", calendar_text)
    for raw in raw_rows:
        # Row that sets the month (rowspan header with month name)
        month_hdr = re.search(r"aria-label=\"(January|February|March|April|May|June|July|August|September|October|November|December)\"", raw)
        if month_hdr:
            current_month = MONTH_NUM[month_hdr.group(1)]
            # The same row often also contains a day header — fall through to day parse

        # Row that sets the day (rowspan="..." | '''DAY''')
        day_hdr = re.search(r"rowspan=\"\d+\"[^|]*\|\s*'''(\d{1,2})'''", raw)
        if day_hdr:
            current_day = int(day_hdr.group(1))

        # A film row contains a title link `''[[Title]]''` after the (possibly absent) day header
        # Use the part of the row AFTER the day header (if present) to find the film
        film_part = raw[day_hdr.end():] if day_hdr else raw
        title_match = re.search(r"''\[\[([^\]\|]+?)(?:\|([^\]]+))?\]\]''", film_part)
        if not title_match or current_month is None or current_day is None:
            continue

        link_target = title_match.group(1).strip()
        display = (title_match.group(2) or link_target).strip()

        # Studio — first wide-distributor link after the title
        studio = ""
        for link in re.finditer(r"\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]", film_part[title_match.end():]):
            candidate = link.group(1).strip().lower()
            if any(d in candidate for d in WIDE_DISTRIBUTORS):
                studio = link.group(1).strip()
                break

        try:
            iso_date = f"{year:04d}-{current_month:02d}-{current_day:02d}"
        except (ValueError, TypeError):
            continue
        rows.append({
            "release_date": iso_date,
            "title": display,
            "wiki_link_target": link_target,
            "studio": studio,
        })
    return rows


# Box office fields on a film's page — we look for "Box office" line in infobox + body text
OPENING_WEEKEND_PATTERNS = [
    # "$X million in its opening weekend"
    re.compile(r"\$\s*([\d,.]+)\s*(?:million|m)\s+(?:in\s+(?:its|the)\s+)?(?:opening\s+weekend|three[- ]day\s+opening|three[- ]day\s+weekend)", re.IGNORECASE),
    # "opened to $X million"
    re.compile(r"opened\s+(?:to|with)\s+\$\s*([\d,.]+)\s*(?:million|m)", re.IGNORECASE),
    # "X opening weekend ... $X million"
    re.compile(r"opening\s+weekend[^\n]{0,80}?\$\s*([\d,.]+)\s*(?:million|m)", re.IGNORECASE),
    # debuted with $X million / three-day debut of $X million
    re.compile(r"(?:three[- ]day\s+(?:debut|opening)|debuted)\s+(?:with\s+|of\s+|to\s+)?\$\s*([\d,.]+)\s*(?:million|m)", re.IGNORECASE),
]


def find_opening_weekend_usd(wikitext: str) -> int | None:
    """Try to extract the domestic 3-day opening weekend from the article body."""
    if not wikitext:
        return None
    cleaned = re.sub(r"<ref[^>]*>.*?</ref>", " ", wikitext, flags=re.DOTALL)
    cleaned = re.sub(r"<ref[^/]*/>", " ", cleaned)
    cleaned = re.sub(r"<!--.*?-->", " ", cleaned, flags=re.DOTALL)
    # Strip nested templates aggressively for matching purposes
    prev = None
    while prev != cleaned:
        prev = cleaned
        cleaned = re.sub(r"\{\{[^{}]*\}\}", " ", cleaned, flags=re.DOTALL)
    cleaned = _strip_links(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)

    candidates = []
    for pat in OPENING_WEEKEND_PATTERNS:
        for m in pat.finditer(cleaned):
            try:
                num = float(m.group(1).replace(",", "")) * 1_000_000
                candidates.append(int(num))
            except ValueError:
                continue
    if not candidates:
        return None
    # Return the median candidate (robust to one outlier)
    candidates.sort()
    return candidates[len(candidates) // 2]


def build_entry(wiki_title: str) -> dict | None:
    md = fetch_film_metadata(wiki_title)
    if not md:
        return None
    wt = fetch_wikitext(wiki_title)
    actual_ow = find_opening_weekend_usd(wt) if wt else None

    rd = md.get("release_date", "")
    year_suffix = rd[:4] if rd else "tba"
    entry_id = f"{slugify(md.get('title', wiki_title))}-{year_suffix}"

    return {
        "id": entry_id,
        "title": md.get("title", wiki_title),
        "release_date": md.get("release_date", ""),
        "distributor": md.get("distributor", ""),
        "studio": md.get("studio", ""),
        "director": md.get("director", ""),
        "cast": md.get("cast", []),
        "genre": [],
        "rating": None,
        "runtime_minutes": md.get("runtime_minutes"),
        "franchise": md.get("franchise"),
        "sequel_number": None,
        "budget_usd": md.get("budget_usd"),
        "opening_theater_count": None,
        "rotten_tomatoes_score": None,
        "metacritic_score": None,
        "notes": f"Auto-imported from {md.get('source_url', '')}",
        "plot_summary": md.get("plot_summary", ""),
        "franchise_priors": [],
        "actual_opening_weekend_usd": actual_ow,
        "actual_opening_theaters": None,
        "actual_opening_per_theater_avg": None,
        "actual_first_week_usd": None,
        "actual_per_day": {},
    }


def parse_top_grossing(year: int) -> list[dict]:
    """Parse the year-list's "highest-grossing" table.

    Format observed in 2026 list:
      |-
      !RANK
      | ''[[Title]]'' {{abbr|...}}
      | [[Studio]]
      |$GROSS,AMOUNT
    """
    page_title = f"List of American films of {year}"
    wt = fetch_wikitext(page_title)
    if not wt:
        return []
    # The top section is "== Box office =="; the table comes immediately after
    bo_start = wt.find("== Box office ==")
    if bo_start < 0:
        return []
    cal_start = wt.find("== January", bo_start)
    if cal_start < 0:
        cal_start = len(wt)
    section = wt[bo_start:cal_start]

    rows = []
    raw_rows = re.split(r"\n\|-", section)
    for raw in raw_rows:
        # Match a rank header (! N) and a title link
        rank_m = re.search(r"^!\s*(\d{1,3})\s*$", raw, re.MULTILINE)
        if not rank_m:
            continue
        title_m = re.search(r"''\[\[([^\]\|]+?)(?:\|([^\]]+))?\]\]''", raw)
        if not title_m:
            continue
        link_target = title_m.group(1).strip()
        display = (title_m.group(2) or link_target).strip()
        # Gross — first $X,XXX,XXX[,...] in the row after the title
        rest = raw[title_m.end():]
        gross_m = re.search(r"\$([\d,]+)", rest)
        gross = int(gross_m.group(1).replace(",", "")) if gross_m else 0
        # Studio link
        studio = ""
        for link in re.finditer(r"\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]", rest):
            cand = link.group(1).strip().lower()
            if any(d in cand for d in WIDE_DISTRIBUTORS):
                studio = link.group(1).strip()
                break
        rows.append({
            "rank": int(rank_m.group(1)),
            "title": display,
            "wiki_link_target": link_target,
            "studio": studio,
            "year_to_date_gross": gross,
        })
    rows.sort(key=lambda r: r["rank"])
    return rows


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--year", type=int, default=2026)
    p.add_argument("--start-date", default="2026-01-01")
    p.add_argument("--end-date", default=None, help="Default: today")
    p.add_argument("--max-films", type=int, default=20)
    p.add_argument("--min-opening-usd", type=int, default=10_000_000,
                   help="Skip films with detected opening weekend below this. Set 0 to keep all.")
    p.add_argument("--mode", choices=("calendar", "top-grossing"), default="top-grossing",
                   help="calendar = walk release calendar; top-grossing = use the highest-grossing table (recommended)")
    p.add_argument("--inter-fetch-sleep", type=float, default=1.5,
                   help="Seconds to wait between consecutive Wikipedia API calls")
    p.add_argument("--out", default="data/films/candidates.json")
    p.add_argument("--dry-run", action="store_true",
                   help="Just list candidates, do not modify candidates.json")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    end = args.end_date or date.today().isoformat()

    if args.mode == "top-grossing":
        print(f"Pulling top-grossing list for {args.year}...", file=sys.stderr)
        top = parse_top_grossing(args.year)
        print(f"  parsed {len(top)} films from top-grossing table", file=sys.stderr)
        # Take the top N
        candidates = [
            {"release_date": "", "title": r["title"], "wiki_link_target": r["wiki_link_target"],
             "studio": r["studio"], "ytd_gross": r["year_to_date_gross"]}
            for r in top[: args.max_films]
        ]
        print(f"  taking top {len(candidates)}", file=sys.stderr)
    else:
        print(f"Pulling Wikipedia year list for {args.year}...", file=sys.stderr)
        rows = parse_year_list(args.year)
        print(f"  parsed {len(rows)} rows from year-list", file=sys.stderr)
        in_window = [r for r in rows if (args.start_date <= r["release_date"] <= end) and r.get("studio")]
        seen = set()
        unique = []
        for r in in_window:
            k = (r["title"].lower(), r["release_date"])
            if k not in seen:
                seen.add(k)
                unique.append(r)
        print(f"  {len(unique)} candidates in window {args.start_date}..{end}", file=sys.stderr)
        candidates = unique[: args.max_films]

    print(f"  fetching detail for {len(candidates)} films (sleep={args.inter_fetch_sleep}s between)...", file=sys.stderr)

    entries = []
    for i, c in enumerate(candidates):
        title = c["wiki_link_target"]
        print(f"  [{i+1}/{len(candidates)}] {title}", file=sys.stderr)
        entry = build_entry(title)
        time.sleep(args.inter_fetch_sleep)
        if not entry:
            print(f"    skip: no metadata", file=sys.stderr)
            continue
        # Apply window filter for top-grossing mode using the fetched release_date
        rd = entry.get("release_date", "")
        if rd and not (args.start_date <= rd <= end):
            print(f"    skip: release {rd} outside window", file=sys.stderr)
            continue
        ow = entry.get("actual_opening_weekend_usd") or 0
        if ow < args.min_opening_usd:
            print(f"    skip: opening weekend ${ow/1e6:.1f}M < ${args.min_opening_usd/1e6:.0f}M (or unknown)", file=sys.stderr)
            continue
        print(f"    OK: ${ow/1e6:.1f}M opening, {entry['distributor']}, '{entry['title']}'", file=sys.stderr)
        entries.append(entry)

    if args.dry_run:
        for e in entries:
            print(json.dumps({k: e[k] for k in ("id", "title", "release_date", "distributor",
                                                 "actual_opening_weekend_usd")}))
        return 0

    # Merge into existing candidates
    out_path = Path(args.out)
    if out_path.exists():
        existing = json.load(out_path.open())
    else:
        existing = {"_metadata": {}, "films": []}
    existing.setdefault("films", [])
    by_id = {f["id"]: f for f in existing["films"]}
    added = 0
    for e in entries:
        if e["id"] in by_id:
            # Update actuals only — preserve any user edits
            current = by_id[e["id"]]
            for k in ("actual_opening_weekend_usd", "plot_summary", "cast", "budget_usd",
                     "runtime_minutes", "franchise"):
                if not current.get(k) and e.get(k):
                    current[k] = e[k]
            continue
        existing["films"].append(e)
        by_id[e["id"]] = e
        added += 1
    with out_path.open("w") as fp:
        json.dump(existing, fp, indent=2)
    print(f"\nAdded {added} new films, total {len(existing['films'])} in {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
