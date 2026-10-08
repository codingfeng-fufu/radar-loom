# 贡献指南

## 开始之前

请先阅读 `README.md` 和 `CLAUDE.md`。知识页使用 UTF-8 Markdown，页面之间用 `[[页面名]]` 建立显式引用。

## 本地检查

提交前运行：

```bash
python3 scripts/build_index.py
python3 scripts/render_graph.py
python3 scripts/check_health.py
python3 scripts/taxonomy_cli.py validate
npm run test:python
node scripts/ci_node_checks.mjs
```

健康检查应为 `ERROR 0 / WARN 0`。不要提交 API Key、Claude 会话状态、个人备份、PDF 原始材料或本机绝对路径。

## 页面变更

新增或更新页面时，请保留真实来源、摘要、信度和更新记录。公式使用 LaTeX 定界符。机器生成的索引和图谱通过脚本更新，不手工编辑。

## Pull Request

说明变更内容、验证命令和任何需要本机服务才能复现的部分。涉及 WebUI 的改动还应说明外部 WebUI 版本和补丁来源。
