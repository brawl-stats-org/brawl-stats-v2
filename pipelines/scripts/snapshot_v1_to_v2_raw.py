import sys
from pathlib import Path
# Add parent (pipelines/) to path so script can run standalone from scripts/ dir

import argparse
from brawl_stats import read_gzip_json, write_gzip_json


def convert_v1_to_v2(v1_data: dict) -> dict:
    """Convert v1 snapshot format to v2 format

    Args:
        v1_data: v1 format with clubs/individual_players structure

    Returns:
        v2_data: {"timestamp": "...", "players": [...]}

    Raises:
        ValueError: If timestamp is missing from v1 data
    """
    # Extract timestamp from v1 (required)
    timestamp = v1_data.get('timestamp')
    if not timestamp:
        raise ValueError("v1 snapshot missing required 'timestamp' field")

    # Check if v1 has clubs/individual_players structure
    if 'clubs' in v1_data and 'individual_players' in v1_data:
        players = []

        # Extract players from clubs
        for club in v1_data.get('clubs', []):
            members = club.get('members', [])
            players.extend(members)

        # Add individual players
        individual = v1_data.get('individual_players', [])
        players.extend(individual)

        return {
            "timestamp": timestamp,
            "players": players
        }

    # Otherwise simple dict format {tag: player_data}
    return {
        "timestamp": timestamp,
        "players": list(v1_data.values())
    }


def convert_file(input_path: str, output_path: str = None, verbose: bool = False):
    """Convert a single v1 snapshot file to v2 format

    Args:
        input_path: Path to v1 .json.gz file
        output_path: Output path (defaults to overwrite input)
        verbose: Print progress
    """
    if verbose:
        print(f"Converting {input_path}")

    # Read v1 format
    v1_data = read_gzip_json(input_path, verbose=verbose)

    if v1_data is None:
        print(f"Error: Could not read {input_path}")
        return False

    # Check if already v2 format (dict with "players" key)
    if isinstance(v1_data, dict) and 'players' in v1_data and 'timestamp' in v1_data:
        if verbose:
            print(f"  Already v2 format, skipping")
        return True

    if verbose:
        clubs_count = len(v1_data.get('clubs', []))
        indiv_count = len(v1_data.get('individual_players', []))
        print(f"  v1 format: {clubs_count} clubs, {indiv_count} individual players")

    # Convert to v2
    v2_data = convert_v1_to_v2(v1_data)

    if verbose:
        print(f"  v2 format: {len(v2_data)} players (list)")

    # Write to output
    out_path = output_path or input_path
    write_gzip_json(out_path, v2_data, verbose=verbose)

    if verbose:
        print(f"  Saved to {out_path}")

    return True


def convert_directory(dir_path: str, verbose: bool = False):
    """Convert all snapshot files in a directory

    Args:
        dir_path: Directory containing .json.gz files
        verbose: Print progress
    """
    dir_path: Path = Path(dir_path)

    if not dir_path.exists():
        print(f"Error: Directory not found: {dir_path}")
        return

    files = list(dir_path.glob("*.json.gz"))

    if verbose:
        print(f"Found {len(files)} files in {dir_path}")

    converted = 0
    skipped = 0
    errors = 0

    for file_path in sorted(files):
        try:
            v1_data = read_gzip_json(str(file_path))

            # Skip if already v2 format
            if isinstance(v1_data, dict) and 'players' in v1_data and 'timestamp' in v1_data:
                skipped += 1
                if verbose:
                    print(f"[SKIP] {file_path.name} - already v2 format")
                continue

            # Convert
            if convert_file(str(file_path), verbose=verbose):
                converted += 1
            else:
                errors += 1
        except Exception as e:
            print(f"[ERROR] {file_path.name}: {e}")
            errors += 1

    print(f"\nConversion complete:")
    print(f"  Converted: {converted}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors: {errors}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert v1 snapshot format (dict) to v2 format (list)"
    )
    parser.add_argument("--file", help="Convert single file")
    parser.add_argument("--dir", help="Convert all files in directory")
    parser.add_argument("--output", help="Output path (for --file mode, defaults to overwrite)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if not args.file and not args.dir:
        print("Error: Specify --file or --dir")
        parser.print_help()
        return 1

    if args.file and args.dir:
        print("Error: Specify only one of --file or --dir")
        return 1

    if args.output and not args.file:
        print("Error: --output only works with --file")
        return 1

    try:
        if args.file:
            success = convert_file(args.file, args.output, verbose=args.verbose)
            if success:
                print(f"✓ Converted {args.file}")
                return 0
            else:
                return 1

        if args.dir:
            convert_directory(args.dir, verbose=args.verbose)
            return 0

    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    sys.exit(main())
