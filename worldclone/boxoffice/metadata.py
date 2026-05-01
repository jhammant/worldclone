"""Wikipedia film metadata fetcher.

Parses the {{Infobox film}} template on a Wikipedia article to populate
the Film schema automatically. Also pulls the lead-section plot/summary text.

Wikitext is messy but film infoboxes are quite consistent. This is best-effort —
fields that can't be parsed cleanly are left empty.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.parse
import urllib.request

log = logging.getLogger(__name__)

WP_API = "https://en.wikipedia.org/w/api.php"


def _http_get_json(url: str, *, max_retries: int = 4) -> dict:
    """GET JSON with retry on 429 / 5xx using exponential backoff."""
    import time as _time
    for attempt in range(max_retries):
        req = urllib.request.Request(url, headers={"User-Agent": "worldclone/0.1 (research)"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                wait = 2.0 * (2 ** attempt)
                log.warning("HTTP %d on %s — retry in %.1fs", e.code, url[:80], wait)
                _time.sleep(wait)
                continue
            raise


def search_wikipedia(query: str, limit: int = 5) -> list[dict]:
    """Returns a list of {title, snippet} matches."""
    url = f"{WP_API}?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json&srlimit={limit}"
    data = _http_get_json(url)
    return data.get("query", {}).get("search", [])


def fetch_wikitext(title: str) -> str | None:
    url = f"{WP_API}?action=parse&page={urllib.parse.quote(title)}&prop=wikitext&format=json&formatversion=2"
    try:
        data = _http_get_json(url)
        return data["parse"]["wikitext"]
    except Exception as e:
        log.warning("fetch_wikitext(%s) failed: %s", title, e)
        return None


def fetch_summary(title: str) -> str | None:
    """Plain-text summary from the REST API (first ~paragraph)."""
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
    try:
        data = _http_get_json(url)
        return data.get("extract", "")
    except Exception as e:
        log.warning("fetch_summary(%s) failed: %s", title, e)
        return None


# --------------------------------------------------------------------------
# Wikitext parsers
# --------------------------------------------------------------------------

INFOBOX_OPEN_RE = re.compile(r"\{\{Infobox film", re.IGNORECASE)


def _extract_balanced_infobox(wikitext: str) -> str | None:
    """Find {{Infobox film ...}} with proper {{ }} brace balancing.

    Wikipedia film infoboxes contain nested templates like {{Plainlist|...}} and
    {{Film date|...}}, so we can't just regex to the first }}.
    """
    m = INFOBOX_OPEN_RE.search(wikitext)
    if not m:
        return None
    start = m.start()
    depth = 0
    i = start
    while i < len(wikitext) - 1:
        if wikitext[i:i+2] == "{{":
            depth += 1
            i += 2
        elif wikitext[i:i+2] == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return wikitext[start:i]
        else:
            i += 1
    return None


def _strip_links(s: str) -> str:
    """[[Foo]] -> Foo, [[Foo|Bar]] -> Bar."""
    return re.sub(r"\[\[(?:[^\|\]]+\|)?([^\]]+)\]\]", r"\1", s)


def _strip_templates_and_refs(s: str) -> str:
    # remove <ref>...</ref>
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.DOTALL)
    s = re.sub(r"<ref[^/]*/>", "", s)
    # remove HTML comments
    s = re.sub(r"<!--.*?-->", "", s, flags=re.DOTALL)
    return s


def _parse_film_date(s: str) -> str | None:
    """{{Film date|YYYY|MM|DD|...|YYYY|MM|DD|...}} → YYYY-MM-DD.

    Wikipedia film infoboxes often contain multiple dates (e.g. festival premiere
    in Country A, theatrical release in Country B). We prefer the date adjacent
    to a US/American/United States qualifier; otherwise return the LAST date
    listed (which is usually the wide-release date by Wikipedia convention).
    """
    s = _strip_templates_and_refs(s)
    # Find all 4-tuple groups (YYYY,MM,DD,context-up-to-next-pipe)
    dates: list[tuple[str, str]] = []  # (iso_date, context)
    pattern = re.compile(
        r"\|\s*(\d{4})\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})(?:\s*\|\s*([^|}]*))?",
    )
    # First locate the {{Film date ...}} block (if any) and search inside it; if not, search the whole string.
    block_match = re.search(r"\{\{Film[ _]date(.*?)\}\}", s, re.IGNORECASE | re.DOTALL)
    target = block_match.group(1) if block_match else s
    for m in pattern.finditer(target):
        iso = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        ctx = (m.group(4) or "").strip()
        dates.append((iso, ctx))
    if not dates:
        return None
    # Prefer US/American/United States
    us_re = re.compile(r"united\s*states|u\.?\s*s\.?|america", re.IGNORECASE)
    for iso, ctx in dates:
        if us_re.search(ctx):
            return iso
    # Fallback: last date in the template (typically wide release)
    return dates[-1][0]


def _strip_all_templates(s: str) -> str:
    """Recursively strip all `{{...}}` templates (including nested ones)."""
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"\{\{[^{}]*\}\}", "", s, flags=re.DOTALL)
    return s


def _parse_plain_list(s: str) -> list[str]:
    """Parses {{Plainlist| * a * b}} into ['a', 'b'], or comma/newline-separated lists."""
    # First strip refs and HTML comments
    s = _strip_templates_and_refs(s)
    # Find the outer Plainlist template using brace balance
    pl_match = re.search(r"\{\{(?:Plain ?list|Plainlist|Plain list)\s*\|", s, re.IGNORECASE)
    if pl_match:
        # Walk to matching }}
        start = pl_match.end()
        depth = 1
        i = start
        while i < len(s) - 1 and depth > 0:
            if s[i:i+2] == "{{":
                depth += 1
                i += 2
            elif s[i:i+2] == "}}":
                depth -= 1
                i += 2
                if depth == 0:
                    break
            else:
                i += 1
        inner = s[start:i-2] if depth == 0 else s[start:]
    else:
        inner = s

    inner = _strip_all_templates(inner)
    items = []
    for line in inner.split("\n"):
        line = line.strip().lstrip("*").strip()
        line = _strip_links(line)
        # Drop trailing footnote markers, parentheticals
        line = re.sub(r"\s*\([^)]*\)\s*$", "", line).strip()
        if line:
            items.append(line)
    if items:
        return items
    # Fallback: comma-separated
    s2 = _strip_all_templates(_strip_links(s)).strip()
    return [t.strip() for t in re.split(r"[,;]\s*", s2) if t.strip()]


def _parse_money(s: str) -> int | None:
    """Try to extract a USD integer from infobox budget/gross text.

    Handles common Wikipedia formatting cruft: {{nbsp}}, {{Currency}}, &nbsp;,
    HTML entities, and inline citations.
    """
    s = _strip_templates_and_refs(s)
    # Replace common space templates and entities with a real space
    s = re.sub(r"\{\{(?:nbsp|hsp|nb sp|spaces?)\}\}", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"&nbsp;|&#160;", " ", s)
    s = _strip_links(s)
    # "$200 million" / "US$200 million" / "$200,000,000" / "200 million USD"
    m = re.search(
        r"\$?\s*([\d,]+(?:\.\d+)?)\s*(million|billion|m|b)\b",
        s, re.IGNORECASE,
    )
    if m:
        num = float(m.group(1).replace(",", ""))
        unit = m.group(2).lower()
        if unit.startswith("b"):
            num *= 1_000_000_000
        else:
            num *= 1_000_000
        return int(num)
    # Plain dollar with no million/billion (already-expanded form)
    m = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", s)
    if m:
        num = float(m.group(1).replace(",", ""))
        # If the number is very small (< 10000), it's probably mis-parsed; reject
        if num < 10000:
            return None
        return int(num)
    return None


def parse_infobox(wikitext: str) -> dict[str, str]:
    """Returns dict of raw infobox field → raw value strings."""
    full = _extract_balanced_infobox(wikitext)
    if not full:
        return {}
    # Strip the opening "{{Infobox film" and the closing "}}"
    body = full[len("{{Infobox film"):-2]
    fields: dict[str, str] = {}
    # Split by lines starting with `|` at column 0; values can span multiple lines
    current_key: str | None = None
    current_val_lines: list[str] = []
    for line in body.split("\n"):
        m2 = re.match(r"^\|\s*([a-zA-Z_][a-zA-Z_0-9 ]*?)\s*=\s*(.*)$", line)
        if m2:
            if current_key is not None:
                fields[current_key] = "\n".join(current_val_lines).strip()
            current_key = m2.group(1).strip().lower().replace(" ", "_")
            current_val_lines = [m2.group(2)]
        else:
            current_val_lines.append(line)
    if current_key is not None:
        fields[current_key] = "\n".join(current_val_lines).strip()
    return fields


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def fetch_film_metadata(title: str) -> dict | None:
    """Returns a dict shaped for the Film pydantic model. Caller still needs to
    fill in the slug/id and any ground truth.

    Includes:
      title, release_date, distributor, studio, director, cast (list),
      genre (list, partial), rating (sometimes), runtime_minutes, franchise,
      sequel_number, budget_usd, plot_summary, source_url
    """
    wt = fetch_wikitext(title)
    if not wt:
        return None
    summary = fetch_summary(title) or ""

    info = parse_infobox(wt)
    out: dict = {
        "title": title,
        "source_url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}",
        "plot_summary": summary,
    }

    # Release date
    if "released" in info:
        d = _parse_film_date(info["released"])
        if d:
            out["release_date"] = d

    # Director
    if "director" in info:
        directors = _parse_plain_list(info["director"])
        if directors:
            out["director"] = directors[0]

    # Distributor / studio (may be in production_companies, distributor, or both)
    if "distributor" in info:
        dl = _parse_plain_list(info["distributor"])
        if dl:
            out["distributor"] = dl[0]
    if "production_companies" in info:
        sl = _parse_plain_list(info["production_companies"])
        if sl:
            out["studio"] = sl[0]
    elif "studio" in info:
        sl = _parse_plain_list(info["studio"])
        if sl:
            out["studio"] = sl[0]

    # Cast
    if "starring" in info:
        cast = _parse_plain_list(info["starring"])
        if cast:
            out["cast"] = cast[:8]

    # Runtime
    if "runtime" in info:
        rt = _strip_templates_and_refs(info["runtime"])
        m = re.search(r"(\d+)\s*minutes", rt, re.IGNORECASE)
        if m:
            out["runtime_minutes"] = int(m.group(1))

    # Budget
    if "budget" in info:
        b = _parse_money(info["budget"])
        if b:
            out["budget_usd"] = b

    # Based-on / franchise
    if "based_on" in info:
        bo = info["based_on"]
        m = re.search(r"\{\{Based on\s*\|\s*''?\[\[([^\]\|]+)", bo, re.IGNORECASE)
        if m:
            out["franchise"] = m.group(1).strip()
        else:
            txt = _strip_links(_strip_templates_and_refs(bo)).strip()
            if txt:
                out["franchise"] = txt[:80]

    # Rating from infobox is uncommon on en.wikipedia; skip — leave optional.
    # Genre is also usually not in the infobox; pull from categories or summary later.

    return out


def fetch_franchise_prior_films(franchise_title: str, exclude_titles: list[str] = None) -> list[dict]:
    """Crude: search Wikipedia for "[franchise] films" and parse the listing.

    Returns up to 5 prior films with {title, release_date, opening_weekend_usd}
    where opening_weekend_usd is left None — caller fills in from BOM if desired.
    Best-effort; may return empty list for franchises without a listing article.
    """
    candidates = [f"List of {franchise_title} films", f"{franchise_title} (franchise)"]
    for cand in candidates:
        wt = fetch_wikitext(cand)
        if not wt:
            continue
        # Pull `{{film date|YYYY|MM|DD}}` rows next to a [[Title]] link
        rows = []
        for m in re.finditer(r"\[\[([^\]\|]+?)\]\][^\n]{0,200}\{\{(?:Film|film)[ _]date\|(\d{4})\|(\d{1,2})\|(\d{1,2})", wt):
            t = m.group(1).strip()
            d = f"{m.group(2)}-{int(m.group(3)):02d}-{int(m.group(4)):02d}"
            if exclude_titles and t in exclude_titles:
                continue
            rows.append({"title": t, "release_date": d})
            if len(rows) >= 5:
                break
        if rows:
            return rows
    return []
