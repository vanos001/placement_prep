#!/usr/bin/env python3
"""
Fix mdBook "unclosed HTML tag" warnings on the research branch.

mdBook's markdown parser (pulldown-cmark, following CommonMark) treats any
token matching `<[A-Za-z][A-Za-z0-9-]*>` as an HTML open-tag. When such a
token appears in a heading or list item and no matching close-tag exists,
mdBook emits:

    WARN unclosed HTML tag `<x>` found in <file> while exiting Heading(H2)
    HTML tags must be closed before exiting a markdown element.

and the heading/item text is silently dropped from the rendered page.

These tokens are not HTML — they are placeholders like `<pid>`, `<service>`,
`<name>` used in path templates (e.g. /proc/<pid>/limits) and config-file
references (e.g. /etc/default/<service>).

Fix: wrap each `<token>` in inline-code backticks. Backticks break the
tag pattern (the `<` is no longer at the start of a tag-shaped run from
the parser's view) and render the placeholder as inline code, which is
the semantically correct presentation for a path slot.

This script targets only the 11 lines mdBook warned about on the research
branch @ b82a2cb. The 3 additional `<token>` occurrences found elsewhere
are inside multi-line inline code spans (backtick opens on a previous
line) and are already safe.
"""
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent

# (relative_path, line_number_1_indexed, old_substring, new_substring)
EDITS = [
    # --- src/linux/binaries/util-linux/prlimit.md:79
    ("src/linux/binaries/util-linux/prlimit.md", 79,
     "### The read-only mirror: /proc/<pid>/limits",
     "### The read-only mirror: /proc/`<pid>`/limits"),

    # --- src/linux/binaries/util-linux/nsenter.md:232
    ("src/linux/binaries/util-linux/nsenter.md", 232,
     "### Q: What do the /proc/<pid>/ns/* files actually contain, and how do tools tell namespaces apart?",
     "### Q: What do the /proc/`<pid>`/ns/* files actually contain, and how do tools tell namespaces apart?"),

    # --- src/linux/binaries/util-linux/mkfs.md:1 (H1)
    ("src/linux/binaries/util-linux/mkfs.md", 1,
     "# mkfs — front-end dispatcher for filesystem builders (mkfs.<type>)",
     "# mkfs — front-end dispatcher for filesystem builders (mkfs.`<type>`)"),

    # --- src/linux/binaries/util-linux/mkfs.md:213 (item)
    ("src/linux/binaries/util-linux/mkfs.md", 213,
     '"mkfs from util-linux <version>"',
     '"mkfs from util-linux `<version>`"'),

    # --- src/linux/binaries/shadow/newgidmap.md:34
    ("src/linux/binaries/shadow/newgidmap.md", 34,
     "### The kernel layer: /proc/<pid>/gid_map",
     "### The kernel layer: /proc/`<pid>`/gid_map"),

    # --- src/linux/binaries/shadow/newuidmap.md:34
    ("src/linux/binaries/shadow/newuidmap.md", 34,
     "### The kernel layer: /proc/<pid>/uid_map",
     "### The kernel layer: /proc/`<pid>`/uid_map"),

    # --- src/linux/init-systems/openrc/init-scripts.md:329
    ("src/linux/init-systems/openrc/init-scripts.md", 329,
     "### Q: Why do OpenRC scripts source /etc/conf.d/<service>, and what belongs there?",
     "### Q: Why do OpenRC scripts source /etc/conf.d/`<service>`, and what belongs there?"),

    # --- src/linux/init-systems/openrc/init-scripts.md:352 (item)
    # The token is inside a glob pattern rc_<svc>_* — wrap the whole glob in
    # backticks instead of just the token, so it reads as one code span.
    ("src/linux/init-systems/openrc/init-scripts.md", 352,
     "rc_<svc>_* dependency knobs",
     "`rc_<svc>_*` dependency knobs"),

    # --- src/linux/init-systems/sysvinit/configuration.md:281 (H2)
    ("src/linux/init-systems/sysvinit/configuration.md", 281,
     "## Per-Service Configuration: /etc/default/<service>",
     "## Per-Service Configuration: /etc/default/`<service>`"),

    # --- src/linux/init-systems/sysvinit/getty-terminals.md:192 (item)
    ("src/linux/init-systems/sysvinit/getty-terminals.md", 192,
     '"wtmp begins <date>" line',
     '"wtmp begins `<date>`" line'),

    # --- src/linux/init-systems/sysvinit/init-scripts.md:285
    ("src/linux/init-systems/sysvinit/init-scripts.md", 285,
     "### Q: Why do Debian init scripts source /etc/default/<name> and /lib/lsb/init-functions, and what breaks if you skip them?",
     "### Q: Why do Debian init scripts source /etc/default/`<name>` and /lib/lsb/init-functions, and what breaks if you skip them?"),
]


def main():
    errors = 0
    for rel, lineno, old, new in EDITS:
        path = REPO / rel
        if not path.is_file():
            print(f"MISSING: {rel}")
            errors += 1
            continue
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        if lineno > len(lines):
            print(f"LINE OUT OF RANGE: {rel}:{lineno} (file has {len(lines)} lines)")
            errors += 1
            continue
        actual = lines[lineno - 1].rstrip("\n")
        if old not in actual:
            print(f"NOT FOUND in {rel}:{lineno}")
            print(f"  expected substring: {old!r}")
            print(f"  actual line:        {actual!r}")
            errors += 1
            continue
        # Replace just the substring (preserves any leading/trailing content)
        new_line = actual.replace(old, new, 1)
        lines[lineno - 1] = new_line + ("\n" if actual != new_line and not lines[lineno-1].endswith("\n") else lines[lineno-1][len(actual):])
        path.write_text("".join(lines), encoding="utf-8")
        print(f"OK   {rel}:{lineno}")

    if errors:
        print(f"\n{errors} error(s); no commit.")
        raise SystemExit(1)
    print(f"\nAll {len(EDITS)} edits applied.")


if __name__ == "__main__":
    main()
