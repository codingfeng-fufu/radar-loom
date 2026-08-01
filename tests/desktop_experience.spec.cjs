const { test, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');

const workbenchUrl = process.env.WEBUI_URL || 'http://127.0.0.1:18080/';
const knowledgeUrl = process.env.KB_URL || 'http://127.0.0.1:18081';
test.use({ viewport: { width: 1440, height: 900 } });

for (const viewport of [
  { name: 'desktop-wide', width: 1440, height: 900 },
  { name: 'desktop-tall', width: 1112, height: 1243 },
]) {
  test.describe(viewport.name, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test('desktop shell loads without root overflow or console errors', async ({ page }) => {
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('console', message => {
        if (message.type() === 'error') errors.push(message.text());
      });

      await page.goto(workbenchUrl);
      await expect(page.locator('#workbench')).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      expect(errors).toEqual([]);
    });
  });
}

test('restores split width after a full page reload', async ({ page }) => {
  await page.goto(workbenchUrl);
  await page.evaluate(() => {
    sessionStorage.setItem('radar-workbench-state-v1', JSON.stringify({
      version: 1,
      knowledgeWidth: 64,
      knowledgeCollapsed: false,
      claudeCollapsed: false,
    }));
  });

  await page.reload();
  await expect(page.locator('#divider')).toHaveAttribute('aria-valuenow', '64');
});

test('failed refresh preserves the current page and Claude draft', async ({ page }) => {
  await page.goto('http://127.0.0.1:18080/');
  const viewer = page.frameLocator('#knowledgeFrame');
  const claude = page.frameLocator('#claudeFrame');
  await expect(viewer.locator('#content h1').first()).toBeVisible({ timeout: 15_000 });
  const title = await viewer.locator('#content h1').first().textContent();
  const input = claude.getByRole('textbox', { name: 'Type message...' });
  await input.fill('刷新失败后仍应保留的草稿');
  await page.route('http://127.0.0.1:18081/api/refresh', route => route.fulfill({
    status: 503,
    contentType: 'application/json',
    body: JSON.stringify({ ok: false, error: 'simulated refresh failure' }),
  }));
  await page.locator('#refreshKnowledge').click();
  await expect(page.locator('#status')).toHaveAttribute('data-kind', 'error');
  await expect(page.locator('#status')).toContainText('知识库刷新失败');
  await expect(page.locator('#status')).toContainText('本次刷新未完成');
  await expect(page.locator('#status')).toContainText('当前页面和 Claude 草稿已保留');
  await expect(page.locator('#status').getByRole('button', { name: '重新刷新知识库' })).toBeVisible();
  await expect(viewer.locator('#content h1').first()).toHaveText(title);
  await expect(input).toHaveValue('刷新失败后仍应保留的草稿');
  await page.locator('#status').getByRole('button', { name: '关闭状态' }).click();
  await expect(page.locator('#status')).toBeHidden();
});

test('successful refresh completes only after the active knowledge surface recovers', async ({ page }) => {
  await page.goto('http://127.0.0.1:18080/');
  await page.locator('#refreshKnowledge').click();
  await expect(page.locator('#status')).toHaveAttribute('data-kind', 'progress');
  await expect(page.locator('#status')).toContainText('正在');
  await expect(page.locator('#status')).toHaveAttribute('data-kind', 'success', { timeout: 30_000 });
  await expect(page.locator('#status')).toContainText('已恢复');
  await page.locator('#lastResultButton').click();
  await expect(page.locator('#lastResultPanel')).toContainText('知识库刷新');
  await expect(page.locator('#lastResultPanel')).toContainText(/节点/);
  await page.reload();
  await page.locator('#lastResultButton').click();
  await expect(page.locator('#lastResultPanel')).toContainText('知识库刷新');
});

test('Claude context details expose the project and do not claim content was read', async ({ page }) => {
  await page.goto(workbenchUrl);
  await expect(page.locator('#contextSummary')).toContainText('首页.md');
  await page.locator('#contextButton').click();
  await expect(page.locator('#contextDetail')).toContainText('/home/u2023312337/知识库');
  await expect(page.locator('#contextDetail')).toContainText(/标准|权限确认|危险跳过确认/);
  await expect(page.locator('#contextDetail')).not.toContainText('Claude 已读取');
});

test('forged messages cannot replace trusted workbench context', async ({ page }) => {
  await page.goto(workbenchUrl);
  const before = await page.locator('#contextSummary').textContent();
  await page.evaluate(() => window.dispatchEvent(new MessageEvent('message', {
    origin: 'http://127.0.0.1:18081',
    source: window,
    data: { type: 'kb-context', version: 1, context: { version: 1, surface: 'viewer', file: '/etc/passwd', title: '伪造' } },
  })));
  await expect(page.locator('#contextSummary')).toHaveText(before);
});

test('failed page navigation keeps the last readable article', async ({ page }) => {
  await page.goto('http://127.0.0.1:18081/viewer.html?f=%E9%A6%96%E9%A1%B5.md');
  const oldTitle = await page.locator('#content h1').first().textContent();
  await page.route('**/pages/Unavailable.md', route => route.fulfill({ status: 503, body: 'unavailable' }));
  await page.evaluate(() => navigateTo('pages/Unavailable.md', { sectionHint: 'knowledge', historyMode: 'push' }));
  await expect(page.locator('#content h1').first()).toHaveText(oldTitle);
  await expect(page.getByRole('alert')).toContainText('当前内容已保留');
});

test('desktop graph controls are not blocked by the mobile scrim', async ({ page }) => {
  await page.goto(workbenchUrl);
  const frame = page.frames().find(candidate => candidate.url().includes('127.0.0.1:18081'));
  await frame.goto('http://127.0.0.1:18081/graph-view.html');
  const graph = page.frameLocator('#knowledgeFrame');

  await graph.locator('[data-mode="combined"]').click();
  await expect(graph.locator('[data-mode="combined"]')).toHaveAttribute('aria-pressed', 'true');
});

test('desktop viewer section tabs remain operable', async ({ page }) => {
  await page.goto(workbenchUrl);
  const viewer = page.frameLocator('#knowledgeFrame');
  const tab = viewer.locator('#interviewTab');

  await tab.click();
  await expect(tab).toHaveAttribute('aria-selected', 'true');
});

test('second ask-Claude insertion updates the controlled textarea', async ({ page }) => {
  await page.goto(workbenchUrl);
  const prompt = page.frameLocator('#claudeFrame').getByRole('textbox', { name: 'Type message...' });

  for (const question of ['基线第一次输入', '基线第二次输入']) {
    await page.locator('#askClaude').click();
    await page.locator('#question').fill(question);
    await page.locator('#insertPrompt').click();
    await expect(prompt).toHaveValue(new RegExp(question));
  }
});

test('opening a long history keeps the composer at the viewport bottom', async ({ page }) => {
  await page.goto(workbenchUrl);
  const claude = page.frameLocator('#claudeFrame');
  await claude.getByRole('button', { name: 'View conversation history' }).click();
  await claude.locator('div.cursor-pointer').first().click();

  await expect.poll(async () => {
    const frame = page.frames().find(candidate => candidate.url().includes('/projects/home/'));
    return frame.evaluate(() => {
      const shell = document.querySelector('.claude-shell');
      const composer = document.querySelector('.claude-composer')?.getBoundingClientRect();
      return shell?.scrollTop === 0 && Math.abs((composer?.bottom || 0) - innerHeight) < 1;
    });
  }).toBe(true);
});

test('complex knowledge pages and graph render without public network resources', async ({ page }) => {
  for (const pattern of ['https://cdn.jsdelivr.net/**', 'https://cdnjs.cloudflare.com/**', 'https://unpkg.com/**']) {
    await page.route(pattern, route => route.abort());
  }

  await page.goto('http://127.0.0.1:18081/viewer.html?f=pages%2F%E6%89%A9%E6%95%A3%E6%A8%A1%E5%9E%8B%20Diffusion%20Models%20DDPM.md');
  await expect(page.locator('.katex').first()).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);

  await page.goto('http://127.0.0.1:18081/graph-view.html');
  await expect(page.locator('#graph canvas').first()).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('invalid Mermaid is isolated without blocking the interview article', async ({ page }) => {
  await page.route('**/pages/MermaidFailure.md', route => route.fulfill({
    status: 200,
    contentType: 'text/markdown; charset=utf-8',
    body: [
      '---',
      'page_type: interview',
      'summary: Mermaid failure fixture',
      '---',
      '# Mermaid failure fixture',
      '## 30 秒回答',
      '1. 结论',
      '2. 机制',
      '3. 边界',
      '```mermaid',
      'graph TD',
      'A -->',
      '```',
      '## 图后内容',
      '这段正文必须继续显示。',
    ].join('\n'),
  }));

  await page.goto(`${knowledgeUrl}/viewer.html?section=interview&f=pages%2FMermaidFailure.md`);
  await expect(page.locator('.mermaid-error')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole('heading', { name: '图后内容' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('unified search, objective quality, and local operation history are visible', async ({ page }) => {
  await page.goto(workbenchUrl);
  await page.locator('#globalSearchButton').click();
  await page.locator('#globalSearchInput').fill('多头注意力');
  await expect(page.locator('#globalSearchResults')).toContainText('知识库');
  await expect(page.locator('#globalSearchResults')).toContainText('工程面试');
  await page.locator('#globalSearchResults .panel-result').filter({ hasText: 'Multi-Head Attention' }).first().click();
  const viewer = page.frameLocator('#knowledgeFrame');
  await expect(viewer.locator('#content h1').first()).toContainText('多头注意力');
  await viewer.locator('#qualityPanel summary').click();
  await expect(viewer.locator('#qualityFacts')).toContainText('入站');
  await expect(viewer.locator('#qualityFacts')).toContainText('断链');
  await expect(viewer.locator('#qualityFacts')).toContainText('健康状态');

  await page.evaluate(() => localStorage.setItem('radar-workbench-history-v1', JSON.stringify([{
    version: 1, operation: 'page-handoff', status: 'success', surface: 'viewer', revision: null,
    stats: null, preserved: ['Claude 输入框中的建页任务'], error: null, time: Date.now(),
  }])));
  await page.reload();
  await page.locator('#historyButton').click();
  await expect(page.locator('#historyList')).toContainText('建页任务已交接');
});

test('paper reading entry uploads material and hands structured prompt to Claude', async ({ page }) => {
  const name = `paper-reading-e2e-${process.pid}-${Date.now()}.txt`;
  const target = path.resolve(__dirname, '..', 'papers', name);
  try {
    await page.goto(workbenchUrl);
    await page.locator('#readPaper').click();
    await page.locator('#paperFiles').setInputFiles({ name, mimeType: 'text/plain', buffer: Buffer.from('paper supplement') });
    await page.locator('#paperUrls').fill('https://arxiv.org/abs/1706.03762');
    await page.locator('#paperFocus').fill('重点核查实验与部署成本');
    await page.locator('#insertPaperPrompt').click();
    await expect(page.locator('#paperReadingDialog')).not.toBeVisible();
    await expect(page.frameLocator('#claudeFrame').getByRole('textbox', { name: 'Type message...' })).toHaveValue(/\$paper-reading[\s\S]*papers\/[\s\S]*arxiv[\s\S]*部署成本[\s\S]*paper-notes\//);
    expect(fs.existsSync(target)).toBe(true);
    await page.locator('#historyButton').click();
    await expect(page.locator('#historyList')).toContainText('论文精读任务已交接');
  } finally {
    try { fs.unlinkSync(target); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
});
