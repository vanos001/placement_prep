#!/usr/bin/env python3
"""Re-resolve every doi.org URL in the book's markdown and fail on dead DOIs.

Research-branch review §V.3: several dead DOIs carried "(Crossref-verified)"
annotations next to them, so textual verification tags can't be trusted. This
script is deterministic: for each DOI it queries the doi.org Handle API
(https://doi.org/api/handles/<doi>), the authoritative registry covering
Crossref, DataCite and all other registrants — bot-friendly JSON, no publisher
anti-bot walls involved.

responseCode 1  -> DOI is registered (HTTP redirect will resolve)
responseCode 100/404 or HTTP error -> DOI is dead

Usage:  python3 check-doi.py [src-dir]          # default: ./src
Needs network access. Exits 1 if any DOI fails to resolve.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'src')
HANDLE_API = 'https://doi.org/api/handles/'
# Two extraction shapes:
#  - URL: https://doi.org/<token>   (URLs can't contain <>, so the token ends at whitespace/quotes/angle brackets)
#  - plain text: DOI 10.x/y or doi: 10.x/y (older Elsevier/Springer DOIs contain <> and (), so allow them)
URL_DOI_RE = re.compile(r'https?://(?:dx\.)?doi\.org/([^\s<>\[\]"]+)', re.I)
TXT_DOI_RE = re.compile(r'\b(?:DOI|doi)\b[:\s]*[<\[]?(10\.\d{4,9}/[^\s\[\]"]+)', re.I)


def _trim_token(tok):
    """Strip markdown/URL delimiters that cling to the DOI token:
    trailing punctuation, and ')' when the token has unbalanced parens
    (markdown link (https://doi.org/10.2168/lmcs-9(4:23)2013) — the final )
    closes the link, (4:23) belongs to the DOI)."""
    tok = tok.rstrip('.,;:*!?\'"')
    while tok.endswith(')') and tok.count('(') < tok.count(')'):
        tok = tok[:-1]
    return tok


def find_dois(path):
    content = open(path, encoding='utf-8').read()
    out, in_fence = set(), False
    for line in content.split('\n'):
        if line.strip().startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence:
            continue  # example DOIs in code blocks are not citations
        for m in URL_DOI_RE.finditer(line):
            # normalize %XX escapes: some pages cite SICI DOIs with %3C/%3E
            # pre-encoded in the URL; the canonical handle is the decoded form
            doi = _trim_token(urllib.parse.unquote(m.group(1)))
            if doi:
                out.add(doi)
        for m in TXT_DOI_RE.finditer(line):
            doi = _trim_token(m.group(1))
            if doi:
                out.add(doi)
    return out


def check_doi(doi):
    # Percent-encode the DOI: SICI-era DOIs contain #, <, > which are URL
    # delimiters/fragments — an unencoded # silently truncates the query.
    url = HANDLE_API + urllib.parse.quote(doi, safe='()')
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'placement-prep-doi-checker/1.0'})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('responseCode') == 1:
                    return (doi, 'OK')
                return (doi, f"FAIL: registered but responseCode={data.get('responseCode')}")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return (doi, 'FAIL: HTTP 404 from Handle registry — DOI does not exist')
            if e.code == 429 and attempt < 2:
                time.sleep(2 * (attempt + 1)); continue
            return (doi, f'FAIL: HTTP {e.code}')
        except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError) as e:
            if attempt < 2:
                time.sleep(2 * (attempt + 1)); continue
            return (doi, f'FAIL: {type(e).__name__}: {str(e)[:120]}')
    return (doi, 'FAIL: unreachable after retries')


def main():
    doi_files = {}
    for dirpath, _dirs, fs in os.walk(root):
        for f in fs:
            if not f.endswith('.md'):
                continue
            p = os.path.join(dirpath, f)
            for d in find_dois(p):
                doi_files.setdefault(d, []).append(p)
    print(f"Unique DOIs found: {len(doi_files)}")
    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for doi, status in ex.map(check_doi, sorted(doi_files)):
            results.append((doi, status))
    fails = [(d, s) for d, s in results if s.startswith('FAIL')]
    print(f"OK: {len(results) - len(fails)}  FAIL: {len(fails)}")
    if fails:
        print("\n--- Dead DOIs ---")
        for d, s in fails:
            rel = [os.path.relpath(p, root) for p in doi_files[d]]
            print(f"  {s}\n    {d}\n    cited in: {', '.join(sorted(set(rel))[:4])}")
        sys.exit(1)
    print("DOI resolution: OK")


if __name__ == '__main__':
    main()
