# AGENTS.md

## 项目概述

本仓库是《PNG 图像格式、解码算法与工程实现》的中文手册及其 VitePress 站点。主要交付物包括：

- 可浏览的 VitePress 文档站点；
- 按章节拆分的 `cn` 文档；
- 带完整目录和已渲染 Mermaid 图的合订 PDF。

## 目录与职责

- `cn/00.md` 至 `cn/15.md` 及 `cn/02-1.md`、`cn/06-1.md`：独立维护的章节文件，文件编号与一级标题编号一致；废弃文档存放在 `deprecated/`。
- `cn/index.md`：手工维护的全书目录页，不由拆分脚本生成。
- `index.md`：VitePress 首页。
- `.vitepress/config.mts`：站点导航、侧栏、搜索、Markdown 和 Mermaid 配置。
- `scripts/minimax_pdf/`：自包含的 PDF 生成管线——章节 Markdown 转 content.json、pdflatex 矢量公式、mermaid 渲染、ReportLab 正文与完整书签、浅色封面与合并校验；入口为 `scripts/minimax_pdf/build.py`，设计令牌集中在 `scripts/minimax_pdf/config.json`。
- `PNG图像格式解码算法与工程实现.pdf`：提交到仓库的合订 PDF，由构建脚本覆盖生成。
- `.vitepress/dist/`、`.vitepress/cache/`：生成物，不作为源文件维护。

## 内容修改规则

1. 正文内容直接修改对应的在役 `cn` 章节文件；不要修改 `deprecated/` 中的废弃文档。
2. `cn/index.md`、`index.md` 和站点配置是手工维护文件，可直接编辑。
3. 若增加、删除或重排章节，必须同步更新：
   - `.vitepress/config.mts` 中的 `chapters`；
   - `cn/index.md`；
   - `scripts/minimax_pdf/config.json` 中的 `chapters`；
4. 保留中文标点、全角篇章空格和现有术语写法。不要无关地重排表格或改写技术术语。
5. Mermaid 使用 fenced code block，并保持 `mermaid` 语言标识；不要把图替换成未经验证的静态占位文本。

## 环境与常用命令

需要 Node.js、npm、Python 3.10 或更高版本、`requirements.txt` 中的 Python 依赖、全局 `playwright` 与 Chromium（封面、公式回退和 Mermaid 渲染用），以及项目 `node_modules` 中的 `mermaid` 与 `katex`；矢量公式需要 pdflatex（推荐免 sudo 的 TinyTeX，并执行 `tlmgr install standalone xcolor lmodern cm-super`）。

```bash
npm install
npm run docs:dev
npm run docs:build
python -m pip install -r requirements.txt
python scripts/minimax_pdf/build.py
```

在 Windows PowerShell 执行策略阻止 `npm.ps1` 时，使用 `npm.cmd`：

```powershell
npm.cmd install
npm.cmd run docs:build
```

PDF 默认输出并覆盖根目录的 `PNG图像格式解码算法与工程实现.pdf`。可用 `--output` 指定其他路径，`--accent` 临时覆盖主色，`--math-engine latex|katex|matplotlib` 选择公式引擎（默认自动：优先 pdflatex，编译失败回退 KaTeX 位图，再回退 matplotlib），`--workdir` 配合 `--keep-work` 保留中间产物调试。

## 验证要求

根据改动范围运行最小且充分的检查：

- 修改章节、首页、导航或 VitePress 配置：运行 `npm run docs:build`。
- 修改 Mermaid、PDF 脚本或 `config.json` 设计令牌：运行 `python scripts/minimax_pdf/build.py`。
- PDF 验证必须包含管线输出的书签校验（数量与跳转目标）和版面溢出检查；当前手册预期有 5 个 Mermaid 图，全部一至三级标题必须具有可跳转的书签目标，公式必须是矢量可复制文本而非图片。
- 构建产生的 Mermaid chunk 大小警告可以记录，但只要构建成功，不应为消除该警告而进行无关重构。

## 实现约定

- JavaScript/TypeScript 延续现有无分号、单引号风格。
- Python 使用标准库优先、类型标注和清晰的错误信息；保持脚本可从仓库根目录之外调用。
- 路径处理使用 `pathlib` 或 Node `path` API，避免手工拼接平台相关路径。
- 不提交 `node_modules/`、VitePress 构建缓存或其他临时产物；根目录合订 PDF 除外。
- 不修改 `LICENSE`，除非任务明确要求。
- 不清理或覆盖与当前任务无关的用户改动。

## 完成标准

改动应保持以下流程可用：19 个独立章节可由 VitePress 构建，站点具有全局目录入口与导航栏 PDF 下载，PDF 正文不插入额外的详细目录页、具有完整可跳转书签，公式为矢量可复制的 LaTeX 排版，且 Mermaid 在 PDF 中显示为渲染后的图形。
