#!/usr/bin/env python3
"""
Fetch publications from Google Scholar and update publications.md

Usage:
    python scripts/update_publications.py           # Interactive mode
    python scripts/update_publications.py --dry-run # Just show what would be added
    python scripts/update_publications.py --yes     # Auto-confirm additions

Requirements:
    pip install scholarly
"""

import argparse
import re
from pathlib import Path
from scholarly import scholarly

SCHOLAR_ID = "kQrQJ1gAAAAJ"
PUBLICATIONS_FILE = Path(__file__).parent.parent / "publications.md"


def get_scholar_publications(scholar_id: str) -> list[dict]:
    """Fetch all publications from Google Scholar profile."""
    print(f"Fetching publications for scholar ID: {scholar_id}")
    author = scholarly.search_author_id(scholar_id)
    author = scholarly.fill(author, sections=["publications"])

    publications = []
    for pub in author.get("publications", []):
        # Fill in publication details
        pub_filled = scholarly.fill(pub)
        bib = pub_filled.get("bib", {})

        publications.append({
            "title": bib.get("title", ""),
            "authors": bib.get("author", ""),
            "venue": bib.get("venue", bib.get("journal", bib.get("conference", ""))),
            "year": bib.get("pub_year", ""),
            "url": pub_filled.get("pub_url", ""),
            "citations": pub_filled.get("num_citations", 0),
        })
        print(f"  Found: {bib.get('title', '')[:50]}...")

    return publications


def load_existing_publications(filepath: Path) -> set[str]:
    """Extract existing publication titles from publications.md."""
    if not filepath.exists():
        return set()

    content = filepath.read_text()
    # Match bold titles: **[Title](url)** or **Title**
    titles = re.findall(r"\*\*\[?([^\]\*]+)\]?(?:\([^)]+\))?\*\*", content)
    # Normalize titles for comparison
    return {normalize_title(t) for t in titles}


def normalize_title(title: str) -> str:
    """Normalize title for comparison (lowercase, remove punctuation)."""
    return re.sub(r"[^\w\s]", "", title.lower()).strip()


def format_publication(pub: dict) -> str:
    """Format a publication entry for markdown."""
    title = pub["title"]
    authors = pub["authors"]
    venue = pub["venue"] or "Preprint"
    url = pub["url"]

    # Truncate long author lists
    if authors.count(",") > 5:
        author_list = authors.split(",")
        authors = ", ".join(author_list[:3]) + ", et al."

    if url:
        return f"""**[{title}]({url})**\\
{authors}.\\
*{venue}*"""
    else:
        return f"""**{title}**\\
{authors}.\\
*{venue}*"""


def update_publications_file(filepath: Path, new_pubs: list[dict]):
    """Add new publications to the file, organized by year."""
    content = filepath.read_text()

    # Group new publications by year
    by_year = {}
    for pub in new_pubs:
        year = pub.get("year", "Unknown")
        if year not in by_year:
            by_year[year] = []
        by_year[year].append(pub)

    # Add to appropriate year sections
    for year, pubs in sorted(by_year.items(), reverse=True):
        section_header = f"## {year}"
        formatted_pubs = "\n\n".join(format_publication(p) for p in pubs)

        if section_header in content:
            # Add after the year header
            content = content.replace(
                section_header,
                f"{section_header}\n\n{formatted_pubs}",
            )
        else:
            # Find where to insert new year section
            year_pattern = re.compile(r"## (\d{4})")
            matches = list(year_pattern.finditer(content))

            insert_pos = None
            for match in matches:
                if int(match.group(1)) < int(year):
                    insert_pos = match.start()
                    break

            new_section = f"{section_header}\n\n{formatted_pubs}\n\n"
            if insert_pos:
                content = content[:insert_pos] + new_section + content[insert_pos:]
            else:
                # Add at the end
                content = content.rstrip() + f"\n\n{new_section}"

    filepath.write_text(content)


def main():
    parser = argparse.ArgumentParser(description="Update publications from Google Scholar")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be added without modifying files")
    parser.add_argument("--yes", "-y", action="store_true", help="Auto-confirm additions")
    args = parser.parse_args()

    print("Updating publications from Google Scholar...\n")

    # Get existing titles
    existing = load_existing_publications(PUBLICATIONS_FILE)
    print(f"Found {len(existing)} existing publications in {PUBLICATIONS_FILE.name}\n")

    # Fetch from Scholar
    scholar_pubs = get_scholar_publications(SCHOLAR_ID)
    print(f"\nFound {len(scholar_pubs)} publications on Google Scholar\n")

    # Find new publications
    new_pubs = []
    for pub in scholar_pubs:
        if normalize_title(pub["title"]) not in existing:
            new_pubs.append(pub)

    if not new_pubs:
        print("\nNo new publications to add!")
        return

    print(f"\n{'=' * 60}")
    print(f"NEW PUBLICATIONS ({len(new_pubs)} found):")
    print("=" * 60)

    for i, pub in enumerate(new_pubs, 1):
        print(f"\n[{i}] {pub['title']}")
        print(f"    Year: {pub['year']} | Venue: {pub['venue'] or 'N/A'}")
        print(f"    Citations: {pub['citations']}")
        if pub['url']:
            print(f"    URL: {pub['url']}")

    if args.dry_run:
        print("\n[DRY RUN] No changes made.")
        print("\nFormatted entries that would be added:\n")
        for pub in new_pubs:
            print(format_publication(pub))
            print()
        return

    # Confirm before updating
    if not args.yes:
        try:
            response = input("\nAdd these publications? [y/N] ")
            if response.lower() != "y":
                print("Aborted.")
                return
        except EOFError:
            print("\nNon-interactive mode detected. Use --yes to auto-confirm or --dry-run to preview.")
            return

    # Update file
    update_publications_file(PUBLICATIONS_FILE, new_pubs)
    print(f"\nUpdated {PUBLICATIONS_FILE.name} with {len(new_pubs)} new publications.")
    print("Review the changes and adjust formatting as needed.")


if __name__ == "__main__":
    main()
