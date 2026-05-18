"""
Utility to extract Horoquartz rules from hopprog.csv, remove comments and variable labels, and save to inputs/ for inference.
"""
import argparse
import os
import re
import sys

import pandas as pd


CSV_DEFAULT = os.path.join(
    os.path.dirname(__file__), "..", "assets", "tables", "hopprog.csv"
)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "inputs")


def extract_rule(rule_name: str, csv_path: str = CSV_DEFAULT, strip_comments: bool = True) -> list[str]:
    """Return instruction lines for *rule_name* sorted by line number.

    When *strip_comments* is True (default) comment lines are removed except
    for the "* Règle : ..." header, and DEBDICO variable labels are blanked.
    When False the raw lines are returned as-is.
    """
    df = pd.read_csv(csv_path.replace('hopregl', 'hopprog'), sep=";", dtype=str)

    mask = df["REGLE"].str.strip().str.upper() == rule_name.strip().upper()
    rule_df = df[mask].copy()

    if rule_df.empty:
        raise ValueError(f"Rule '{rule_name}' not found in {csv_path}")

    rule_df = rule_df.sort_values("LIG")

    if strip_comments:
        # Drop comment lines (INST starts with '*') except the "* Règle : ..." header
        is_regle_header = (
            rule_df['INST'].str.strip().str.match(r'^\*\s*R[èe]gle\s*:', re.IGNORECASE)
        )
        first_10 = pd.Series(False, index=rule_df.index)
        first_10.iloc[:10] = True
        keep_header = is_regle_header & first_10
        is_comment = rule_df['INST'].str.lstrip(" ").str.startswith("*")
        rule_df = rule_df[~is_comment | keep_header]

        # Remove trailing ;"..."; label at end of DEBDICO variable declarations
        lines = rule_df['INST'].str.replace(r';"[^"]*";\s*$', ';"";', regex=True)
    else:
        lines = rule_df['INST']

    return lines


def save_rule(
    rule_name: str,
    csv_path: str = CSV_DEFAULT,
    output_dir: str = OUTPUT_DIR,
    strip_comments: bool = True,
) -> str:
    """Extract rule and write to output_dir. Returns the output path."""
    lines = extract_rule(rule_name, csv_path, strip_comments=strip_comments)
    os.makedirs(output_dir, exist_ok=True)
    suffix = "_sans_commentaire" if strip_comments else ""
    output_path = os.path.join(output_dir, f"{rule_name}{suffix}.txt")
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return output_path


_HOPREGL_CSV = os.path.join(
    os.path.dirname(__file__), "..", "assets", "tables", "hopregl.csv"
)


def _all_rule_names(hopprog_path: str) -> list[str]:
    """Return all rule names from hopregl.csv sorted by ORDRE ascending."""
    df = pd.read_csv(hopprog_path.replace('hopprog', 'hopregl'), sep=";", dtype=str)
    df["REGLE"] = df["REGLE"].str.strip('"').str.strip()
    df["ORDRE"] = pd.to_numeric(df["ORDRE"].str.strip('"').str.strip(), errors="coerce")
    return df.sort_values("ORDRE")["REGLE"].tolist()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract a Horoquartz rule from hopprog.csv without comments."
    )
    parser.add_argument(
        "rule_name",
        nargs="*",
        help="One or more rule names (REGLE) to extract. If omitted, all rules from hopregl.csv are processed.",
    )
    parser.add_argument(
        "--csv",
        default=CSV_DEFAULT,
        help="Path to hopprog.csv (default: backend/assets/tables/hopprog.csv)",
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        help="Directory where the output file is written (default: inputs/)",
    )
    parser.add_argument(
        "--keep-comments",
        action="store_true",
        default=False,
        help="Keep comment lines in the output (default: strip comments).",
    )
    args = parser.parse_args()

    strip_comments = not args.keep_comments
    rule_names = args.rule_name if args.rule_name else _all_rule_names(args.csv)

    for rule_name in rule_names:
        try:
            path = save_rule(rule_name, args.csv, args.output_dir, strip_comments=strip_comments)
            print(f"Saved: {path}")
        except ValueError as exc:
            print(f"Warning: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
