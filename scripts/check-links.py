#!/usr/bin/env python3
"""Verify all relative .md links in files resolve correctly relative to each file."""
import os, re, sys

root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'src')
files = sys.argv[2:] if len(sys.argv) > 2 else None

def check(path):
    base = os.path.dirname(path)
    content = open(path).read()
    bad = []
    for m in re.finditer(r'\[[^\]]*\]\(([^)]+)\)', content):
        r = m.group(1)
        if r.startswith(('http://', 'https://', '#', 'mailto:')):
            continue
        target = r.split('#')[0].split('?')[0]
        full = os.path.normpath(os.path.join(base, target))
        if target.endswith('.md') and not os.path.exists(full):
            bad.append((r, full))
        elif target.endswith('/') and not os.path.isdir(full):
            bad.append((r, full))
    return bad

if files:
    for f in files:
        path = os.path.join(root, f)
        bad = check(path)
        print(f, "OK" if not bad else bad)
else:
    total_bad = 0
    for dirpath, dirs, fs in os.walk(root):
        for f in fs:
            if not f.endswith('.md'):
                continue
            path = os.path.join(dirpath, f)
            bad = check(path)
            if bad:
                total_bad += len(bad)
                print(path)
                for r, full in bad:
                    print("   ", r, "=>", full)
    print(f"\nTotal broken links: {total_bad}")
