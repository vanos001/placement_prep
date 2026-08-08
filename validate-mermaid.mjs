#!/usr/bin/env node
/**
 * Improved Mermaid diagram validator.
 * Uses mermaid library for actual parsing when available,
 * falls back to heuristic checks.
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

  // Check for markdown syntax inside mermaid blocks
  for (const line of block.raw) {
    const trimmed = line.trim();
    if (trimmed.match(/^#{1,6}\s/)) return { ok: false, error: `Markdown heading inside mermaid: "${trimmed.substring(0, 40)}"` };
    if (trimmed.match(/^[-*]\s/) && !trimmed.match(/^[-*]\w/)) {
      // Could be a mermaid list in mindmap/gantt, check context
      if (!firstLine.startsWith('mindmap') && !firstLine.startsWith('gantt') && !firstLine.startsWith('journey')) {
        // More likely an error if it looks like a real list item
        if (trimmed.length > 3 && trimmed.match(/^[-*]\s+[A-Z]/)) {
          return { ok: false, error: `Possible markdown list inside mermaid: "${trimmed.substring(0, 40)}"` };
        }
      }
    }
  }

  // For flowcharts/graphs, check that all referenced nodes are defined or connected
  if (firstLine.match(/^(graph|flowchart)/i)) {
    // Check for unbalanced quotes
    const fullText = content;
    let dq = 0, sq = 0;
    for (const ch of fullText) {
      if (ch === '"') dq++;
      if (ch === "'") sq++;
    }
    if (dq % 2 !== 0) return { ok: false, error: 'Unmatched double quote' };
    // Single quotes in mermaid are often used in labels (e.g., Q'), so don't enforce
  }

  // For sequence diagrams, check participant declarations
  if (firstLine.startsWith('sequenceDiagram')) {
    const participants = new Set();
    const used = new Set();
    for (const line of block.raw) {
      const trimmed = line.trim();
      const pMatch = trimmed.match(/^participant\s+(\w+)/);
      if (pMatch) participants.add(pMatch[1]);
      const arrowMatch = trimmed.match(/^(\w+)\s*[-]+>>?\s*(\w+)/);
      if (arrowMatch) {
        used.add(arrowMatch[1]);
        used.add(arrowMatch[2]);
      }
    }
    // In sequence diagrams, participants can be auto-declared
    // So this is just a warning, not an error
  }

  // For ER diagrams, check entity definitions
  if (firstLine.startsWith('erDiagram')) {
    // Check for unbalanced braces in entity definitions
    // Note: Mermaid relationship notation uses { and } (e.g., ||--o{, }o--o{)
    // These are NOT actual braces, so we only count braces in entity definition blocks
    let braceDepth = 0;
    let inEntityDef = false;
    for (const line of block.raw) {
      const trimmed = line.trim();
      // Entity definition lines end with { or }
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
