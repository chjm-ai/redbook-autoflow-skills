#!/usr/bin/env node
/**
 * 小红书卡片渲染脚本 V2 - Node.js 智能分页版
 * 将 Markdown 文件渲染为小红书风格的图片卡片
 * 
 * 新特性：
 * 1. 智能分页：自动检测内容高度，超出时自动拆分到多张卡片
 * 2. 多种样式：支持多种预设样式主题
 * 
 * 使用方法:
 *   node render_xhs_v2.js <markdown_file> [options]
 * 
 * 依赖安装:
 *   npm install marked js-yaml playwright
 *   npx playwright install chromium
 */

const fs = require('fs');
const path = require('path');
const AUTO_FLOW_ROOT = path.join(__dirname, '..', '..', 'redbook-auto-flow');
const DEFAULT_OUTPUT_DIR = path.join(AUTO_FLOW_ROOT, 'workspace');
const { chromium } = require('playwright');
const { marked } = require('marked');
const yaml = require('js-yaml');

// 获取脚本所在目录
const SCRIPT_DIR = path.dirname(__dirname);
const ASSETS_DIR = path.join(SCRIPT_DIR, 'assets');
const TEMPLATE_CACHE = new Map();

// 卡片尺寸配置 (3:4 比例)
const CARD_WIDTH = 1080;
const CARD_HEIGHT = 1440;

// 内容区域安全高度
const SAFE_HEIGHT = CARD_HEIGHT - 120 - 100 - 80 - 40; // ~1100px

// 样式配置
const STYLES = {
    purple: {
        name: "紫韵",
        mode: "light",
        cover_bg: "linear-gradient(180deg, #3450E4 0%, #D266DA 100%)",
        card_bg: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        accent_color: "#6366f1",
    },
    xiaohongshu: {
        name: "小红书红",
        mode: "light",
        cover_bg: "linear-gradient(180deg, #FF2442 0%, #FF6B81 100%)",
        card_bg: "linear-gradient(135deg, #FF2442 0%, #FF6B81 100%)",
        accent_color: "#FF2442",
    },
    mint: {
        name: "清新薄荷",
        mode: "light",
        cover_bg: "linear-gradient(180deg, #43e97b 0%, #38f9d7 100%)",
        card_bg: "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)",
        accent_color: "#43e97b",
        card_surface: "rgba(249, 255, 252, 0.96)",
        title_gradient: "linear-gradient(180deg, #0f766e 0%, #134e4a 100%)",
        text_primary: "#134e4a",
        text_secondary: "#115e59",
        text_tertiary: "#0f766e",
        text_muted: "#4b5563",
        surface_muted: "#dffcf2",
        border_color: "#a7f3d0",
        code_surface: "#dcfce7",
        pre_surface: "#134e4a",
        pre_text: "#ecfdf5",
        page_number_color: "rgba(10, 60, 52, 0.45)",
    },
    sunset: {
        name: "日落橙",
        mode: "light",
        cover_bg: "linear-gradient(180deg, #fa709a 0%, #fee140 100%)",
        card_bg: "linear-gradient(135deg, #fa709a 0%, #fee140 100%)",
        accent_color: "#fa709a",
        cover_inner_background: "#fff7ed",
        title_gradient: "linear-gradient(180deg, #9a3412 0%, #7c2d12 100%)",
        text_primary: "#7c2d12",
        text_secondary: "#9a3412",
        text_tertiary: "#c2410c",
        text_muted: "#9a3412",
        surface_muted: "#ffedd5",
        border_color: "#fdba74",
        code_surface: "#ffedd5",
        pre_surface: "#7c2d12",
        pre_text: "#fff7ed",
    },
    ocean: {
        name: "深海蓝",
        mode: "light",
        cover_bg: "linear-gradient(180deg, #4facfe 0%, #00f2fe 100%)",
        card_bg: "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",
        accent_color: "#4facfe",
        cover_inner_background: "#f0f9ff",
        title_gradient: "linear-gradient(180deg, #0f172a 0%, #0369a1 100%)",
        text_primary: "#082f49",
        text_secondary: "#0c4a6e",
        text_tertiary: "#075985",
        text_muted: "#155e75",
        surface_muted: "#e0f2fe",
        border_color: "#7dd3fc",
        code_surface: "#e0f2fe",
        pre_surface: "#082f49",
        pre_text: "#e0f2fe",
    },
    elegant: {
        name: "优雅白",
        mode: "light",
        cover_bg: "linear-gradient(180deg, #f5f5f5 0%, #e0e0e0 100%)",
        card_bg: "linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%)",
        accent_color: "#333333",
        cover_inner_background: "#fafaf9",
        title_gradient: "linear-gradient(180deg, #292524 0%, #57534e 100%)",
        text_primary: "#292524",
        text_secondary: "#44403c",
        text_tertiary: "#57534e",
        text_muted: "#78716c",
        surface_muted: "#f5f5f4",
        border_color: "#d6d3d1",
        code_surface: "#f5f5f4",
        pre_surface: "#1c1917",
        pre_text: "#f5f5f4",
        page_number_color: "rgba(41, 37, 36, 0.4)",
    },
    dark: {
        name: "暗黑模式",
        mode: "dark",
        cover_bg: "linear-gradient(180deg, #1a1a2e 0%, #16213e 100%)",
        card_bg: "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)",
        accent_color: "#e94560",
    },
    botanical: {
        name: "植物园",
        mode: "light",
        cover_bg: "linear-gradient(180deg, #6aa57b 0%, #d6ead7 100%)",
        card_bg: "linear-gradient(135deg, #8bcf98 0%, #eef8ea 100%)",
        accent_color: "#2f855a",
        cover_inner_background: "#f8f5ec",
        title_gradient: "linear-gradient(180deg, #1f4d3a 0%, #5a7f62 100%)",
        subtitle_color: "#345c46",
        card_surface: "rgba(250, 247, 238, 0.96)",
        text_primary: "#1f3b2f",
        text_secondary: "#365844",
        text_tertiary: "#4d6b57",
        text_muted: "#647766",
        surface_muted: "#edf4ea",
        border_color: "#cfe2cf",
        code_surface: "#edf4ea",
        pre_surface: "#213a2f",
        pre_text: "#eaf5eb",
        card_shadow: "0 14px 38px rgba(35, 63, 45, 0.14)",
        page_number_color: "rgba(31, 59, 47, 0.4)",
    },
    retro: {
        name: "复古海报",
        mode: "light",
        cover_bg: "linear-gradient(180deg, #f3d6b3 0%, #dd8452 100%)",
        card_bg: "linear-gradient(135deg, #f4d8b8 0%, #c96f44 100%)",
        accent_color: "#a63d2f",
        cover_inner_background: "#fff3df",
        title_gradient: "linear-gradient(180deg, #7a2e22 0%, #c75b3d 100%)",
        subtitle_color: "#7a2e22",
        card_surface: "rgba(255, 244, 225, 0.95)",
        text_primary: "#5c2418",
        text_secondary: "#7a2e22",
        text_tertiary: "#93412d",
        text_muted: "#8a5b48",
        surface_muted: "#f8e4c7",
        border_color: "#d9a574",
        code_surface: "#f6dfc2",
        pre_surface: "#5c2418",
        pre_text: "#fff2dd",
        card_shadow: "0 10px 0 rgba(92, 36, 24, 0.22)",
        page_number_color: "rgba(92, 36, 24, 0.45)",
    },
    brutalist: {
        name: "新粗野",
        mode: "light",
        cover_bg: "linear-gradient(180deg, #ffe600 0%, #ff8a00 100%)",
        card_bg: "linear-gradient(135deg, #fff27a 0%, #ffb400 100%)",
        accent_color: "#111111",
        cover_inner_background: "#fffdf5",
        title_gradient: "linear-gradient(180deg, #111111 0%, #2f2f2f 100%)",
        subtitle_color: "#111111",
        card_surface: "rgba(255, 255, 255, 0.98)",
        text_primary: "#111111",
        text_secondary: "#1f2937",
        text_tertiary: "#111827",
        text_muted: "#374151",
        surface_muted: "#fff7b8",
        border_color: "#111111",
        code_surface: "#fff7b8",
        pre_surface: "#111111",
        pre_text: "#fef3c7",
        card_shadow: "12px 12px 0 rgba(17, 17, 17, 0.95)",
        radius: "8px",
        page_number_color: "rgba(17, 17, 17, 0.55)",
    },
    sakura: {
        name: "樱雾粉",
        mode: "light",
        cover_bg: "linear-gradient(180deg, #ffd1dc 0%, #ffe7ef 100%)",
        card_bg: "linear-gradient(135deg, #ffc7d7 0%, #fff1f5 100%)",
        accent_color: "#e8799e",
        cover_inner_background: "#fffafc",
        title_gradient: "linear-gradient(180deg, #831843 0%, #be185d 100%)",
        subtitle_color: "#9d174d",
        card_surface: "rgba(255, 250, 252, 0.96)",
        text_primary: "#831843",
        text_secondary: "#9d174d",
        text_tertiary: "#be185d",
        text_muted: "#a35d76",
        surface_muted: "#ffe4ec",
        border_color: "#f9a8d4",
        code_surface: "#ffe4ec",
        pre_surface: "#831843",
        pre_text: "#fff1f5",
        card_shadow: "0 12px 34px rgba(190, 24, 93, 0.16)",
        page_number_color: "rgba(131, 24, 67, 0.35)",
    },
    midnight: {
        name: "午夜霓虹",
        mode: "dark",
        cover_bg: "linear-gradient(180deg, #09090b 0%, #1d1135 100%)",
        card_bg: "linear-gradient(135deg, #09090b 0%, #231942 100%)",
        accent_color: "#22d3ee",
        cover_inner_background: "#111827",
        title_gradient: "linear-gradient(180deg, #67e8f9 0%, #c4b5fd 100%)",
        subtitle_color: "#e0f2fe",
        card_surface: "rgba(17, 24, 39, 0.96)",
        text_primary: "#f5f3ff",
        text_secondary: "#dbeafe",
        text_tertiary: "#c4b5fd",
        text_muted: "#94a3b8",
        surface_muted: "#1f2a44",
        border_color: "#334155",
        code_surface: "#1f2a44",
        pre_surface: "#020617",
        pre_text: "#cffafe",
        card_shadow: "0 16px 42px rgba(34, 211, 238, 0.15)",
        page_number_color: "rgba(186, 230, 253, 0.6)",
    },
    cocoa: {
        name: "可可杂志",
        mode: "light",
        cover_bg: "linear-gradient(180deg, #6f4e37 0%, #d8c3a5 100%)",
        card_bg: "linear-gradient(135deg, #8d6e63 0%, #ede0d4 100%)",
        accent_color: "#6b4226",
        cover_inner_background: "#faf3e8",
        title_gradient: "linear-gradient(180deg, #4e342e 0%, #8d6e63 100%)",
        subtitle_color: "#5d4037",
        card_surface: "rgba(250, 243, 232, 0.96)",
        text_primary: "#4e342e",
        text_secondary: "#5d4037",
        text_tertiary: "#6d4c41",
        text_muted: "#8d6e63",
        surface_muted: "#efdfd1",
        border_color: "#d7b899",
        code_surface: "#efdfd1",
        pre_surface: "#3e2723",
        pre_text: "#fbe9e7",
        card_shadow: "0 12px 34px rgba(78, 52, 46, 0.18)",
        page_number_color: "rgba(78, 52, 46, 0.35)",
    },
    terminal: {
        name: "终端绿",
        mode: "dark",
        cover_bg: "linear-gradient(180deg, #04130b 0%, #0b2a16 100%)",
        card_bg: "linear-gradient(135deg, #03150d 0%, #0f2f1b 100%)",
        accent_color: "#4ade80",
        cover_inner_background: "#07150e",
        title_gradient: "linear-gradient(180deg, #86efac 0%, #4ade80 100%)",
        subtitle_color: "#d1fae5",
        card_surface: "rgba(7, 21, 14, 0.96)",
        text_primary: "#d1fae5",
        text_secondary: "#bbf7d0",
        text_tertiary: "#86efac",
        text_muted: "#94a3b8",
        surface_muted: "#10311d",
        border_color: "#166534",
        code_surface: "#10311d",
        pre_surface: "#020617",
        pre_text: "#bbf7d0",
        card_shadow: "0 16px 42px rgba(74, 222, 128, 0.15)",
        font_family: "'SF Mono', 'JetBrains Mono', 'Cascadia Code', 'Source Han Sans CN', monospace",
        radius: "16px",
        page_number_color: "rgba(187, 247, 208, 0.58)",
    },
};

function readAssetFile(fileName) {
    if (!TEMPLATE_CACHE.has(fileName)) {
        TEMPLATE_CACHE.set(fileName, fs.readFileSync(path.join(ASSETS_DIR, fileName), 'utf-8'));
    }
    return TEMPLATE_CACHE.get(fileName);
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function getCoverTitleSize(title) {
    const titleLen = String(title).length;
    if (titleLen <= 6) return 150;
    if (titleLen <= 10) return 130;
    if (titleLen <= 18) return 100;
    if (titleLen <= 30) return 80;
    return 60;
}

function buildThemeCss(styleKey, metadata = {}) {
    const style = STYLES[styleKey] || STYLES.purple;
    const isDark = style.mode === 'dark';
    const title = metadata.title || '';
    const defaultLightTitleGradient = 'linear-gradient(180deg, #2E67B1 0%, #4C4C4C 100%)';
    const defaultDarkTitleGradient = 'linear-gradient(180deg, #ffffff 0%, #cccccc 100%)';

    const vars = {
        '--font-family': style.font_family || "'Noto Sans SC', 'Source Han Sans CN', 'PingFang SC', 'Microsoft YaHei', -apple-system, sans-serif",
        '--cover-background': style.cover_bg,
        '--cover-inner-background': style.cover_inner_background || (isDark ? '#1a1a2e' : '#F3F3F3'),
        '--cover-title-gradient': style.title_gradient || (isDark ? defaultDarkTitleGradient : defaultLightTitleGradient),
        '--cover-subtitle-color': style.subtitle_color || (isDark ? '#ffffff' : '#000000'),
        '--cover-title-size': `${getCoverTitleSize(title)}px`,
        '--card-background': style.card_bg,
        '--card-surface': style.card_surface || (isDark ? 'rgba(30, 30, 46, 0.95)' : 'rgba(255, 255, 255, 0.95)'),
        '--card-shadow': style.card_shadow || '0 8px 32px rgba(0, 0, 0, 0.1)',
        '--border-radius': style.radius || '25px',
        '--inner-radius': style.inner_radius || '20px',
        '--accent-color': style.accent_color,
        '--text-primary': style.text_primary || (isDark ? '#ffffff' : '#1e293b'),
        '--text-secondary': style.text_secondary || (isDark ? '#e0e0e0' : '#334155'),
        '--text-tertiary': style.text_tertiary || (isDark ? '#e0e0e0' : '#475569'),
        '--text-muted': style.text_muted || (isDark ? '#a0a0a0' : '#64748b'),
        '--text-on-accent': style.text_on_accent || '#ffffff',
        '--surface-muted': style.surface_muted || (isDark ? '#252540' : '#f1f5f9'),
        '--border-color': style.border_color || (isDark ? '#333355' : '#e2e8f0'),
        '--code-surface': style.code_surface || (isDark ? '#252540' : '#f1f5f9'),
        '--pre-surface': style.pre_surface || (isDark ? '#0f0f23' : '#1e293b'),
        '--pre-text': style.pre_text || (isDark ? '#e0e0e0' : '#e2e8f0'),
        '--page-number-color': style.page_number_color || (isDark ? 'rgba(255, 255, 255, 0.72)' : 'rgba(255, 255, 255, 0.8)'),
    };

    const cssVars = Object.entries(vars)
        .map(([key, value]) => `    ${key}: ${value};`)
        .join('\n');

    return `${readAssetFile('styles.css')}\n\n:root {\n${cssVars}\n}`;
}

/**
 * 解析 Markdown 文件，提取 YAML 头部和正文内容
 */
function parseMarkdownFile(filePath) {
    const content = fs.readFileSync(filePath, 'utf-8');
    
    const yamlPattern = /^---\s*\n([\s\S]*?)\n---\s*\n/;
    const yamlMatch = content.match(yamlPattern);
    
    let metadata = {};
    let body = content;
    
    if (yamlMatch) {
        try {
            metadata = yaml.load(yamlMatch[1]) || {};
        } catch (e) {
            metadata = {};
        }
        body = content.slice(yamlMatch[0].length);
    }
    
    return { metadata, body: body.trim() };
}

/**
 * 按照 --- 分隔符拆分正文为多张卡片内容
 */
function splitContentBySeparator(body) {
    const parts = body.split(/\n---+\n/);
    return parts.filter(part => part.trim()).map(part => part.trim());
}

/**
 * 预估内容高度
 */
function estimateContentHeight(content) {
    const lines = content.split('\n');
    let totalHeight = 0;
    
    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) {
            totalHeight += 20;
            continue;
        }
        
        if (trimmed.startsWith('# ')) {
            totalHeight += 130;
        } else if (trimmed.startsWith('## ')) {
            totalHeight += 110;
        } else if (trimmed.startsWith('### ')) {
            totalHeight += 90;
        } else if (trimmed.startsWith('```')) {
            totalHeight += 80;
        } else if (trimmed.match(/^[-*+]\s/)) {
            totalHeight += 85;
        } else if (trimmed.startsWith('>')) {
            totalHeight += 100;
        } else if (trimmed.startsWith('![')) {
            totalHeight += 300;
        } else {
            const charCount = trimmed.length;
            const linesNeeded = Math.max(1, charCount / 28);
            totalHeight += Math.floor(linesNeeded * 42 * 1.7) + 35;
        }
    }
    
    return totalHeight;
}

/**
 * 智能拆分内容
 */
function smartSplitContent(content, maxHeight = SAFE_HEIGHT) {
    const blocks = [];
    let currentBlock = [];
    
    const lines = content.split('\n');
    
    for (const line of lines) {
        if (line.trim().startsWith('#') && currentBlock.length > 0) {
            blocks.push(currentBlock.join('\n'));
            currentBlock = [line];
        } else if (line.trim() === '---') {
            if (currentBlock.length > 0) {
                blocks.push(currentBlock.join('\n'));
                currentBlock = [];
            }
        } else {
            currentBlock.push(line);
        }
    }
    
    if (currentBlock.length > 0) {
        blocks.push(currentBlock.join('\n'));
    }
    
    if (blocks.length <= 1) {
        const paragraphs = content.split('\n\n').filter(b => b.trim());
        blocks.length = 0;
        blocks.push(...paragraphs);
    }
    
    const cards = [];
    let currentCard = [];
    let currentHeight = 0;
    
    for (const block of blocks) {
        const blockHeight = estimateContentHeight(block);
        
        if (blockHeight > maxHeight) {
            if (currentCard.length > 0) {
                cards.push(currentCard.join('\n\n'));
                currentCard = [];
                currentHeight = 0;
            }
            
            const blockLines = block.split('\n');
            let subBlock = [];
            let subHeight = 0;
            
            for (const line of blockLines) {
                const lineHeight = estimateContentHeight(line);
                
                if (subHeight + lineHeight > maxHeight && subBlock.length > 0) {
                    cards.push(subBlock.join('\n'));
                    subBlock = [line];
                    subHeight = lineHeight;
                } else {
                    subBlock.push(line);
                    subHeight += lineHeight;
                }
            }
            
            if (subBlock.length > 0) {
                cards.push(subBlock.join('\n'));
            }
        } else if (currentHeight + blockHeight > maxHeight && currentCard.length > 0) {
            cards.push(currentCard.join('\n\n'));
            currentCard = [block];
            currentHeight = blockHeight;
        } else {
            currentCard.push(block);
            currentHeight += blockHeight;
        }
    }
    
    if (currentCard.length > 0) {
        cards.push(currentCard.join('\n\n'));
    }
    
    return cards.length > 0 ? cards : [content];
}

/**
 * 将 Markdown 转换为 HTML
 */
function convertMarkdownToHtml(mdContent, style = STYLES.purple) {
    const tagsPattern = /((?:#[\w\u4e00-\u9fa5]+\s*)+)$/m;
    const tagsMatch = mdContent.match(tagsPattern);
    let tagsHtml = "";
    
    if (tagsMatch) {
        const tagsStr = tagsMatch[1];
        mdContent = mdContent.slice(0, tagsMatch.index).trim();
        const tags = tagsStr.match(/#([\w\u4e00-\u9fa5]+)/g);
        if (tags) {
            const accent = style.accent_color;
            tagsHtml = '<div class="tags-container">';
            for (const tag of tags) {
                tagsHtml += `<span class="tag" style="background: ${accent};">${tag}</span>`;
            }
            tagsHtml += '</div>';
        }
    }
    
    const html = marked.parse(mdContent, { breaks: true, gfm: true });
    return html + tagsHtml;
}

/**
 * 生成封面 HTML
 */
function generateCoverHtml(metadata, styleKey = 'purple') {
    const emoji = metadata.emoji || '📝';
    const title = metadata.title || '标题';
    const subtitle = metadata.subtitle || '';
    return readAssetFile('cover.html')
        .replace('{{SHARED_STYLES}}', buildThemeCss(styleKey, metadata))
        .replace('{{EMOJI}}', escapeHtml(emoji))
        .replace('{{TITLE}}', escapeHtml(title))
        .replace('{{SUBTITLE}}', escapeHtml(subtitle));
}

/**
 * 生成正文卡片 HTML
 */
function generateCardHtml(content, pageNumber = 1, totalPages = 1, styleKey = 'purple') {
    const style = STYLES[styleKey] || STYLES.purple;
    const htmlContent = convertMarkdownToHtml(content, style);
    const pageText = totalPages > 1 ? `${pageNumber}/${totalPages}` : '';
    return readAssetFile('card.html')
        .replace('{{SHARED_STYLES}}', buildThemeCss(styleKey))
        .replace('{{CONTENT}}', htmlContent)
        .replace('{{PAGE_NUMBER}}', escapeHtml(pageText));
}

/**
 * 测量内容高度
 */
async function measureContentHeight(page, htmlContent) {
    await page.setContent(htmlContent, { waitUntil: 'networkidle' });
    await page.waitForTimeout(300);
    
    return await page.evaluate(() => {
        const inner = document.querySelector('.card-inner');
        if (inner) return inner.scrollHeight;
        const container = document.querySelector('.card-container');
        return container ? container.scrollHeight : document.body.scrollHeight;
    });
}

/**
 * 处理和渲染卡片
 */
async function processAndRenderCards(cardContents, styleKey) {
    const browser = await chromium.launch();
    const page = await browser.newPage({ viewport: { width: CARD_WIDTH, height: CARD_HEIGHT } });
    
    const allCards = [];
    
    try {
        for (const content of cardContents) {
            const estimatedHeight = estimateContentHeight(content);
            
            let splitContents;
            if (estimatedHeight > SAFE_HEIGHT) {
                splitContents = smartSplitContent(content, SAFE_HEIGHT);
            } else {
                splitContents = [content];
            }
            
            for (const splitContent of splitContents) {
                const tempHtml = generateCardHtml(splitContent, 1, 1, styleKey);
                const actualHeight = await measureContentHeight(page, tempHtml);
                
                if (actualHeight > CARD_HEIGHT - 100) {
                    const lines = splitContent.split('\n');
                    const subContents = [];
                    let subLines = [];
                    
                    for (const line of lines) {
                        const testLines = [...subLines, line];
                        const testHtml = generateCardHtml(testLines.join('\n'), 1, 1, styleKey);
                        const testHeight = await measureContentHeight(page, testHtml);
                        
                        if (testHeight > CARD_HEIGHT - 100 && subLines.length > 0) {
                            subContents.push(subLines.join('\n'));
                            subLines = [line];
                        } else {
                            subLines = testLines;
                        }
                    }
                    
                    if (subLines.length > 0) {
                        subContents.push(subLines.join('\n'));
                    }
                    
                    allCards.push(...subContents);
                } else {
                    allCards.push(splitContent);
                }
            }
        }
    } finally {
        await browser.close();
    }
    
    return allCards;
}

/**
 * 渲染 HTML 到图片
 */
async function renderHtmlToImage(page, htmlContent, outputPath, htmlOutputPath = null) {
    if (htmlOutputPath) {
        fs.writeFileSync(htmlOutputPath, htmlContent, 'utf-8');
    }

    await page.setContent(htmlContent, { waitUntil: 'networkidle' });
    await page.waitForTimeout(300);
    
    await page.screenshot({
        path: outputPath,
        clip: { x: 0, y: 0, width: CARD_WIDTH, height: CARD_HEIGHT },
        type: 'png'
    });
    
    console.log(`  ✅ 已生成: ${outputPath}`);
}

/**
 * 主渲染函数
 */
function estimateOnlyProcessCards(cardContents) {
    const processedCards = [];

    for (const content of cardContents) {
        if (estimateContentHeight(content) > SAFE_HEIGHT) {
            processedCards.push(...smartSplitContent(content, SAFE_HEIGHT));
        } else {
            processedCards.push(content);
        }
    }

    return processedCards;
}

async function renderMarkdownToCards(mdFile, outputDir, styleKey = 'dark', saveHtml = false, htmlOnly = false) {
    console.log(`\n🎨 开始渲染: ${mdFile}`);
    console.log(`🎨 使用样式: ${STYLES[styleKey].name}`);
    
    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }
    
    const data = parseMarkdownFile(mdFile);
    const { metadata, body } = data;
    
    const cardContents = splitContentBySeparator(body);
    console.log(`  📄 检测到 ${cardContents.length} 个内容块`);
    
    console.log('  🔍 分析内容高度并智能分页...');
    const processedCards = htmlOnly
        ? estimateOnlyProcessCards(cardContents)
        : await processAndRenderCards(cardContents, styleKey);
    const totalCards = processedCards.length;
    console.log(`  📄 将生成 ${totalCards} 张卡片`);
    
    if (metadata.emoji || metadata.title) {
        console.log('  📷 生成封面...');
        const coverHtml = generateCoverHtml(metadata, styleKey);

        if (htmlOnly) {
            fs.writeFileSync(path.join(outputDir, 'cover.html'), coverHtml, 'utf-8');
        } else {
            const browser = await chromium.launch();
            const page = await browser.newPage({ viewport: { width: CARD_WIDTH, height: CARD_HEIGHT } });
        
            try {
                await renderHtmlToImage(
                    page,
                    coverHtml,
                    path.join(outputDir, 'cover.png'),
                    saveHtml ? path.join(outputDir, 'cover.html') : null
                );
            } finally {
                await browser.close();
            }
        }
    }
    
    if (htmlOnly) {
        for (let i = 0; i < processedCards.length; i++) {
            const pageNum = i + 1;
            const cardHtml = generateCardHtml(processedCards[i], pageNum, totalCards, styleKey);
            fs.writeFileSync(path.join(outputDir, `card_${pageNum}.html`), cardHtml, 'utf-8');
            console.log(`  ✅ 已生成: ${path.join(outputDir, `card_${pageNum}.html`)}`);
        }
        console.log(`\n✨ HTML 预览已生成，共 ${totalCards} 张卡片，保存到: ${outputDir}`);
        return totalCards;
    }

    const browser = await chromium.launch();
    const page = await browser.newPage({ viewport: { width: CARD_WIDTH, height: CARD_HEIGHT } });
    
    try {
        for (let i = 0; i < processedCards.length; i++) {
            const pageNum = i + 1;
            console.log(`  📷 生成卡片 ${pageNum}/${totalCards}...`);
            
            const cardHtml = generateCardHtml(processedCards[i], pageNum, totalCards, styleKey);
            const cardPath = path.join(outputDir, `card_${pageNum}.png`);
            
            await renderHtmlToImage(
                page,
                cardHtml,
                cardPath,
                saveHtml ? path.join(outputDir, `card_${pageNum}.html`) : null
            );
        }
    } finally {
        await browser.close();
    }
    
    console.log(`\n✨ 渲染完成！共生成 ${totalCards} 张卡片，保存到: ${outputDir}`);
    return totalCards;
}

/**
 * 列出所有样式
 */
function listStyles() {
    console.log('\n📋 可用样式列表：');
    console.log('-'.repeat(40));
    for (const [key, style] of Object.entries(STYLES)) {
        console.log(`  ${key.padEnd(12)} - ${style.name}`);
    }
    console.log('-'.repeat(40));
}

/**
 * 解析命令行参数
 */
function parseArgs() {
    const args = process.argv.slice(2);
    
    if (args.length === 0 || args.includes('--help')) {
        console.log(`
使用方法: node render_xhs_v2.js <markdown_file> [options]

选项:
  -o, --output-dir <dir>   输出目录（默认: ../redbook-auto-flow/workspace/）
  -s, --style <style>      样式主题（默认: dark）
  --save-html             同时导出 HTML 预览文件
  --html-only             仅导出 HTML 预览，不渲染 PNG
  --list-styles           列出所有可用样式
  --help                  显示帮助信息

可用样式:
  purple, xiaohongshu, mint, sunset, ocean, elegant, dark,
  botanical, retro, brutalist, sakura, midnight, cocoa, terminal

示例:
  node render_xhs_v2.js note.md
  node render_xhs_v2.js note.md -o ../redbook-auto-flow/workspace/20260306_120000_ai-tools/assets --style dark
        `);
        process.exit(0);
    }
    
    if (args.includes('--list-styles')) {
        listStyles();
        process.exit(0);
    }
    
    let markdownFile = null;
    let outputDir = DEFAULT_OUTPUT_DIR;
    let style = 'dark';
    let saveHtml = false;
    let htmlOnly = false;
    
    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--output-dir' || args[i] === '-o') {
            outputDir = args[i + 1];
            i++;
        } else if (args[i] === '--style' || args[i] === '-s') {
            if (STYLES[args[i + 1]]) {
                style = args[i + 1];
            } else {
                console.error(`❌ 无效样式: ${args[i + 1]}`);
                console.log('可用样式:', Object.keys(STYLES).join(', '));
                process.exit(1);
            }
            i++;
        } else if (args[i] === '--save-html') {
            saveHtml = true;
        } else if (args[i] === '--html-only') {
            htmlOnly = true;
        } else if (!args[i].startsWith('-')) {
            markdownFile = args[i];
        }
    }
    
    if (!markdownFile) {
        console.error('❌ 错误: 请指定 Markdown 文件');
        process.exit(1);
    }
    
    if (!fs.existsSync(markdownFile)) {
        console.error(`❌ 错误: 文件不存在 - ${markdownFile}`);
        process.exit(1);
    }
    
    return { markdownFile, outputDir, style, saveHtml, htmlOnly };
}

// 主函数
async function main() {
    const { markdownFile, outputDir, style, saveHtml, htmlOnly } = parseArgs();
    await renderMarkdownToCards(markdownFile, outputDir, style, saveHtml, htmlOnly);
}

main().catch(error => {
    console.error('❌ 渲染失败:', error.message);
    process.exit(1);
});
