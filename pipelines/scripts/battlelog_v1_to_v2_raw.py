import sys
from pathlib import Path
# Add parent (pipelines/) to path so script can run standalone from scripts/ dir

import argparse
from collections import defaultdict
from datetime import datetime
from brawl_stats import read_gzip_json, write_gzip_json


def extract_date_from_battletime(battle_time: str) -> str:
    """Extract date from battleTime timestamp

    Args:
        battle_time: e.g., "20260424T144308.000Z"

    Returns:
        Date string: "2026-04-24"
    """
    # Parse ISO format: 20260424T144308.000Z
    dt = datetime.strptime(battle_time[:15], "%Y%m%dT%H%M%S")
    return dt.strftime("%Y-%m-%d")


def convert_v1_to_v2(input_dir: str, output_dir: str, dry_run: bool = True, verbose: bool = False):
    """Convert v1 battlelog format (per-player) to v2 format (per-day)

    Args:
        input_dir: Directory with v1 files (TAG.json.gz)
        output_dir: Directory for v2 files (YYYY-MM-DD.json.gz)
        dry_run: Preview only, don't write files
        verbose: Print detailed progress
    """
    input_path: Path = Path(input_dir)

    if not input_path.exists():
        print(f"Error: Input directory not found: {input_dir}")
        return

    # Find all player battlelog files (*.json.gz, excluding date-formatted files)
    player_files: list[Path] = []
    for f in input_path.glob("*.json.gz"):
        # Skip if filename looks like a date (YYYY-MM-DD.json.gz)
        if len(f.stem) == 10 and f.stem.count('-') == 2:
            if verbose:
                print(f"[SKIP] Already v2 format: {f.name}")
            continue
        player_files.append(f)

    if not player_files:
        print(f"No v1 battlelog files found in {input_dir}")
        return

    if verbose:
        print(f"Found {len(player_files)} v1 battlelog files")

    # Group battles by date
    battles_by_date = defaultdict(lambda: defaultdict(list))

    for player_file in player_files:
        # Extract tag from filename (remove .json.gz or .json)
        # e.g., "2LGCLLPU2.json.gz" → "2LGCLLPU2"
        tag_name = player_file.stem  # Removes .gz
        if tag_name.endswith('.json'):
            tag_name = tag_name[:-5]  # Remove .json
        tag = "#" + tag_name

        if verbose:
            print(f"Processing {tag}")

        # Read v1 file (list of battles)
        battles = read_gzip_json(str(player_file))

        if not isinstance(battles, list):
            print(f"[WARNING] {tag}: Not a list, skipping")
            continue

        # Group by date
        for battle in battles:
            battle_time = battle.get("battleTime")
            if not battle_time:
                continue

            try:
                date = extract_date_from_battletime(battle_time)
                battles_by_date[date][tag].append(battle)
            except Exception as e:
                print(f"[WARNING] {tag}: Failed to parse battleTime '{battle_time}': {e}")

    # Summary
    print("\nConversion summary:")
    print(f"  v1 player files: {len(player_files)}")
    print(f"  v2 date files: {len(battles_by_date)}")

    if verbose:
        total_battles = sum(
            sum(len(battles) for battles in players.values())
            for players in battles_by_date.values()
        )
        print(f"  Total battles: {total_battles}")

    # Show sample
    sample_dates = sorted(battles_by_date.keys())[-5:]
    print("\nSample dates (last 5):")
    for date in sample_dates:
        player_count = len(battles_by_date[date])
        battle_count = sum(len(battles) for battles in battles_by_date[date].values())
        print(f"  {date}: {player_count} players, {battle_count} battles")

    if dry_run:
        print(f"\n[DRY RUN] Would write {len(battles_by_date)} files to {output_dir}")
        print("Run with --execute to actually write files")
        return

    # Write v2 files
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    written = 0
    merged = 0
    # Process dates in chronological order
    for date in sorted(battles_by_date.keys()):
        players_battles = battles_by_date[date]
        file_path = output_path / f"{date}.json.gz"

        # Load existing file if it exists
        existing_data = {}
        if file_path.exists():
            if verbose:
                print(f"[MERGE] {date}: Loading existing file")
            existing_data = read_gzip_json(str(file_path)) or {}
            merged += 1

        # Merge new battles with existing
        for tag, new_battles in players_battles.items():
            # Get existing battles for this player
            old_battles = existing_data.get(tag, {}).get("items", [])

            # Dedup by battleTime
            seen = {battle["battleTime"]: battle for battle in old_battles}
            for battle in new_battles:
                seen[battle["battleTime"]] = battle

            # Update player's battles
            existing_data[tag] = {"items": list(seen.values())}

        # Write merged data
        write_gzip_json(str(file_path), existing_data, verbose=verbose)
        written += 1

        if verbose:
            player_count = len(existing_data)
            battle_count = sum(len(p["items"]) for p in existing_data.values())
            print(f"✓ {date}.json.gz ({player_count} players, {battle_count} battles)")

    if merged > 0:
        print(f"\n✓ Wrote {written} files ({merged} merged with existing) to {output_dir}")
    else:
        print(f"\n✓ Wrote {written} v2 battlelog files to {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert v1 battlelog format (per-player) to v2 format (per-day)"
    )
    parser.add_argument("--input", default="./data/raw/battlelogs_v1", help="Input directory (v1 files)")
    parser.add_argument("--output", default="./data/raw/battlelogs", help="Output directory (v2 files)")
    parser.add_argument("--execute", action="store_true", help="Actually write files (default is dry-run)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    dry_run = not args.execute

    if dry_run:
        print("=" * 60)
        print("DRY RUN MODE - No files will be written")
        print("Add --execute to actually convert files")
        print("=" * 60)
        print()

    convert_v1_to_v2(args.input, args.output, dry_run=dry_run, verbose=args.verbose)

    return 0


if __name__ == "__main__":
    sys.exit(main())
