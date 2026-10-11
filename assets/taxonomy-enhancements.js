(function () {
  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  async function enrich() {
    try {
      const response = await fetch('graph-data.json', { cache: 'no-store' });
      if (!response.ok) return;
      const taxonomy = (await response.json()).taxonomy || {};
      const candidates = new Map((taxonomy.candidates || []).map((item) => [item.id, item]));
      const memberships = taxonomy.memberships || [];
      const membersByCategory = new Map();
      memberships.forEach((item) => {
        if (!membersByCategory.has(item.category)) membersByCategory.set(item.category, []);
        membersByCategory.get(item.category).push(item.page);
      });
      document.querySelectorAll('#candidates .row[data-id]').forEach((row) => {
        const item = candidates.get(row.dataset.id);
        if (!item) return;
        const score = Number(item.cohesion_score);
        const note = document.createElement('span');
        note.className = 'meta taxonomy-explanation';
        note.textContent = `形成信号：${Object.keys(item.signals || {}).join('、') || '未记录'} · 内聚度：${Number.isFinite(score) ? score.toFixed(3) : '未记录'} · 目标：${item.target_size || '未记录'}`;
        row.append(note);
        row.title = `候选成员：${(item.members || []).join('、')}；相关类别：${(item.related_category_ids || []).join('、') || '无'}`;
      });
      document.querySelectorAll('#categories .row[data-id]').forEach((row) => {
        const members = membersByCategory.get(row.dataset.id) || [];
        if (!members.length) return;
        const note = document.createElement('span');
        note.className = 'meta taxonomy-explanation';
        note.textContent = `成员归属：${members.length} · 代表页面：${members.slice(0, 3).join('、')}`;
        row.append(note);
      });
    } catch (_) {
      // The core taxonomy page already has its own error and retry state.
    }
  }
  window.addEventListener('load', () => window.setTimeout(enrich, 120));
})();
