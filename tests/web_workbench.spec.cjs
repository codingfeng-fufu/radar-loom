const { test, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const viewerBase = process.env.KB_VIEWER_URL || 'http://127.0.0.1:18081';
const samplePage = '多头注意力机制的核心作用是什么';
const sampleFile = `pages/${samplePage}.md`;
const artifactDir = process.env.E2E_ARTIFACT_DIR || '/tmp/engineering-interview-e2e';

test('interview insertion helpers distinguish direct and clipboard outcomes', async () => {
  const helpers = await import(pathToFileURL('/home/u2023312337/webui/patch-integrated-workbench.mjs').href);
  expect(helpers.interviewInsertionClears({ inserted: true, method: 'direct' })).toBe(true);
  expect(helpers.interviewInsertionClears({ inserted: true, method: 'clipboard' })).toBe(false);
  expect(helpers.interviewInsertionClears({ inserted: false, method: 'clipboard' })).toBe(false);
  expect(helpers.buildInterviewPrompt({
    question: '多头注意力为什么有效？',
    paths: ['raw/inbox/mha-e2e.txt'],
    focus: '区分表示能力与可解释性',
  })).toBe([
    '请使用 $create-engineering-interview-page Skill 完成工程面试页创建或更新任务。',
    '面试问题：多头注意力为什么有效？',
    '参考材料：raw/inbox/mha-e2e.txt',
    '特别关注：区分表示能力与可解释性',
    '如材料包含多道问题，先列出问题清单、建议标题和推测难度，等待我确认后再建页。',
  ].join('\n'));
});

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

test('engineering interview workspace supports authored sample, filters, graph, state, and upload', async ({ page }) => {
  const consoleErrors = [];
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  await page.route('http://127.0.0.1:18080/assets/claude.html', route => route.fulfill({
    contentType: 'text/html',
    body: '<!doctype html><html><body><textarea aria-label="Claude prompt"></textarea></body></html>',
  }));
  await page.goto('http://127.0.0.1:18080/');

  const frame = () => page.frames().find(candidate => candidate.url().startsWith(viewerBase));
  const viewer = page.frameLocator('#knowledgeFrame');
  await viewer.locator('#interviewTab').click();
  await expect(viewer.locator('#interviewTab')).toHaveAttribute('aria-selected', 'true');
  await expect(viewer.getByRole('link', { name: samplePage }).first()).toBeVisible();
  fs.mkdirSync(artifactDir, { recursive: true });
  await page.screenshot({ path: path.join(artifactDir, 'engineering-interview-list.png'), fullPage: true });

  await viewer.locator('#roleFilter').selectOption('算法工程师');
  await viewer.locator('#difficultyFilter').selectOption('进阶');
  await viewer.locator('#tagFilter').selectOption('Transformer');
  await expect(viewer.locator('.search-card:visible')).toHaveCount(1);
  await viewer.locator('.search-card').filter({ hasText: samplePage }).click();
  await expect(viewer.locator('#content h1')).toHaveText(samplePage);
  await expect(viewer.locator('#content')).toContainText('多头注意力机制的核心作用到底是什么？');
  await expect(viewer.locator('#content')).toContainText('多个可学习的表示子空间');
  await expect(viewer.locator('#content')).toContainText('不保证');
  await page.screenshot({ path: path.join(artifactDir, 'engineering-interview-sample-page.png'), fullPage: true });
  await frame().evaluate(() => location.reload());
  await expect(viewer.locator('#interviewTab')).toHaveAttribute('aria-selected', 'true');
  await expect(viewer.locator('#roleFilter')).toHaveValue('算法工程师');
  await expect(viewer.locator('#difficultyFilter')).toHaveValue('进阶');
  await expect(viewer.locator('#tagFilter')).toHaveValue('Transformer');
  await expect(viewer.locator('#content h1')).toHaveText(samplePage);

  await frame().evaluate(() => { location.href = 'graph-view.html?profile=interview'; });
  const graph = page.frameLocator('#knowledgeFrame');
  await expect(graph.locator('#graph canvas').first()).toBeVisible();
  await expect(graph.locator('#nodeCount')).toHaveText('1');
  await page.screenshot({ path: path.join(artifactDir, 'engineering-interview-graph.png'), fullPage: true });
  await graph.locator('#search').fill('多头注意力');
  await expect(graph.locator('.search-result').filter({ hasText: samplePage })).toBeVisible();
  await expect(graph.locator('.search-result').filter({ hasText: 'Multi-Head Attention' })).toBeVisible();
  await graph.locator('.search-result').filter({ hasText: 'Multi-Head Attention' }).click();
  await graph.getByRole('link', { name: '在 Viewer 打开' }).click();
  await expect.poll(() => new URL(frame().url()).pathname).toContain('/viewer.html');
  await expect.poll(() => decodeURIComponent(new URL(frame().url()).searchParams.get('f') || '')).toContain('多头注意力 Multi-Head Attention.md');
  await frame().evaluate(() => history.back());
  await expect.poll(() => new URL(frame().url()).pathname).toContain('/graph-view.html');
  await frame().evaluate(() => location.reload());
  await expect(page.frameLocator('#knowledgeFrame').locator('#graph canvas').first()).toBeVisible();
  await frame().evaluate(() => history.back());
  await expect.poll(() => new URL(frame().url()).pathname).toContain('/viewer.html');
  await expect(viewer.locator('#interviewTab')).toHaveAttribute('aria-selected', 'true');
  await expect(viewer.locator('#roleFilter')).toHaveValue('算法工程师');
  await expect(viewer.locator('#difficultyFilter')).toHaveValue('进阶');
  await expect(viewer.locator('#tagFilter')).toHaveValue('Transformer');
  await expect(viewer.locator('#content h1')).toHaveText(samplePage);

  const fixture = Buffer.from('多头注意力与表示子空间\n', 'utf8');
  await page.locator('#createInterview').click();
  await page.locator('#interviewQuestion').fill('多头注意力为什么有效？');
  await page.locator('#interviewFocus').fill('区分表示能力与可解释性');
  await page.locator('#interviewFiles').setInputFiles({ name: 'mha-e2e.txt', mimeType: 'text/plain', buffer: fixture });
  await page.locator('#insertInterviewPrompt').click();
  await expect(page.locator('#insertInterviewPrompt')).toBeEnabled();
  await expect(page.locator('#createInterviewDialog')).not.toHaveAttribute('open', '');
  const prompt = await page.frameLocator('#claudeFrame').getByRole('textbox', { name: 'Claude prompt' }).inputValue();
  expect(prompt).toContain('$create-engineering-interview-page Skill');
  expect(prompt).toContain('raw/inbox/');
  expect(prompt).toContain('mha-e2e.txt');
  expect(prompt).toContain('如材料包含多道问题，先列出问题清单、建议标题和推测难度，等待我确认后再建页。');
  await expect(page.locator('#interviewFiles')).toHaveValue('');

  await page.frameLocator('#claudeFrame').locator('body').evaluate(body => body.replaceChildren());
  await page.evaluate(() => {
    window.__clipboardText = '';
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: async text => { window.__clipboardText = text; } },
    });
  });
  await page.locator('#createInterview').click();
  await page.locator('#interviewQuestion').fill('剪贴板回退题目');
  await page.locator('#interviewFocus').fill('剪贴板回退关注点');
  await page.locator('#interviewFiles').setInputFiles({ name: 'mha-clipboard-e2e.txt', mimeType: 'text/plain', buffer: fixture });
  await page.locator('#insertInterviewPrompt').click();
  await expect(page.locator('#insertInterviewPrompt')).toBeEnabled();
  await expect(page.locator('#createInterviewDialog')).toHaveAttribute('open', '');
  const clipboardPrompt = await page.evaluate(() => window.__clipboardText);
  expect(clipboardPrompt).toBe([
    '请使用 $create-engineering-interview-page Skill 完成工程面试页创建或更新任务。',
    '面试问题：剪贴板回退题目',
    '参考材料：raw/inbox/mha-clipboard-e2e.txt',
    '特别关注：剪贴板回退关注点',
    '如材料包含多道问题，先列出问题清单、建议标题和推测难度，等待我确认后再建页。',
  ].join('\n'));
  await expect(page.locator('#interviewQuestion')).toHaveValue('剪贴板回退题目');
  await expect(page.locator('#interviewFocus')).toHaveValue('剪贴板回退关注点');
  await expect(page.locator('#interviewFiles')).toHaveValue(/mha-clipboard-e2e\.txt$/);
  await page.locator('#cancelCreateInterview').click();

  await page.route('**/api/uploads', route => route.fulfill({
    status: 415,
    contentType: 'application/json',
    body: JSON.stringify({ ok: false, error: '测试上传失败' }),
  }));
  await page.locator('#createInterview').click();
  await page.locator('#interviewQuestion').fill('上传失败题目');
  await page.locator('#interviewFocus').fill('上传失败关注点');
  await page.locator('#interviewFiles').setInputFiles({ name: 'mha-error-e2e.txt', mimeType: 'text/plain', buffer: fixture });
  await page.screenshot({ path: path.join(artifactDir, 'engineering-interview-upload-dialog.png'), fullPage: true });
  await page.locator('#insertInterviewPrompt').click();
  await expect(page.locator('#createInterviewError')).toHaveText('测试上传失败');
  await expect(page.locator('#createInterviewDialog')).toHaveAttribute('open', '');
  await expect(page.locator('#interviewQuestion')).toHaveValue('上传失败题目');
  await expect(page.locator('#interviewFocus')).toHaveValue('上传失败关注点');
  await expect(page.locator('#interviewFiles')).toHaveValue(/mha-error-e2e\.txt$/);
  await page.locator('#cancelCreateInterview').click();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('tab', { name: '文件' }).click();
  await expect(page.locator('#workbench')).toHaveAttribute('data-mobile-tab', 'files');
  await page.getByRole('tab', { name: '预览' }).click();
  await expect(page.locator('#workbench')).toHaveAttribute('data-mobile-tab', 'preview');
  await viewer.locator('#scrim').evaluate(element => element.click());
  await expect(viewer.locator('body')).not.toHaveClass(/nav-open/);
  await page.waitForTimeout(350);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await frame().evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: path.join(artifactDir, 'engineering-interview-mobile.png'), fullPage: true });
  const unexpectedConsoleErrors = consoleErrors.filter(message => !message.includes('status of 415 (Unsupported Media Type)'));
  expect(unexpectedConsoleErrors).toEqual([]);
  expect(consoleErrors.filter(message => message.includes('status of 415 (Unsupported Media Type)'))).toHaveLength(1);
});
