# minimax_pdf — PNG 手册 PDF 生成模板

基于 minimax-pdf skill 思路的自包含 PDF 生成管线：Markdown 章节 → 浅色技术文档
风格 PDF，含真矢量可复制公式（pdflatex）、渲染后的 mermaid 图、完整三级书签。

## 使用

```bash
python3 scripts/minimax_pdf/build.py                        # 按默认配置生成到仓库根目录
python3 scripts/minimax_pdf/build.py --output out.pdf       # 指定输出
python3 scripts/minimax_pdf/build.py --accent "#33A6B8"     # 临时改主色
python3 scripts/minimax_pdf/build.py --math-engine katex    # 强制公式引擎
python3 scripts/minimax_pdf/build.py --workdir /tmp/pdfbuild --keep-work  # 保留中间产物
```

配色、标题、章节顺序、字体、字号、页边距等全部在 `config.json` 中调整。

## 依赖

- Python 3.10+：`reportlab` `pypdf` `matplotlib` `fonttools`（QA 可选 `pymupdf`）
- Node.js 18+：全局 `playwright` + Chromium（`npm install -g playwright && npx playwright install chromium`）
- 项目 `node_modules`：`mermaid`（图表）、`katex`（公式回退）
- 公式引擎 pdflatex：推荐免 sudo 的 [TinyTeX](https://yihui.org/tinytex/)，
  安装后补充宏包 `tlmgr install standalone xcolor lmodern cm-super`
  （脚本会在 `~/Library/TinyTeX` 与 `~/.TinyTeX` 自动查找 pdflatex）

## 公式管线（矢量、可复制）

1. `md2content.py` 提取 `$$...$$` 块并分配 `math_N` ID；
2. `build.py` 为每个公式生成 standalone TeX 源并用 pdflatex 编译为按内容裁剪的矢量 PDF；
3. `render_body_cjk.py` 在正文中放置同尺寸占位（`MathPlaceholder`）；
4. `stamp_math.py` 用 pypdf 把矢量公式按坐标叠加进正文——文字保持可选中、可复制、可检索。

任一公式编译失败时自动回退：pdflatex → KaTeX（高清位图）→ matplotlib mathtext。

## 文件说明

| 文件 | 职责 |
|---|---|
| `build.py` | 总编排：依赖检查、mermaid/公式/封面/正文/合并 |
| `config.json` | 全部设计令牌：配色、字体、字号、章节、元数据 |
| `md2content.py` | Markdown → content.json（表格列宽、CJK 行内标记、公式/图表提取） |
| `render_body_cjk.py` | ReportLab 正文渲染 + 大纲书签 + 页眉页脚 |
| `render_cover.py` / `render_cover.mjs` | 浅色封面 HTML 生成 + Playwright 打印 PDF |
| `render_mermaid.mjs` | mermaid 源 → 2x PNG |
| `render_math.mjs` | KaTeX 公式 → 3x PNG（回退引擎用） |
| `stamp_math.py` | 矢量公式叠加 |
| `merge_outline.py` | 封面+正文合并、元数据、书签与版面 QA |
