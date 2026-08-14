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
automatically after `mdbook build`. Current graph size: **~1,880 nodes, ~7,500+ internal links** (estimated growth from 1,723 nodes / 7,405 links as of 2026-08-13).

## Graph scope

- Includes every Markdown page under `src/` except `SUMMARY.md`.
- Includes internal relative Markdown links as directed edges.
- Includes orphan pages as nodes so coverage gaps remain visible.
- Omits external URLs, image links, self-links, and Summary navigation edges.
- Current graph size is reported inside the generated visualization.
