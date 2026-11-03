#!/usr/bin/env node
/**
 * Phase 13 performance budget gate.
 *
 * Fails the build when the initial JavaScript payload (entry + preloaded
 * vendor chunks) or any single chunk exceeds the approved gzip budget.
 */
import { readdir, readFile, stat } from 'node:fs/promises';
import { gzipSync } from 'node:zlib';
import path from 'node:path';

const DIST = path.resolve(process.cwd(), 'dist/assets');
const INITIAL_BUDGET_BYTES = 190 * 1024; // gzip, entry + react/icons vendor
const CHUNK_BUDGET_BYTES = 180 * 1024; // gzip, any single lazy chunk
const TOTAL_BUDGET_BYTES = 360 * 1024; // gzip, all JavaScript

async function main() {
  let files;
  try {
    files = await readdir(DIST);
  } catch {
    console.error('Bundle check failed: dist/assets is missing. Run `npm run build` first.');
    process.exit(1);
  }

  const jsFiles = files.filter((file) => file.endsWith('.js'));
  if (jsFiles.length === 0) {
    console.error('Bundle check failed: no JavaScript assets were emitted.');
    process.exit(1);
  }

  const sizes = [];
  for (const file of jsFiles) {
    const fullPath = path.join(DIST, file);
    const info = await stat(fullPath);
    const contents = await readFile(fullPath);
    sizes.push({
      file,
      raw: info.size,
      gzip: gzipSync(contents, { level: 9 }).length,
      initial: /^index-/.test(file),
    });
  }

  const allFiles = await readdir(path.resolve(process.cwd(), 'dist'), {
    recursive: true,
  });
  const sourceMaps = allFiles.filter((file) => String(file).endsWith('.map'));
  if (sourceMaps.length > 0) {
    console.error(`Bundle check failed: source maps are published (${sourceMaps.join(', ')}).`);
    process.exit(1);
  }

  sizes.sort((a, b) => b.gzip - a.gzip);
  const totalGzip = sizes.reduce((sum, entry) => sum + entry.gzip, 0);
  const initialGzip = sizes
    .filter((entry) => entry.initial || /^(react-vendor|icons)-/.test(entry.file))
    .reduce((sum, entry) => sum + entry.gzip, 0);

  const kb = (bytes) => `${(bytes / 1024).toFixed(1)} kB`;
  console.log('Bundle budget report (gzip):');
  for (const entry of sizes) {
    console.log(
      `  ${entry.file.padEnd(36)} ${kb(entry.gzip).padStart(10)}${entry.initial ? '  initial' : ''}`,
    );
  }
  console.log(`  ${'initial payload'.padEnd(36)} ${kb(initialGzip).padStart(10)}`);
  console.log(`  ${'all javascript'.padEnd(36)} ${kb(totalGzip).padStart(10)}`);

  const failures = [];
  if (initialGzip > INITIAL_BUDGET_BYTES) {
    failures.push(`Initial payload ${kb(initialGzip)} exceeds ${kb(INITIAL_BUDGET_BYTES)} budget.`);
  }
  if (totalGzip > TOTAL_BUDGET_BYTES) {
    failures.push(`Total JavaScript ${kb(totalGzip)} exceeds ${kb(TOTAL_BUDGET_BYTES)} budget.`);
  }
  for (const entry of sizes) {
    if (entry.gzip > CHUNK_BUDGET_BYTES) {
      failures.push(`Chunk ${entry.file} is ${kb(entry.gzip)} (budget ${kb(CHUNK_BUDGET_BYTES)}).`);
    }
  }

  if (failures.length > 0) {
    console.error('\nBundle budget failed:');
    for (const failure of failures) console.error(`  - ${failure}`);
    process.exit(1);
  }

  console.log('\nBundle budget passed.');
}

main().catch((error) => {
  console.error('Bundle check crashed:', error);
  process.exit(1);
});
