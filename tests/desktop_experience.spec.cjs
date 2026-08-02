const { test, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');

const workbenchUrl = process.env.WEBUI_URL || 'http://127.0.0.1:18080/';
const knowledgeUrl = process.env.KB_URL || 'http://127.0.0.1:18081';
test.use({ viewport: { width: 1440, height: 900 } });

async function measuredNavigate(page, file, section) {
  return page.evaluate(async ({ file, section }) => {
    const started = performance.now();
    const ok = await navigateTo(file, { sectionHint: section, historyMode: 'push' });
    return { ok, elapsed: performance.now() - started };
  }, { file, section });
}

async function installClipboardCapture(page, { rich = true } = {}) {
  await page.addInitScript(({ rich }) => {
    window.__clipboardWrites = [];
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: async text => window.__clipboardWrites.push({ kind: 'text', text }),
        write: rich ? async items => {
          const item = items[0];
          const html = await (await item.getType('text/html')).text();
          const plain = await (await item.getType('text/plain')).text();
          window.__clipboardWrites.push({ kind: 'rich', html, plain });
        } : undefined,
      },
    });
    Object.defineProperty(window, 'ClipboardItem', {
      configurable: true,
      value: rich ? class ClipboardItemCapture {
        constructor(data) { this.data = data; }
        async getType(type) { return this.data[type]; }
      } : undefined,
    });
  }, { rich });
}

async function chooseExport(page, triggerName, itemName) {
  await page.getByRole('button', { name: triggerName }).click();
  await page.getByRole('menuitem', { name: itemName }).click();
}

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

test('failed page navigation keeps export available for the retained article', async ({ page }) => {
  await installClipboardCapture(page);
  await page.goto('http://127.0.0.1:18081/viewer.html?f=%E9%A6%96%E9%A1%B5.md');
  await expect(page.getByRole('button', { name: '复制当前页面' })).toBeVisible();
  const retainedSource = await page.evaluate(() => activeExportSnapshot.source);
  await page.route('**/pages/UnavailableExport.md', route => route.fulfill({ status: 503, body: 'unavailable' }));
  await page.evaluate(() => navigateTo('pages/UnavailableExport.md', { sectionHint: 'knowledge', historyMode: 'push' }));
  await expect(page.getByRole('alert')).toContainText('当前内容已保留');
  await chooseExport(page, '复制当前页面', '原始 Markdown');
  await expect.poll(() => page.evaluate(() => window.__clipboardWrites.at(-1)?.text)).toBe(retainedSource);
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

  await page.goto(`${knowledgeUrl}/viewer.html?f=pages%2F%E6%89%A9%E6%95%A3%E6%A8%A1%E5%9E%8B%20Diffusion%20Models%20DDPM.md`);
  await expect(page.locator('.katex').first()).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);

  await page.goto(`${knowledgeUrl}/graph-view.html`);
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

test('interview body hierarchy stays scoped across all migrated pages', async ({ page }) => {
  const interviewPages = [
    '设计一个AI Agent的记忆系统.md',
    '多头注意力机制的核心作用是什么.md',
    '知识图谱的存储方式与索引优化.md',
  ];

  for (const filename of interviewPages) {
    const target = new URL('/viewer.html', knowledgeUrl);
    target.searchParams.set('section', 'interview');
    target.searchParams.set('f', `pages/${filename}`);
    await page.goto(target.toString());
    await expect(page.locator('#content')).toHaveClass(/page-type-interview/, { timeout: 15_000 });
    await expect(page.locator('.interview-answer-brief')).toHaveCount(1);
    await expect(page.locator('.interview-answer-brief')).toBeVisible();
    await expect(page.locator('.mermaid svg').first()).toBeVisible({ timeout: 30_000 });
    await expect(page.locator('#content')).not.toContainText('**');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }

  await page.evaluate(() => navigateTo('pages/LRU 缓存替换 Least Recently Used.md', {
    sectionHint: 'knowledge',
    historyMode: 'push',
  }));
  await expect(page.locator('#content h1')).toContainText('LRU');
  await expect(page.locator('#content')).not.toHaveClass(/page-type-interview/);
});

test('knowledge pages do not expose unresolved strong-emphasis markers', async ({ page }) => {
  const filenames = [
    'K近邻 KNN K-Nearest Neighbors.md',
    'Robust Scaler 鲁棒缩放.md',
    'Scaling Law 大模型缩放律.md',
    '层归一化 LayerNorm BatchNorm.md',
    '词嵌入 Word Embedding.md',
    '马尔可夫 Markov.md',
  ];

  for (const filename of filenames) {
    const target = new URL('/viewer.html', knowledgeUrl);
    target.searchParams.set('section', 'knowledge');
    target.searchParams.set('f', `pages/${filename}`);
    await page.goto(target.toString());
    await expect(page.locator('#content h1')).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('#content')).not.toContainText('**');
  }
});

test('slow enrichment never blocks article navigation', async ({ page }) => {
  await page.route('**/api/catalog', route => new Promise(resolve => {
    setTimeout(() => resolve(route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: '{"entries":[],"edges":[]}',
    })), 1500);
  }));
  await page.route('**/graph-data.json', route => new Promise(resolve => {
    setTimeout(() => resolve(route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: '{"taxonomy":{"categories":[],"stats":{}}}',
    })), 1500);
  }));

  await page.goto(`${knowledgeUrl}/viewer.html?f=pages%2FK%E8%BF%91%E9%82%BB%20KNN%20K-Nearest%20Neighbors.md`);
  await expect(page.locator('#content h1')).toContainText('K近邻');
  const result = await measuredNavigate(page, 'pages/词嵌入 Word Embedding.md', 'knowledge');
  expect(result.ok).toBe(true);
  expect(result.elapsed).toBeLessThan(300);
  await expect(page.locator('#content h1')).toContainText('词嵌入');
});

test('navigation reuses one index per section and meets desktop budgets', async ({ page }) => {
  const counts = { knowledge: 0, interview: 0 };
  page.on('request', request => {
    const pathname = new URL(request.url()).pathname;
    if (pathname === '/_index.md') counts.knowledge += 1;
    if (pathname === '/_interview_index.md') counts.interview += 1;
  });

  await page.goto(`${knowledgeUrl}/viewer.html?f=pages%2FK%E8%BF%91%E9%82%BB%20KNN%20K-Nearest%20Neighbors.md`);
  await expect(page.locator('#content h1')).toContainText('K近邻');
  const same = await measuredNavigate(page, 'pages/词嵌入 Word Embedding.md', 'knowledge');
  const cross = await measuredNavigate(page, 'pages/多头注意力机制的核心作用是什么.md', 'interview');
  const interviewAgain = await measuredNavigate(page, 'pages/知识图谱的存储方式与索引优化.md', 'interview');

  expect(same.elapsed).toBeLessThan(300);
  expect(cross.elapsed).toBeLessThan(500);
  expect(interviewAgain.elapsed).toBeLessThan(300);
  expect(counts).toEqual({ knowledge: 1, interview: 1 });
});

test('rapid navigation shows feedback and commits only the latest target', async ({ page }) => {
  await page.route(url => decodeURIComponent(url.pathname).endsWith('/pages/Robust Scaler 鲁棒缩放.md'), async route => {
    await new Promise(resolve => setTimeout(resolve, 250));
    await route.continue();
  });
  await page.goto(`${knowledgeUrl}/viewer.html?f=pages%2FK%E8%BF%91%E9%82%BB%20KNN%20K-Nearest%20Neighbors.md`);
  await expect(page.locator('#content h1')).toContainText('K近邻');

  await page.evaluate(() => {
    window.firstNavigation = navigateTo('pages/Robust Scaler 鲁棒缩放.md', {
      sectionHint: 'knowledge', historyMode: 'push',
    });
  });
  await expect(page.locator('#content')).toHaveAttribute('aria-busy', 'true', { timeout: 100 });
  await expect(page.locator('#message')).toContainText('正在打开');
  await page.evaluate(() => {
    window.secondNavigation = navigateTo('pages/词嵌入 Word Embedding.md', {
      sectionHint: 'knowledge', historyMode: 'push',
    });
  });

  await expect(page.locator('#content h1')).toContainText('词嵌入');
  await page.waitForTimeout(300);
  await expect(page.locator('#content h1')).toContainText('词嵌入');
  await expect(page.locator('#content')).toHaveAttribute('aria-busy', 'false');
});

test('viewer export menus are accessible and a long title does not overlap actions', async ({ page }) => {
  await page.route('**/pages/LongExportTitle.md', route => route.fulfill({
    status: 200,
    contentType: 'text/markdown; charset=utf-8',
    body: '# 这是一个用于验证标题换行且不会遮挡复制和下载按钮的非常长的知识页面标题\n\n正文。',
  }));
  await page.goto(`${knowledgeUrl}/viewer.html?f=pages%2FLongExportTitle.md`);
  const copy = page.getByRole('button', { name: '复制当前页面' });
  const download = page.getByRole('button', { name: '下载当前页面' });
  await copy.click();
  await expect(page.getByRole('menuitem', { name: '原始 Markdown' })).toBeFocused();
  await page.keyboard.press('End');
  await expect(page.getByRole('menuitem', { name: '渲染后的富文本' })).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(copy).toBeFocused();
  const [titleBox, copyBox, downloadBox] = await Promise.all([
    page.locator('.article-title').boundingBox(), copy.boundingBox(), download.boundingBox(),
  ]);
  expect(titleBox.x + titleBox.width).toBeLessThanOrEqual(copyBox.x);
  expect(copyBox.x + copyBox.width).toBeLessThanOrEqual(downloadBox.x);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('viewer copies exact source, body-only Markdown, and dual-MIME rich text', async ({ page }) => {
  await installClipboardCapture(page);
  const source = '---\ntags: [测试]\nsummary: export fixture\n---\n# Export Fixture\n\n**重点**与公式 $x^2$。';
  await page.route('**/pages/ExportFixture.md', route => route.fulfill({
    status: 200, contentType: 'text/markdown; charset=utf-8', body: source,
  }));
  await page.goto(`${knowledgeUrl}/viewer.html?f=pages%2FExportFixture.md`);
  await chooseExport(page, '复制当前页面', '原始 Markdown');
  await expect.poll(() => page.evaluate(() => window.__clipboardWrites.at(-1)?.text)).toBe(source);
  await chooseExport(page, '复制当前页面', '纯正文 Markdown');
  await expect.poll(() => page.evaluate(() => window.__clipboardWrites.at(-1)?.text)).toBe('# Export Fixture\n\n**重点**与公式 $x^2$。');
  await chooseExport(page, '复制当前页面', '渲染后的富文本');
  await expect.poll(() => page.evaluate(() => window.__clipboardWrites.at(-1)?.kind)).toBe('rich');
  const rich = await page.evaluate(() => window.__clipboardWrites.at(-1));
  expect(rich.kind).toBe('rich');
  expect(rich.html).toContain('<strong>重点</strong>');
  expect(rich.html).toContain('class="katex"');
  expect(rich.html).not.toContain('export-actions');
  expect(rich.plain).toContain('重点与公式');
});

test('viewer rich-text copy falls back truthfully to plain text', async ({ page }) => {
  await installClipboardCapture(page, { rich: false });
  await page.goto(`${knowledgeUrl}/viewer.html?f=%E9%A6%96%E9%A1%B5.md`);
  await chooseExport(page, '复制当前页面', '渲染后的富文本');
  await expect.poll(() => page.evaluate(() => window.__clipboardWrites.at(-1)?.kind)).toBe('text');
  await expect(page.locator('#message')).toContainText('Plain text copied because rich-text clipboard is unavailable.');
});

test('viewer downloads exact Markdown using the source basename', async ({ page }) => {
  const source = '---\nsummary: exact bytes\n---\n# Download Fixture\n\n末尾保留两个换行。\n\n';
  await page.route('**/pages/DownloadFixture.md', route => route.fulfill({
    status: 200, contentType: 'text/markdown; charset=utf-8', body: source,
  }));
  await page.goto(`${knowledgeUrl}/viewer.html?f=pages%2FDownloadFixture.md`);
  const downloadPromise = page.waitForEvent('download');
  await chooseExport(page, '下载当前页面', '原始 .md');
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('DownloadFixture.md');
  expect(fs.readFileSync(await download.path(), 'utf8')).toBe(source);
  await expect(page.locator('#message')).toContainText('Markdown downloaded.');
});

test('viewer downloads a self-contained article with image, KaTeX, and Mermaid data', async ({ page }) => {
  const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64');
  await page.route('**/pages/SelfContainedFixture.md', route => route.fulfill({
    status: 200,
    contentType: 'text/markdown; charset=utf-8',
    body: '# Self Contained Fixture\n\n![pixel](assets/pixel.png)\n\n$$x^2$$\n\n```mermaid\ngraph LR\nA --> B\n```',
  }));
  await page.route('**/pages/assets/pixel.png', route => route.fulfill({ status: 200, contentType: 'image/png', body: png }));
  await page.goto(`${knowledgeUrl}/viewer.html?f=pages%2FSelfContainedFixture.md`);
  await expect(page.locator('.mermaid svg')).toBeVisible({ timeout: 30_000 });
  const downloadPromise = page.waitForEvent('download');
  await chooseExport(page, '下载当前页面', '自包含 .html');
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('Self Contained Fixture.html');
  const html = fs.readFileSync(await download.path(), 'utf8');
  expect(html).toContain('<!doctype html>');
  expect(html).toContain('<title>Self Contained Fixture</title>');
  expect(html).toMatch(/src="data:image\/png;base64,/);
  expect(html).toMatch(/url\(["']?data:font\/woff2;base64,/);
  expect(html).toContain('class="katex"');
  expect(html).toContain('<svg');
  expect(html).not.toContain('export-actions');
  expect(html).not.toContain('id="sidebar"');
  expect(html).not.toContain('<script');
  expect(html).not.toContain('vendor/katex');
});

test('viewer refuses partial HTML when a required image cannot be embedded', async ({ page }) => {
  await page.route('**/pages/BrokenAssetFixture.md', route => route.fulfill({
    status: 200,
    contentType: 'text/markdown; charset=utf-8',
    body: '# Broken Asset Fixture\n\n![missing](assets/missing.png)',
  }));
  await page.route('**/pages/assets/missing.png', route => route.fulfill({ status: 404, body: 'missing' }));
  await page.goto(`${knowledgeUrl}/viewer.html?f=pages%2FBrokenAssetFixture.md`);
  let downloads = 0;
  page.on('download', () => { downloads += 1; });
  await chooseExport(page, '下载当前页面', '自包含 .html');
  await expect(page.getByRole('alert')).toContainText('assets/missing.png');
  await page.waitForTimeout(200);
  expect(downloads).toBe(0);
  await expect(page.getByRole('menuitem', { name: '自包含 .html' })).toBeVisible();
});

test('viewer export always reads the final active page after rapid navigation', async ({ page }) => {
  await installClipboardCapture(page);
  await page.route('**/pages/SlowExport.md', async route => {
    await new Promise(resolve => setTimeout(resolve, 250));
    await route.fulfill({ status: 200, contentType: 'text/markdown', body: '# Slow Export\n\nstale-body' });
  });
  await page.route('**/pages/FinalExport.md', route => route.fulfill({
    status: 200, contentType: 'text/markdown', body: '# Final Export\n\nfinal-body',
  }));
  await page.goto(`${knowledgeUrl}/viewer.html?f=%E9%A6%96%E9%A1%B5.md`);
  await page.evaluate(() => {
    window.slowExportNavigation = navigateTo('pages/SlowExport.md', { sectionHint: 'knowledge', historyMode: 'push' });
    window.finalExportNavigation = navigateTo('pages/FinalExport.md', { sectionHint: 'knowledge', historyMode: 'push' });
  });
  await expect(page.locator('#content h1')).toHaveText('Final Export');
  await page.waitForTimeout(300);
  await chooseExport(page, '复制当前页面', '原始 Markdown');
  await expect.poll(() => page.evaluate(() => window.__clipboardWrites.at(-1)?.text)).toBe('# Final Export\n\nfinal-body');
});

test('refresh invalidates cached section indexes before recovery', async ({ page }) => {
  let indexRequests = 0;
  page.on('request', request => {
    if (new URL(request.url()).pathname === '/_index.md') indexRequests += 1;
  });
  await page.goto(`${knowledgeUrl}/viewer.html?f=pages%2FK%E8%BF%91%E9%82%BB%20KNN%20K-Nearest%20Neighbors.md`);
  await expect(page.locator('#content h1')).toContainText('K近邻');
  expect(indexRequests).toBe(1);

  const ok = await page.evaluate(() => refreshActiveSurface('knowledge'));

  expect(ok).toBe(true);
  expect(indexRequests).toBe(2);
  await expect(page.locator('#content h1')).toContainText('K近邻');
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
