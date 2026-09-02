#!/usr/bin/env python3
"""Verify all relative .md links in files resolve correctly relative to each file.

Extended: `#fragment` anchors are validated against the ids mdBook generates
for headings (id_from_content: lowercase alphanumerics/`-`/`_` kept, other
punctuation dropped, whitespace -> '-'), plus explicit `{#custom-id}` attrs.

External URL mode (research-branch review §V.1): the original validator never
checked http(s):// URLs, yet ~24% of a sampled 120 external URLs were dead.
Run `--external` to probe every external URL in markdown links and autolinks:
  - skips fenced code blocks (example URLs) and doi.org URLs (handled by
    scripts/check-doi.py via the doi.org Handle API, which is authoritative
    and bot-friendly)
  - sends a descriptive UA, retries twice, and treats 403/429/999 and
    IEEE-style 202 challenges as MANUAL (bot-blocked, not dead) via an
    allowlist of known bot-blockers
  - FAILS (exit 1) on hard 404/410/5xx, DNS failures and timeouts

Usage: python3 check-links.py [src-dir]                 # internal links only
       python3 check-links.py --external [src-dir]      # + external URL probing
"""
import os, re, sys
import concurrent.futures

EXTERNAL = False
BATCH = None  # (i, M): only URLs with hash(url) % M == i
args = sys.argv[1:]
if '--external' in args:
    EXTERNAL = True
    args.remove('--external')
if '--batch' in args:
    i = args.index('--batch')
    BATCH = (int(args[i + 1]), int(args[i + 2]))
    del args[i:i + 3]
root = os.path.abspath(args[0] if args else 'src')

UA = 'placement-prep-link-checker/1.0 (+https://github.com/vanos001/placement_prep; repo QA bot)'
# Hosts that block automation with 403/202 regardless of URL health.
BOT_BLOCKED_HOSTS = (
    'dl.acm.org', 'acm.org', 'ieeexplore.ieee.org', 'netflixtechblog.com',
    'cppreference.com', 'kubecost.com', 'sciencedirect.com', 'doi.org',
)


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


def strip_fenced(content):
    """Remove fenced code blocks so example URLs aren't probed."""
    out, in_fence = [], False
    for line in content.split('\n'):
        if line.strip().startswith('```'):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return '\n'.join(out)


def external_urls(path):
    """All external http(s) URLs in markdown links + <> autolinks, outside fences."""
    content = strip_fenced(open(path).read())
    urls = set()
    for m in re.finditer(r'\[[^\]]*\]\((https?://[^)\s]+)\)', content):
        urls.add(m.group(1).rstrip('.'))
    for m in re.finditer(r'<(https?://[^>\s]+)>', content):
        urls.add(m.group(1).rstrip('.'))
    return urls


def _to_ascii_url(url):
    """IRI -> URI: IDNA-encode non-ASCII hosts, percent-encode non-ASCII paths.
    http.client encodes requests as ASCII and crashes on raw Unicode."""
    import urllib.parse
    try:
        parts = urllib.parse.urlsplit(url)
        host, port = parts.hostname, parts.port
        if host and not host.isascii():
            host = host.encode('idna').decode('ascii')
        netloc = host or ''
        if parts.username:
            netloc = f"{parts.username}:{parts.password}@{netloc}" if parts.password else f"{parts.username}@{netloc}"
        if port:
            netloc = f"{netloc}:{port}"
        path = urllib.parse.quote(parts.path, safe="/%:@&=+$,;~*'()![]")
        query = urllib.parse.quote(parts.query, safe="=%&?/+,;:@$'()*[]!")
        return urllib.parse.urlunsplit((parts.scheme, netloc, path, query, ''))
    except Exception:
        return url


def check_external_url(url):
    """Return (url, status) where status is 'OK', 'MANUAL: <why>' or 'FAIL: <why>'."""
    try:
        return _check_external_url_inner(url)
    except Exception as e:  # one bad URL must never abort the whole sweep
        return (url, f'MANUAL: checker error {type(e).__name__}: {str(e)[:100]}')


def _check_external_url_inner(url):
    host = re.sub(r'^https?://([^/]+).*$', r'\1', url).lower()
    if host.endswith('doi.org') or host == 'doi.org':
        return (url, 'SKIP-DOI')  # handled by check-doi.py (Handle API)
    if any(host == b or host.endswith('.' + b) for b in BOT_BLOCKED_HOSTS):
        return (url, 'MANUAL: known bot-blocker, verify in a browser')
    headers = {'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml'}
    import urllib.request, urllib.error, ssl
    ctx = ssl.create_default_context()
    target = _to_ascii_url(url)
    for attempt in range(3):
        try:
            req = urllib.request.Request(target, headers=headers, method='GET')
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                return (url, 'OK')
        except urllib.error.HTTPError as e:
            code = e.code
            if code in (403, 429, 999):
                return (url, f'MANUAL: HTTP {code} to automation (likely bot-blocked)')
            if code == 202:
                return (url, 'MANUAL: HTTP 202 anti-bot challenge (IEEE-style)')
            if code in (404, 410) or 500 <= code < 600:
                if attempt < 2:
                    import time; time.sleep(1.5 * (attempt + 1)); continue
                return (url, f'FAIL: HTTP {code}')
            if 300 <= code < 400:
                return (url, 'OK')  # redirect handled by urlopen normally; defensive
            return (url, f'FAIL: HTTP {code}')
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            if attempt < 2:
                import time; time.sleep(1.5 * (attempt + 1)); continue
            return (url, f'FAIL: {type(e).__name__}: {str(e)[:120]}')
    return (url, 'FAIL: unreachable after retries')


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


if __name__ == '__main__':
    if EXTERNAL:
        all_urls = {}
        for dirpath, dirs, fs in os.walk(root):
            for f in fs:
                if not f.endswith('.md'):
                    continue
                p = os.path.join(dirpath, f)
                for u in external_urls(p):
                    all_urls.setdefault(u, []).append(p)
        print(f"External URLs found: {len(all_urls)}")
        if BATCH:
            import hashlib
            i, m = BATCH
            keys = sorted(u for u in all_urls if int(hashlib.md5(u.encode()).hexdigest(), 16) % m == i)
            print(f"Batch {i}/{m}: {len(keys)} URLs")
            all_urls = {u: all_urls[u] for u in keys}
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:
            for url, status in ex.map(check_external_url, sorted(all_urls)):
                results.append((url, status))
        fails = [(u, s) for u, s in results if s.startswith('FAIL')]
        manuals = [(u, s) for u, s in results if s.startswith('MANUAL')]
        skips = [(u, s) for u, s in results if s == 'SKIP-DOI']
        oks = len(results) - len(fails) - len(manuals) - len(skips)
        print(f"OK: {oks}  MANUAL(bot-blocked, verify by hand): {len(manuals)}  DOI(delegated to check-doi.py): {len(skips)}  FAIL: {len(fails)}")
        if manuals:
            print("\n--- Manual-check URLs ---")
            for u, s in manuals:
                print(f"  {s}\n    {u}\n    used in: {', '.join(sorted(set(os.path.relpath(p, root) for p in all_urls[u]))[:3])}")
        if fails:
            print("\n--- Dead URLs ---")
            for u, s in fails:
                print(f"  {s}\n    {u}\n    used in: {', '.join(sorted(set(os.path.relpath(p, root) for p in all_urls[u]))[:3])}")
        sys.exit(1 if fails else 0)
    else:
        files = args[1:] if len(args) > 1 else None
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
            sys.exit(1 if total_bad else 0)
