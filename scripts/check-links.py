#!/usr/bin/env python3
"""Verify all relative .md links in files resolve correctly relative to each file.

Extended: `#fragment` anchors are validated against the ids mdBook generates
for headings (id_from_content: lowercase alphanumerics/`-`/`_` kept, other
punctuation dropped, whitespace -> '-'), plus explicit `{#custom-id}` attrs.
"""
import os, re, sys

root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'src')
files = sys.argv[2:] if len(sys.argv) > 2 else None


def mdbook_id(heading_text):
    # strip markdown emphasis/code markers and trailing {#custom-id}
    t = re.sub(r'\{#([A-Za-z0-9_-]+)\}\s*$', '', heading_text)
    t = re.sub(r'[*_~`]', '', t)
    t = re.sub(r'<[^>]+>', '', t)
    out = []
    for c in t:
        if c.isalnum() or c in '-_':
            out.append(c.lower())
        elif c.isspace():
            out.append('-')
    return ''.join(out)


def heading_ids(path):
    ids = set()
    custom = set()
    counts = {}
    try:
        content = open(path).read()
    except OSError:
        return ids
    in_fence = False
    for line in content.split('\n'):
        if line.strip().startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r'^#{1,6}\s+(.*?)\s*$', line)
        if not m:
            continue
        cm = re.search(r'\{#([A-Za-z0-9_-]+)\}\s*$', m.group(1))
        if cm:
            custom.add(cm.group(1))
            continue
        hid = mdbook_id(m.group(1))
        if not hid:
            continue
        n = counts.get(hid, 0)
        counts[hid] = n + 1
        ids.add(hid)
        if n:            # mdBook disambiguates duplicates with -N
            ids.add(f'{hid}-{n}')
    return ids | custom


def check(path):
    base = os.path.dirname(path)
    content = open(path).read()
    bad = []
    for m in re.finditer(r'\[[^\]]*\]\(([^)]+)\)', content):
        r = m.group(1).strip()
        if r.startswith(('http://', 'https://', '#', 'mailto:')):
            continue
        frag = None
        if '#' in r:
            r_nofrag, frag = r.split('#', 1)
        else:
            r_nofrag = r
        target = r_nofrag.split('?')[0]
        full = os.path.normpath(os.path.join(base, target))
        if target.endswith('.md') and not os.path.exists(full):
            bad.append((r, full, 'missing file'))
        elif target.endswith('/') and not os.path.isdir(full):
            bad.append((r, full, 'missing dir'))
        elif frag and target.endswith('.md') and os.path.exists(full):
            if frag not in heading_ids(full):
                bad.append((r, full, 'missing anchor'))
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
                for r, full, why in bad:
                    print("   ", r, "=>", full, f"({why})")
    print(f"\nTotal broken links/anchors: {total_bad}")
