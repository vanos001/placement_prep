#!/usr/bin/env python3
"""Verify SUMMARY.md navigation completeness.

Checks that:
  1. Every .md file under the book's src dir is reachable from SUMMARY.md
  2. Every SUMMARY.md link points to an existing file
  3. No SUMMARY destination is listed more than once (duplicate destinations
     break mdBook's nav generation — batch-65 shipped one that had to be
     fixed by hand; a duplicate check catches it deterministically)

Usage: python3 check-summary.py /path/to/repo/src
"""
import os
import re
import sys
from collections import Counter


def main():
    src = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'src')
    summary_path = os.path.join(src, 'SUMMARY.md')
    if not os.path.exists(summary_path):
        print(f"ERROR: {summary_path} not found")
        sys.exit(1)

    summary = open(summary_path).read()

    # Every .md file under src (excluding SUMMARY.md itself)
    all_md = set()
    for dirpath, _dirs, files in os.walk(src):
        for f in files:
            if f.endswith('.md'):
                all_md.add(os.path.relpath(os.path.join(dirpath, f), src))

    # Links referenced by SUMMARY.md — keep an ordered list so duplicates are visible
    ref_list = []
    for m in re.finditer(r'\]\(\./([^)]+\.md)', summary):
        dest = m.group(1).split('#')[0]
        if dest:
            ref_list.append(dest)
    refs = set(ref_list)
    refs.add('introduction.md')  # implicit first page

    duplicates = sorted(d for d, c in Counter(ref_list).items() if c > 1)

    missing = sorted(all_md - refs - {'SUMMARY.md'})
    broken = sorted(refs - all_md)

    print(f"Files under src: {len(all_md)}")
    print(f"Files referenced by SUMMARY: {len(refs & all_md)}")
    print(f"Duplicate SUMMARY destinations: {len(duplicates)}")
    if missing:
        print(f"\nNOT in SUMMARY ({len(missing)}):")
        for m in missing:
            print("  ", m)
    if broken:
        print(f"\nBROKEN SUMMARY refs ({len(broken)}):")
        for b in broken:
            print("  ", b)

    if duplicates:
        print(f"\nDUPLICATE SUMMARY destinations ({len(duplicates)}):")
        for d in duplicates:
            print(f"   {d} (x{Counter(ref_list)[d]})")
    if missing or broken or duplicates:
        sys.exit(1)
    print("SUMMARY navigation: OK")


if __name__ == '__main__':
    main()
