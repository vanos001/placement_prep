# Cross-Reference Graph

This page is a navigational map of the placement-preparation knowledge base.
Each dot is a Markdown page and each line is an internal cross-reference.
Colors identify top-level sections such as Linux, DSA, Operating Systems,
Networks, DBMS, and Interview Preparation.

The interactive graph is generated automatically from the current `src/`
links during the GitHub Pages deployment. It is intentionally emitted into the
mdBook output rather than committed as a large generated artifact.

[Open the full-screen graph](cross-reference-graph-view.html)

<iframe
  title="Placement Prep cross-reference graph"
  src="cross-reference-graph-view.html"
  style="width: 100%; height: 720px; border: 1px solid #dbe3ef; border-radius: 10px; background: #f4f7fb;"
></iframe>

## Local generation

After a successful `mdbook build`, regenerate the graph from the repository root:

```bash
python3 scripts/generate-cross-reference-graph.py \
  --output src/meta/cross-reference-graph-view.html
```

The generated file is not tracked. The deployment workflow runs this command
automatically after `mdbook build`. Current graph size: **~4,119 nodes, ~19,169 unique internal links** (regenerated across 4,119 content files on 2026-10-15; one edge per source→target pair, so a link repeated across pages or inside one page counts once). For comparison, the 2026-09-19 review measured ~2,810 nodes and 24,754 link *occurrences* — occurrence counts are higher because they do not deduplicate.

## Graph scope

- Includes every Markdown page under `src/` except `SUMMARY.md`.
- Includes internal relative Markdown links as directed edges.
- Since 2026-10-13 there are no orphan pages: every content page is reachable
  from `SUMMARY.md`, so the graph and the sidebar cover the same corpus.
- Omits external URLs, image links, self-links, and Summary navigation edges.
- Current graph size is reported inside the generated visualization.
