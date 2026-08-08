#!/usr/bin/env node
/**
 * Mermaid diagram validator for the Placement Prep book.
 *
 * Runs heuristic checks that catch the failure patterns that break the
 * Mermaid v11 renderer used by this book (mermaid-init.js loads v11 from
 * CDN). For authoritative validation, run the real parser locally:
 *
 *   npm i mermaid@11 jsdom && node /path/to/real-parser-validation.mjs
 *
 * These heuristics catch the common v11 breakers:
 *   - unquoted labels containing ( ) | || → ~ unicode math, nested brackets
 *   - escaped quotes (\") inside quoted labels (unreliable in v11; use #quot;)
 *   - 'Note over' / 'Note:' (sequence-diagram syntax) inside graph/flowchart
 *   - multiple node definitions on one line
 *   - '+' joining node statements (block-beta syntax in a flowchart)
 *   - single '->' arrows in flowcharts (must be '-->')
 *   - raw ';' inside sequenceDiagram message/note text (breaks the lexer)
 *   - bare '...' lines and unrecognized prose lines in sequence diagrams
 *   - unquoted subgraph titles containing '=' or spaces
 */
import { readFileSync, readdirSync, statSync, writeFileSync } from 'fs';
import { join, relative } from 'path';

const ROOT = 'src';
const results = { total: 0, passed: 0, failed: 0, errors: [], all: [] };

function walk(dir) {
  const files = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) files.push(...walk(full));
    else if (full.endsWith('.md')) files.push(full);
  }
  return files;
}

function extractMermaidBlocks(content, filePath) {
  const blocks = [];
  const lines = content.split('\n');
  let inBlock = false;
  let startLine = 0;
  let blockLines = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.startsWith('```mermaid')) {
      inBlock = true;
      startLine = i + 1;
      blockLines = [];
    } else if (inBlock && line === '```') {
      blocks.push({ line: startLine + 1, content: blockLines.join('\n'), raw: blockLines });
      inBlock = false;
    } else if (inBlock) {
      blockLines.push(lines[i]);
    }
  }
  return blocks;
}

const DIAGRAM_TYPES = [
  'graph', 'flowchart', 'sequenceDiagram', 'classDiagram', 'stateDiagram',
  'erDiagram', 'gantt', 'pie', 'journey', 'gitGraph', 'mindmap',
  'timeline', 'quadrantChart', 'requirementDiagram', 'C4Context', 'C4Container',
  'C4Component', 'C4Deployment', 'block-beta', 'sankey-beta', 'xychart-beta',
  'radar-beta', 'treemap-beta', 'packet-beta'
];

// Regexes for sequence-diagram statement prefixes that we know are legal.
const SEQ_KEYWORDS = /^\s*(%%|rect|end|else|and|opt|loop|alt|par|critical|break|box|Note|participant|actor|activate|deactivate|autonumber|title:|legend|destroy|create)/;
const SEQ_ARROWS = /->>|-->>|->|-->|-x|--x|-\||--\||\)\)/;

function validateBlock(block, filePath) {
  const content = block.content.trim();
  if (!content) return { ok: false, error: 'Empty mermaid block' };

  const firstLine = block.raw[0]?.trim() || '';

  // Check for valid diagram type
  const hasValidType = DIAGRAM_TYPES.some(t => firstLine.startsWith(t)) ||
                       firstLine.match(/^(graph|flowchart)\s+(TD|TB|BT|RL|LR)/i) ||
                       firstLine.match(/^(sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|journey|gitGraph|mindmap|timeline)/);

  if (!hasValidType) {
    return { ok: false, error: `Unknown diagram type: "${firstLine.substring(0, 50)}"` };
  }

  const isGraph = /^(graph|flowchart)/i.test(firstLine);
  const isSeq = firstLine.startsWith('sequenceDiagram');

  // Check for markdown syntax inside mermaid blocks
  for (const line of block.raw) {
    const trimmed = line.trim();
    if (trimmed.match(/^#{1,6}\s/)) return { ok: false, error: `Markdown heading inside mermaid: "${trimmed.substring(0, 40)}"` };
    if (trimmed.match(/^[-*]\s/) && !trimmed.match(/^[-*]\w/)) {
      if (!firstLine.startsWith('mindmap') && !firstLine.startsWith('gantt') && !firstLine.startsWith('journey')) {
        if (trimmed.length > 3 && trimmed.match(/^[-*]\s+[A-Z]/)) {
          return { ok: false, error: `Possible markdown list inside mermaid: "${trimmed.substring(0, 40)}"` };
        }
      }
    }
    // Escaped quotes inside labels are unreliable in Mermaid v11 → use #quot;
    if (/\\"/.test(trimmed)) {
      return { ok: false, error: `Escaped quote (\\") inside mermaid label — use #quot; entity instead: "${trimmed.substring(0, 60)}"` };
    }
  }

  if (isGraph) {
    const err = validateGraph(block, content);
    if (err) return err;
  }

  if (isSeq) {
    const err = validateSequence(block);
    if (err) return err;
  }

  // For ER diagrams, check entity definitions
  if (firstLine.startsWith('erDiagram')) {
    let braceDepth = 0;
    let inEntityDef = false;
    for (const line of block.raw) {
      const trimmed = line.trim();
      if (trimmed.endsWith('{') && trimmed.match(/^\w+\s*\{/)) {
        inEntityDef = true;
        braceDepth++;
      } else if (inEntityDef && trimmed === '}') {
        braceDepth--;
        if (braceDepth === 0) inEntityDef = false;
      }
    }
    if (braceDepth !== 0) return { ok: false, error: `Unbalanced braces in ER diagram (depth: ${braceDepth})` };
  }

  return { ok: true };
}

function validateGraph(block, content) {
  // Balanced double quotes
  let dq = 0;
  for (const ch of content) if (ch === '"') dq++;
  if (dq % 2 !== 0) return { ok: false, error: 'Unmatched double quote' };

  for (const line of block.raw) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('%%') || /^style\s/.test(trimmed) || /^classDef\s/.test(trimmed)) continue;

    // Quoted segments are opaque to the parser — remove them before checking
    // unquoted labels/arrows so we don't report false positives.
    const stripped = trimmed.replace(/"[^"]*"/g, '""');

    // Note over / Note: are sequence-diagram syntax, invalid in graphs
    if (/^Note(\s+over)?\s*[:]/.test(trimmed) || /^Note\s+over\s+\S+[:,]/.test(trimmed)) {
      return { ok: false, error: `'Note over' is sequence-diagram syntax, invalid in a flowchart: "${trimmed.substring(0, 50)}"` };
    }

    // Single-arrow -> is block-diagram syntax; flowcharts need --> (not part of --> or -.->)
    if (/(^|[^.\-])->(?!-)/.test(stripped)) {
      return { ok: false, error: `Single arrow '->' in flowchart (use '-->'): "${trimmed.substring(0, 50)}"` };
    }

    // '+' joining node statements is block-beta syntax, invalid in flowcharts
    if (/\]\s*\+\s*\[/.test(stripped)) {
      return { ok: false, error: `'+' between node definitions is block-beta syntax, invalid in a flowchart: "${trimmed.substring(0, 50)}"` };
    }

    // Unquoted subgraph titles containing '=' or '(' after the id break v11.
    // (id["Title"], id[Title], "Title", and bare multi-word titles are valid.)
    if (/^\s*subgraph\s+([A-Za-z_][\w.-]*)\s*(=|\(|\{)/.test(stripped)) {
      return { ok: false, error: `Subgraph title should be quoted or use id["title"]: "${trimmed.substring(0, 50)}"` };
    }

    // Multiple node definitions on one line with no edge between them
    const nodeDefs = stripped.match(/\b[A-Za-z_][\w.]*\s*\[[^\[\]]*\]/g) || [];
    const hasEdge = /-->|---|-.->|==>|==/.test(stripped);
    if (nodeDefs.length >= 2 && !hasEdge) {
      return { ok: false, error: `Multiple node definitions on one line (put each on its own line): "${trimmed.substring(0, 60)}"` };
    }

    // Unquoted labels containing characters that break the v11 parser.
    // Verified break-set for unquoted node labels: ( ) { } |
    // Cylinder [( ... )] and circle (( ... )) shapes use parens as delimiters,
    // so neutralize them first; each check is scoped to one bracketed group.
    const normalized = stripped
      .replace(/\[\([^\[\]]*\)\]/g, '[ ]')   // cylinder node ID[(text)] → ID[ ]
      .replace(/\(\([^()]*\)\)/g, '( )');    // circle node ID((text)) → ID( )

    const riskyLabel = /\[[^"[\]]*[(){}|][^"[\]]*\]/;
    const riskyDiamond = /\{[^"{}]*[(){}|][^"{}]*\}/;
    const riskyNestedBracket = /\[[^"[\]]*\[[^"[\]]*\]/;   // [ inside unquoted [ ... ]
    if (riskyLabel.test(normalized) || riskyDiamond.test(normalized) || riskyNestedBracket.test(normalized)) {
      return { ok: false, error: `Unquoted label with special characters (quote it, e.g. ID["..."]): "${trimmed.substring(0, 60)}"` };
    }
    // Edge labels |...| : inspect each label's contents
    for (const em of (normalized.match(/\|([^|"]*)\|/g) || [])) {
      const inner = em.slice(1, -1);
      if (/[()|]/.test(inner)) {
        return { ok: false, error: `Unquoted edge label with special characters (quote it): "${trimmed.substring(0, 60)}"` };
      }
    }
  }
  return null;
}

function validateSequence(block) {
  for (const line of block.raw) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('%%')) continue;

    // Raw semicolons break the sequence-diagram lexer (use #59;).
    // Strip HTML entities (#quot;, #59;, ...) first — their trailing ';' is legal.
    if (/(^|[^0-9]);/.test(trimmed.replace(/#[A-Za-z0-9]+;/g, '#')) && (SEQ_ARROWS.test(trimmed) || /^Note\s+over/.test(trimmed))) {
      return { ok: false, error: `Raw ';' in sequence diagram text breaks the lexer (use #59;): "${trimmed.substring(0, 50)}"` };
    }

    // Bare '...' ellipsis lines are not accepted by v11
    if (/^\.\.\.+\s*$/.test(trimmed)) {
      return { ok: false, error: `Bare '...' line is not valid in sequenceDiagram (use a Note instead): "${trimmed.substring(0, 50)}"` };
    }

    // Unrecognized prose lines (not a message, not a keyword)
    if (!SEQ_KEYWORDS.test(trimmed) && !SEQ_ARROWS.test(trimmed) && /\s/.test(trimmed) && !/^[A-Za-z_]+\s*$/.test(trimmed)) {
      return { ok: false, error: `Unrecognized statement in sequenceDiagram: "${trimmed.substring(0, 50)}"` };
    }
  }
  return null;
}

// Main
const mdFiles = walk(ROOT);
let fileCount = 0;

for (const file of mdFiles) {
  const content = readFileSync(file, 'utf8');
  const blocks = extractMermaidBlocks(content, file);
  if (blocks.length === 0) continue;
  fileCount++;

  for (const block of blocks) {
    results.total++;
    const validation = validateBlock(block, file);
    const info = { file: relative(process.cwd(), file), line: block.line, preview: block.raw[0]?.trim().substring(0, 60) || '' };
    results.all.push(info);
    if (validation.ok) {
      results.passed++;
    } else {
      results.failed++;
      results.errors.push({ ...info, error: validation.error });
    }
  }
}

// Output report
console.log(`\n=== Mermaid Validation Report ===`);
console.log(`Files with diagrams: ${fileCount}`);
console.log(`Total diagrams: ${results.total}`);
console.log(`Passed: ${results.passed}`);
console.log(`Failed: ${results.failed}`);
console.log(`Pass rate: ${((results.passed / results.total) * 100).toFixed(1)}%`);

if (results.errors.length > 0) {
  console.log(`\n--- Errors ---`);
  for (const err of results.errors) {
    console.log(`  ${err.file}:${err.line}: ${err.error}`);
    console.log(`    Preview: ${err.preview}`);
  }
}

writeFileSync('mermaid-validation-report.json', JSON.stringify(results, null, 2));
console.log(`\nFull report written to mermaid-validation-report.json`);

// Make the validator usable in CI: a broken diagram must fail the command.
if (results.failed > 0) process.exitCode = 1;
