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
3. 先检查 Markdown 原始结构是否适合直接渲染：
   - 如果已经有明确层级（标题、小节、列表、引用、强调），可直接进入清洗
   - 如果整体接近纯文本长段落、层级弱、分页后可读性差，必须先做一次格式增强
4. 格式增强时，优先只改 Markdown 结构，不先改模板：
   - 补充标题层级（如 `##` / `###`）
   - 将长段拆成短段
   - 为结论、提醒、金句增加引用块 `> `
   - 为并列信息增加列表或 checklist
   - 为关键信息增加 `**加粗**`
   - 保持原文观点和信息不变，不凭空扩写结论
5. 生成：
   - `assets/source.md`
   - `assets/cleaned.md`
6. 渲染输出到该 candidate 的 `assets/`
7. 默认使用 `dark` 主题，除非任务明确指定其他主题；`memo` 主题默认无封面，直接输出分页图

格式增强判断建议：

- 满足任一情况时，默认先增强格式再渲染：
  - 正文大部分是连续长段，几乎没有小标题
  - 全文缺少列表、引用、强调，页面视觉层次单一
  - 主题为 `memo`，且内容更适合“备忘录式信息分层”而非整段阅读
- 增强目标是“提高分页后的阅读效率和视觉节奏”，不是重写文案风格

示例：

```bash
node scripts/render_xhs_v2.js \
  ../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/assets/cleaned.md \
  --output-dir ../redbook-auto-flow/workspace/{run_id}/candidates/{candidate_id}/assets \
  --style dark
```

模板调试：

- 模板文件在 `assets/styles.css`、`assets/cover.html`、`assets/card.html`
- `memo` 长页模板在 `assets/memo_card.html`、`assets/memo_styles.css`
- 只导出 HTML 预览可使用 `node scripts/render_xhs_v2.js ... --html-only`
- 主题切换预览页在 `theme-preview.html`
- skill 默认主题为 `dark`
- `memo` 的分页逻辑为“先长图渲染，再按 1440px 高度和 96px 重叠裁切”

## 约束

- 一个任务下多个 candidate 可以分别配图
- 不能把不同 candidate 的图片输出到同一个目录
- 输入来自 `redbook-writer` 产出的某个 `candidate_id/drafts/final.md`
- 如果原始 Markdown 可读性不足，应先生成适合渲染的增强版 `assets/cleaned.md`，再出图
- 默认先做“结构增强”，只有在 Markdown 增强仍不足时，才考虑修改模板/CSS
