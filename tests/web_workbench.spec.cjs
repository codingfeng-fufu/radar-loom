const { test, expect } = require('@playwright/test');

test('complete knowledge workbench regression', async ({ page }) => {
  const consoleErrors = [];
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  await page.goto('http://127.0.0.1:18080/');

  const createTrigger = page.locator('#createKnowledge');
  await createTrigger.click();
  await page.locator('#cancelCreateKnowledge').click();
  await expect(page.locator('#createKnowledgeDialog')).not.toHaveAttribute('open', '');
  await expect(createTrigger).toBeFocused();
  await createTrigger.click();
  await page.keyboard.press('Escape');
  await expect(page.locator('#createKnowledgeDialog')).not.toHaveAttribute('open', '');
  await createTrigger.click();
  await page.mouse.click(2, 2);
  await expect(page.locator('#createKnowledgeDialog')).not.toHaveAttribute('open', '');

  const viewer = page.frameLocator('#knowledgeFrame');
  await viewer.locator('#navigationSearch').fill('扩散模型');
  await expect(viewer.locator('.search-card').filter({ hasText: '扩散模型 Diffusion Models DDPM' })).toBeVisible();
  await page.keyboard.press('Control+K');
  await expect(viewer.locator('#navigationSearch')).toBeFocused();

  const knowledgeFrame = () => page.frames().find(frame => frame.url().includes('127.0.0.1:18081'));
  await knowledgeFrame().goto('http://127.0.0.1:18081/graph-view.html');
  const graph = page.frameLocator('#knowledgeFrame');
  await graph.locator('#search').fill('扩散模型');
  await graph.locator('.search-result').filter({ hasText: '扩散模型' }).first().click();
  await page.locator('#askClaude').click();
  await expect(page.locator('#dialogContextKind')).toHaveText('当前图谱');
  await expect(page.locator('#dialogFile')).toContainText('扩散模型');
  await page.locator('#cancelAsk').click();

  await graph.locator('[data-mode="combined"]').click();
  await knowledgeFrame().goto(knowledgeFrame().url());
  await expect(page.frameLocator('#knowledgeFrame').locator('[data-mode="combined"]')).toHaveAttribute('aria-pressed', 'true');
  const graphState = await knowledgeFrame().evaluate(() => JSON.parse(sessionStorage.getItem('radar-graph-state-v1')));
  expect(graphState.mode).toBe('combined');
  expect(typeof graphState.zoom).toBe('number');
  expect(graphState.pan).toBeTruthy();

  await page.locator('#askClaude').click();
  await page.locator('#question').fill('刷新后保留草稿');
  await page.locator('#insertPrompt').click();
  const draftBefore = await page.evaluate(() => sessionStorage.getItem('radar-claude-draft-v1'));
  await page.locator('#refreshKnowledge').click();
  await expect(page.locator('#refreshKnowledge')).toBeEnabled({ timeout: 60_000 });
  expect(await page.evaluate(() => sessionStorage.getItem('radar-claude-draft-v1'))).toBe(draftBefore);

  for (const pattern of ['https://cdn.jsdelivr.net/**', 'https://cdnjs.cloudflare.com/**', 'https://unpkg.com/**']) {
    await page.route(pattern, route => route.abort());
  }
  await knowledgeFrame().goto('http://127.0.0.1:18081/viewer.html?f=pages%2F%E6%89%A9%E6%95%A3%E6%A8%A1%E5%9E%8B%20Diffusion%20Models%20DDPM.md');
  await expect(page.frameLocator('#knowledgeFrame').locator('.katex').first()).toBeVisible();
  await knowledgeFrame().goto('http://127.0.0.1:18081/graph-view.html');
  await expect(page.frameLocator('#knowledgeFrame').locator('#graph canvas').first()).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await knowledgeFrame().evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(consoleErrors).toEqual([]);
});
