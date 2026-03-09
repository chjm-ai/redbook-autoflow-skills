# 新增功能计划：redbook-ops-planner 运营规划层

## 目标
- 新增独立 skill：`redbook-ops-planner`，作为 `redbook-auto-flow` 的上游运营决策层。
- 每日沉淀账号快照、垂类热点、搜索词与规划摘要到 `redbook-auto-flow/data-sources/ops/{plan_id}/`。
- 为 `workspace/{run_id}/inputs/` 增加 `ops_ref.json`，与现有 `data_ref.json` 分离。
- 提供高层入口，支持从“最新账号数据 + 外部热点”一路跑到“已准备好搜索输入”。

## 实施步骤
- [x] 新增 `redbook-ops-planner/` 目录与 `SKILL.md`、`requirements.txt`、`plan.md`。
- [x] 在 `redbook-ops-planner/scripts/` 实现账号快照采集、热点采集、日计划生成、挂载、总入口脚本。
- [x] 为热点源保留 provider 抽象，第一版接入一个可替换的 RSS provider。
- [x] 在 `redbook-auto-flow` 增加 `ops_ref.json` 约定及搜索数据集衔接脚本。
- [x] 更新 `redbook-auto-flow` 元数据结构，记录 `ops_plan_id`、`selected_keyword`、`account`。
- [x] 同步更新仓库根 README、`redbook-auto-flow/SKILL.md`、`redbook-writer/SKILL.md`。
- [x] 补充最小自动化测试，覆盖快照规范化、热点去重、关键词生成、`ops_ref.json` 写入与搜索数据集衔接。
