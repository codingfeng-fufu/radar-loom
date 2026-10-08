import { readFile } from 'node:fs/promises';

const files = [
  'graph-view.html',
  'viewer.html',
  'ideas/viewer.html',
];

for (const file of files) {
  const source = await readFile(file, 'utf8');
  if (!source.includes('<script')) throw new Error(`${file}: no script block found`);
  const scripts = [...source.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)]
    .map((match) => match[1].trim()).filter(Boolean);
  for (const [index, script] of scripts.entries()) {
    try { new Function(script); } catch (error) {
      throw new Error(`${file}: inline script ${index + 1} failed syntax check: ${error.message}`);
    }
  }
}

console.log('Node source and viewer shell checks passed');
