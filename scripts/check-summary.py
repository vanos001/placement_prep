#!/usr/bin/env python3
"""Verify SUMMARY.md navigation completeness.

Checks that:
  1. Every .md file under the book's src dir is reachable from SUMMARY.md
  2. Every SUMMARY.md link points to an existing file

Usage: python3 check-summary.py /path/to/repo/src
"""
import os
import re
import sys


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

    # Links referenced by SUMMARY.md
    refs = set()
    for m in re.finditer(r'\]\(\./([^)]+\.md)', summary):
        refs.add(m.group(1).split('#')[0])
    refs.add('introduction.md')  # implicit first page

    missing = sorted(all_md - refs - {'SUMMARY.md'})
    broken = sorted(refs - all_md)

    print(f"Files under src: {len(all_md)}")
    print(f"Files referenced by SUMMARY: {len(refs & all_md)}")
    if missing:
        print(f"\nNOT in SUMMARY ({len(missing)}):")
        for m in missing:
            print("  ", m)
    if broken:
        print(f"\nBROKEN SUMMARY refs ({len(broken)}):")
        for b in broken:
            print("  ", b)

    if missing or broken:
        sys.exit(1)
    print("SUMMARY navigation: OK")


if __name__ == '__main__':
    main()
