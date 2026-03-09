---
name: redbook-ops-planner
description: 小红书运营规划技能。基于指定账号的最新内容数据和垂类外部热点，生成当天搜索词、规划摘要，并把结构化运营计划挂到 redbook-auto-flow 的 workspace，作为 search -> writer -> illustrator -> publish 的上游输入。
---

# 小红书运营规划器

本 skill 只负责每日运营规划，不负责写作、配图和最终发布。

工作边界：

- 读取账号最新内容数据：调用 `redbook-operator/scripts/cdp_publish.py content-data`
- 读取垂类外部热点：当前默认使用可替换的 RSS provider
- 生成当天关键词与规划摘要
- 把规划结果挂到 `redbook-auto-flow/workspace/{run_id}/inputs/ops_ref.json`

本 skill 不负责：

- 直接写文案
- 渲染图片
- 自动发布

共享规划数据目录：

- `{skill_path}/../redbook-auto-flow/data-sources/ops/{plan_id}/`

单次任务工作区：

- `{skill_path}/../redbook-auto-flow/workspace/{run_id}/`

## 标准产物

```text
data-sources/ops/{plan_id}/
├── manifest.json
├── account_snapshot.json
├── account_snapshot.csv
├── trend_briefs.json
├── trend_briefs.md
├── daily_keywords.json
└── planning_summary.md
```

`plan_id` 推荐格式：

- `ops_{account}_{domain}_{YYYYMMDD}`

## 标准流程

### 1. 采集账号快照

```bash
python scripts/collect_account_snapshot.py \
  --account {account_name} \
  --domain "AI 工具"
```

输出：

- `account_snapshot.json`
- `account_snapshot.csv`

### 2. 采集垂类热点

```bash
python scripts/collect_trends.py \
  --account {account_name} \
  --domain "AI 工具"
```

输出：

- `trend_briefs.json`
- `trend_briefs.md`

### 3. 生成每日规划

```bash
python scripts/build_daily_plan.py \
  --account {account_name} \
  --domain "AI 工具"
```

输出：

- `daily_keywords.json`
- `planning_summary.md`
- `manifest.json`

### 4. 创建 run 并挂载 ops 计划

```bash
python ../redbook-auto-flow/scripts/init_run.py \
  --topic "{selected_keyword}" \
  --source-type ops

python scripts/attach_ops_plan.py \
  --run-id {run_id} \
  --plan-id {plan_id}
```

输出：

- `workspace/{run_id}/inputs/ops_ref.json`

### 5. 可选：直接把 selected_keyword 送入现有搜索导入链路

```bash
python ../redbook-auto-flow/scripts/materialize_ops_search_dataset.py \
  --run-id {run_id}
```

这一步会继续触发：

- `redbook-operator search-feeds`
- `import_xhs_search_payload.py`
- `attach_dataset.py`

并生成或更新：

- `workspace/{run_id}/inputs/data_ref.json`

## 高层入口

如果要一条命令完成“采集账号数据 -> 采集热点 -> 生成规划 -> 建 run -> 挂 ops_ref”，使用：

```bash
python scripts/run_daily_ops.py \
  --account {account_name} \
  --domain "AI 工具"
```

如需进一步把 `selected_keyword` 直接送入现有搜索导入链路，可加：

```bash
python scripts/run_daily_ops.py \
  --account {account_name} \
  --domain "AI 工具" \
  --materialize-search-dataset
```

## 约束

- 第一版只面向单账号
- 第一版账号信号只使用 `content-data`
- 第一版只做垂类热点，不混排泛热点
- 默认每天只推进 1 个 `selected_keyword`
- `ops_ref.json` 与 `data_ref.json` 必须分开维护
- 最终发布仍应保留人工确认闸门
