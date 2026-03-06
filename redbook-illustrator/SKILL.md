---
name: redbook-illustrator
description: >
  小红书配图生成技能。读取 redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/drafts/final.md，
  并把图片输出到同一 candidate 的 assets 目录。
---

# 小红书笔记配图生成器

本 skill 负责把确认后的候选文案渲染成小红书图文卡片。

## 标准输入输出

输入文案：

- `{skill_path}/../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/drafts/final.md`

中间文件：

- `{skill_path}/../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/assets/source.md`
- `{skill_path}/../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/assets/cleaned.md`

输出图片：

```text
{skill_path}/../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/assets/
├── cover.png
├── card_1.png
├── card_2.png
└── card_*.png
```

## 标准流程

1. 明确目标 `candidate_id`
2. 只读取该 candidate 的 `drafts/final.md`
3. 生成：
   - `assets/source.md`
   - `assets/cleaned.md`
4. 渲染输出到该 candidate 的 `assets/`
5. 默认使用 `dark` 主题，除非任务明确指定其他主题

示例：

```bash
node scripts/render_xhs_v2.js \
  ../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/assets/cleaned.md \
  --output-dir ../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/assets \
  --style dark
```

模板调试：

- 模板文件在 `assets/styles.css`、`assets/cover.html`、`assets/card.html`
- 只导出 HTML 预览可使用 `node scripts/render_xhs_v2.js ... --html-only`
- 主题切换预览页在 `theme-preview.html`
- skill 默认主题为 `dark`

## 约束

- 一个任务下多个 candidate 可以分别配图
- 不能把不同 candidate 的图片输出到同一个目录
- 输入来自 `redbook-writer` 产出的某个 `candidate_id/drafts/final.md`
