// Real Mermaid v11 parser-based validation of all diagrams in the repo.
// Usage: node validate.mjs [path-to-repo-src]
import { readFileSync, readdirSync, statSync, writeFileSync } from 'fs';
import { join, relative } from 'path';
import { JSDOM } from 'jsdom';

const ROOT = process.argv[2] || 'src'; // pass the repo's src dir, or run from repo root

// --- Set up DOM environment for mermaid ---
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', { pretendToBeVisual: true });
global.window = dom.window;
global.document = dom.window.document;
global.navigator = { userAgent: 'node.js', language: 'en-US' };
global.DOMParser = dom.window.DOMParser;
global.Node = dom.window.Node;
global.Element = dom.window.Element;
global.SVGElement = dom.window.SVGElement;
global.HTMLElement = dom.window.HTMLElement;
global.getComputedStyle = dom.window.getComputedStyle.bind(dom.window);
global.window.devicePixelRatio = 1;

const { default: mermaid } = await import('mermaid');

mermaid.initialize({
  startOnLoad: false,
  securityLevel: 'loose',
  logLevel: 'fatal',
  flowchart: { useMaxWidth: true, htmlLabels: true },
  sequence: { useMaxWidth: true, wrap: true },
});

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

function extractMermaidBlocks(content) {
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

const files = walk(ROOT);
const results = { total: 0, passed: 0, failed: 0, errors: [], filesWithDiagrams: 0 };

let idx = 0;
for (const file of files) {
  const content = readFileSync(file, 'utf8');
  const blocks = extractMermaidBlocks(content);
  if (blocks.length === 0) continue;
  results.filesWithDiagrams++;

  for (const block of blocks) {
    idx++;
    results.total++;
    const text = block.content.trim();
    if (!text) {
      results.failed++;
      results.errors.push({ file: relative(process.cwd(), file), line: block.line, error: 'Empty mermaid block', preview: '' });
      continue;
    }
    try {
      await mermaid.parse(text);
      results.passed++;
    } catch (e) {
      results.failed++;
      const msg = (e && (e.message || e.toString())) || 'unknown error';
      // Extract just the first meaningful part of the mermaid error
      const clean = String(msg).split('\n').filter(l => l.trim()).slice(0, 3).join(' | ');
      results.errors.push({
        file: relative(process.cwd(), file),
        line: block.line,
        error: clean.substring(0, 300),
        preview: block.raw[0]?.trim().substring(0, 80) || '',
      });
    }
  }
  if (idx % 400 === 0) console.error(`progress: ${idx}/${totalSoFar()}`);
}
function totalSoFar() { return '?'; }

console.log(`\n=== Mermaid Parser Validation (mermaid v${mermaid.version || '11'}) ===`);
console.log(`Files with diagrams: ${results.filesWithDiagrams}`);
console.log(`Total diagrams: ${results.total}`);
console.log(`Passed: ${results.passed}`);
console.log(`Failed: ${results.failed}`);
console.log(`Pass rate: ${((results.passed / results.total) * 100).toFixed(2)}%`);

// Group errors by file
const byFile = {};
for (const e of results.errors) {
  if (!byFile[e.file]) byFile[e.file] = [];
  byFile[e.file].push(e);
}

if (results.errors.length > 0) {
  console.log(`\n--- Files with broken diagrams: ${Object.keys(byFile).length} ---`);
  for (const [f, errs] of Object.entries(byFile)) {
    console.log(`\n${f}:`);
    for (const e of errs) {
      console.log(`  line ${e.line}: ${e.error}`);
      if (e.preview) console.log(`    preview: ${e.preview}`);
    }
  }
}

writeFileSync('/home/user/mermaid-validate/report.json', JSON.stringify({ results, byFile }, null, 2));
console.log('\nReport written to report.json');
process.exitCode = results.failed > 0 ? 1 : 0;
