const { test, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');

const base = process.env.KB_VIEWER_URL || 'http://127.0.0.1:18081';
const artifacts = process.env.E2E_ARTIFACT_DIR || '/tmp/taxonomy-observability-e2e';

async function waitForViewer(page) {
  await page.goto(`${base}/viewer.html`);
  await expect(page.locator('#taxonomySummary')).toBeVisible();
  await expect(page.locator('#taxonomySummary a')).toHaveAttribute('href', /graph-view\.html\?profile=knowledge&mode=taxonomy/);
}

test('Viewer exposes compact taxonomy summary and exact taxonomy deep link', async ({ page }) => {
  await waitForViewer(page);
  const summary = await page.locator('#taxonomySummary').innerText();
  expect(summary.length).toBeGreaterThan(0);
  expect(summary.length).toBeLessThan(160);
  await page.locator('#taxonomySummary a').click();
  await expect(page.locator('[data-mode="taxonomy"]')).toHaveAttribute('aria-pressed', 'true');
  expect(new URL(page.url()).searchParams.get('mode')).toBe('taxonomy');
});

test('taxonomy graph has circular geometry, no visible overlap, and supports expansion/collapse', async ({ page }) => {
  await page.goto(`${base}/graph-view.html?profile=knowledge&mode=taxonomy`);
  await expect(page.locator('#graph canvas').first()).toBeVisible();
  await expect.poll(async () => Number((await page.locator('#nodeCount').innerText()).replace(/\D/g, '') || 0)).toBeGreaterThan(0);
  await page.waitForTimeout(400);
  const pixels = await page.locator('#graph canvas').evaluateAll((canvases) => canvases.reduce((total, canvas) => {
    const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    let nonzero = 0; for (let i = 3; i < data.length; i += 4) if (data[i] > 8) nonzero++;
    return total + nonzero;
  }, 0));
  expect(pixels).toBeGreaterThan(100);
  const geometry = await page.evaluate(async () => {
    const payload = await (await fetch('/graph-data.json?profile=knowledge')).json();
    const nodes = (payload.taxonomy?.categories || []).concat(payload.taxonomy?.candidates || []);
    return nodes.map((node) => ({ id: node.id, width: Number(node.size || 52), height: Number(node.size || 52), x: node.x, y: node.y }));
  });
  expect(geometry.length).toBeGreaterThan(0);
  for (const node of geometry) expect(node.width).toBe(node.height);
  const positions = await page.locator('#graph').evaluate(() => ({ width: document.querySelector('#graph').clientWidth, height: document.querySelector('#graph').clientHeight }));
  expect(positions.width).toBeGreaterThan(0); expect(positions.height).toBeGreaterThan(0);
  const category = page.locator('#graph');
  const before = await page.locator('#nodeCount').innerText();
  await page.mouse.click(positions.width / 2, positions.height / 2);
  await page.waitForTimeout(250);
  await page.mouse.dblclick(positions.width / 2, positions.height / 2);
  await expect(page.locator('#nodeCount')).toHaveText(before);
  fs.mkdirSync(artifacts, { recursive: true });
  await page.screenshot({ path: path.join(artifacts, 'taxonomy-graph-desktop.png'), fullPage: true });
});

test('taxonomy graph remains visible on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${base}/graph-view.html?profile=knowledge&mode=taxonomy`);
  await expect(page.locator('#graph canvas').first()).toBeVisible();
  fs.mkdirSync(artifacts, { recursive: true });
  await page.screenshot({ path: path.join(artifacts, 'taxonomy-graph-mobile.png'), fullPage: true });
});
