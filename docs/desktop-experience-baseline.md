# Web 操作台桌面体验基线

## 验收环境

- 日期：2026-07-23
- 外层工作台：`http://127.0.0.1:18080/`
- 知识库服务：`http://127.0.0.1:18081/`
- 桌面视口：`1440×900`、`1112×1243`
- 证据目录：`output/playwright/desktop-baseline/`

## 问题记录

| ID | 旅程阶段 | 视口 | 复现步骤 | 期望 | 实际 | 证据 | 优先级 | 状态 |
|---|---|---|---|---|---|---|---|---|
| DX-001 | 进入与恢复 | 两者 | 将分栏设为 64%，整页刷新 | 恢复 64% | 回到默认 58% | `restores split width after a full page reload`：期望 `64`，实际 `58` | P0 | 已复现 |

## 场景盘点

| 场景 | 基线结果 | 证据 |
|---|---|---|
| 冷启动与双栏恢复 | 工作台可用；自定义分栏不恢复 | 两视口烟测通过；DX-001 失败 |
| 搜索并阅读复杂页 | 含公式的 DDPM 页可渲染，无根横向溢出 | `complex knowledge pages and graph render without public network resources` |
| 图谱模式、筛选、节点和刷新恢复 | 模式按钮可用；完整恢复在 Task 5 验收 | `desktop graph controls are not blocked by the mobile scrim` |
| 连续两次询问 Claude | 通过，两次均进入受控 textarea | `second ask-Claude insertion updates the controlled textarea` |
| 打开长历史会话 | 通过，`shell.scrollTop=0`，Composer 贴底 | `opening a long history keeps the composer at the viewport bottom` |
| Claude 401、429、流中断与本机不可用 | 现有错误未统一为用户可执行表达 | Task 6 建立映射契约 |
| 创建页面后定位结果 | Skill 已报告路径与验证，两类页的输出顺序不统一 | Task 7 契约 |
| 双服务重启后恢复 | 服务支持幂等启动；全现场恢复待 Task 9 重启验收 | `webui-control status`、`kbserve-control status` |
| 阻断公网资源 | 通过，KaTeX 和 Cytoscape 使用本地资源 | `complex knowledge pages and graph render without public network resources` |
| 连续完成整条旅程 | 尚未形成单一连续回归，现有分段用例可用 | Task 9 完整旅程用例 |
