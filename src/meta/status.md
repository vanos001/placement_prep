# Project Status

> Status snapshot: 2026-08-13 (Asia/Shanghai)

## Current status

**Massive content expansion in progress via 6 parallel agents.**
Six new sections are being created simultaneously: Git, Software Engineering,
Programming Fundamentals, Security, Machine Coding, Data Engineering, Search,
Aptitude, Placement Preparation, Resume, Behavioral Interviews, Communication,
Practical Problems, and DBMS Interview Problems.

| Area | Status | Evidence |
|---|---|---|
| Git safety | ✅ Complete | Development is on `dev`; `main` unchanged |
| Git section | 🔄 In progress | 15 files created, commit pushed |
| Software Engineering | 🔄 Agent working | 10 files being created |
| Programming Fundamentals | 🔄 Agent working | 10 files being created |
| Security & Cryptography | 🔄 Agent working | 7 files being created |
| Machine Coding | 🔄 Agent working | 10 files being created |
| Data Engineering | 🔄 Agent working | 7 files being created |
| Search Engines | 🔄 Agent working | 5 files being created |
| Aptitude | 🔄 Agent working | 11 files being created |
| Placement Preparation | 🔄 Agent working | 6 files being created |
| Resume & Career | 🔄 Agent working | 7 files being created |
| Behavioral Interviews | 🔄 Agent working | 5 files being created |
| Communication | 🔄 Agent working | 4 files being created |
| Practical Problems | 🔄 Agent working | 6 files being created |
| DBMS Interview Problems | 🔄 Agent working | 6 files being created |
| Navigation | ✅ Passing | SUMMARY.md updated with all new sections |
| Meta tracking | ✅ Updated | Changelog, coverage, backlog, knowledge graph updated |

## Repository provenance

- Target: [`vanos001/placement_prep`](https://github.com/vanos001/placement_prep)
- Linux source: [`Abhinav-Kumar012/lb2`](https://github.com/Abhinav-Kumar012/lb2)
- DSA source: [`Abhinav-Kumar012/dsa_book_2`](https://github.com/Abhinav-Kumar012/dsa_book_2)

Only educational Markdown was imported. Git metadata, workflows, deployment
configuration, generated output, source JavaScript/CSS, and the DSA source's
anchor-named artifacts were not copied into the target book. Links were
rewritten or converted to nearby text when their old source path did not exist.

## Safety constraints

- Development work is performed on `dev`.
- Release promotion from `dev` to `main` occurs only after validation.
- The current released tree is synchronized on `origin/dev` and `origin/main`.
- Credentials are read only at command time and are not stored in repository
  files, commits, or documentation.

## Final record

`validate-all.sh` was run with an absolute repository path, mdBook 0.4.52, and
Mermaid v11/jsdom. It returned 0: Mermaid heuristic/parser, links, and Summary
all passed. The search-enabled build was attempted twice and killed by the
sandbox memory limit; an isolated full build with `output.html.search.enable = false`
completed successfully. The production `book.toml` was left unchanged.

The release was promoted from `dev` to `main` after validation and synchronized
back to `dev`. The two release branches are kept at the same validated tree;
the working tree is clean.
