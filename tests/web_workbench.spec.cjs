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
  const graphState = await knowledgeFrame().evaluate(() => JSON.parse(sessionStorage.getItem('radar-graph-state-knowledge-v1')));
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

test('latest viewer navigation wins delayed response race', async ({ page }) => {
  const viewerBase = process.env.KB_VIEWER_URL || 'http://127.0.0.1:18081';
  await page.route('**/pages/Slow.md', async route => {
    await new Promise(resolve => setTimeout(resolve, 300));
    await route.fulfill({ contentType: 'text/markdown', body: '---\nsummary: slow\ntags: [RAG]\n---\n# Slow page\n' });
  });
  await page.route('**/pages/Fast.md', route => route.fulfill({
    contentType: 'text/markdown',
    body: '---\npage_type: interview\nsummary: fast\ntags: [RAG]\nroles: [backend]\ndifficulty: 基础\nquestion: fast question\n---\n# Fast interview\n'
  }));
  await page.route('**/_interview_index.md', route => route.fulfill({
    contentType: 'text/markdown',
    body: '# 面试索引\n\n## 角色: backend\n\n- [[Fast]] `#RAG` — 原问题: fast question · 摘要: fast · 角色: backend · 难度: 基础\n'
  }));
  await page.goto(`${viewerBase}/viewer.html`);
  await page.evaluate(() => {
    navigateTo('pages/Slow.md', { sectionHint: 'knowledge', historyMode: 'push' });
    navigateTo('pages/Fast.md', { sectionHint: 'interview', historyMode: 'push' });
  });
  await expect(page.locator('#content h1')).toHaveText('Fast interview');
  await page.waitForTimeout(450);
  await expect(page.locator('#content h1')).toHaveText('Fast interview');
  await expect(page.locator('#interviewTab')).toHaveAttribute('aria-selected', 'true');
  expect(new URL(page.url()).searchParams.get('section')).toBe('interview');
  expect(new URL(page.url()).searchParams.get('f')).toBe('pages/Fast.md');
});

test('failed cross-section navigation retries original interview intent', async ({ page }) => {
  const viewerBase = process.env.KB_VIEWER_URL || 'http://127.0.0.1:18081';
  let interviewAttempts = 0;
  await page.route('**/_interview_index.md', route => {
    interviewAttempts += 1;
    if (interviewAttempts === 1) return route.fulfill({ status: 503, body: 'temporary failure' });
    return route.fulfill({
      contentType: 'text/markdown',
      body: '# 面试索引\n\n## 角色: backend\n\n- [[RetryFast]] `#RAG` — 原问题: retry? · 摘要: retry · 角色: backend · 难度: 基础\n'
    });
  });
  await page.route('**/pages/RetryFast.md', route => route.fulfill({
    contentType: 'text/markdown',
    body: '---\npage_type: interview\nsummary: retry\ntags: [RAG]\nroles: [backend]\ndifficulty: 基础\nquestion: retry?\n---\n# Retried interview\n'
  }));
  await page.goto(`${viewerBase}/viewer.html`);
  await page.locator('#interviewTab').click();
  await expect(page.locator('.nav-retry')).toBeVisible();
  await page.locator('.nav-retry').click();
  await expect(page.locator('#content h1')).toHaveText('Retried interview');
  await expect(page.locator('#interviewTab')).toHaveAttribute('aria-selected', 'true');
  expect(new URL(page.url()).searchParams.get('section')).toBe('interview');
  expect(interviewAttempts).toBe(2);
});
