# GitHub 发布清单

## 已准备

- 核心运行时只依赖仓库路径，不依赖固定用户目录。
- 本地凭据、运行时环境、备份、日志和测试产物已加入忽略规则。
- `README.md` 提供从克隆到启动 Viewer 的最短路径。
- `CONTRIBUTING.md`、`SECURITY.md` 和 MIT `LICENSE` 已加入。
- GitHub Actions 覆盖 Python 测试、Node 契约检查和生成物健康检查。
- 生成索引、图谱、社区数据和 taxonomy 的命令可以在仓库根目录执行。

## 不随仓库发布

- Claude WebUI 安装目录、Claude 会话配置和外部控制脚本；
- API Key、Token、运行日志和本地备份；
- 原始论文 PDF 与上传材料；
- `.superpowers/`、浏览器截图和 E2E 临时文本；
- 指向个人目录或其他私有项目的本机绝对路径。

## 上传前人工确认

1. 检查 `git status --short`，确认没有个人材料或凭据文件。
2. 检查 `git diff --check`。
3. 运行 `npm run refresh:artifacts`。
4. 运行 `npm run test:python` 和 `node scripts/ci_node_checks.mjs`。
5. 检查 `git grep -n -I '/home/'` 没有个人路径残留；测试中用于模拟 Claude 项目 URL 的固定字符串除外。
6. 在 GitHub 创建空仓库后添加远程地址，再推送 `master` 或改名后的默认分支。

项目当前没有自动推送逻辑；远程仓库地址和推送动作由维护者明确执行。
