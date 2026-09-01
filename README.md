# PNG Handbook

《PNG 图像格式、解码算法与工程实现》的 VitePress 文档站点。

## 使用

安装依赖：

```bash
npm install
```

启动本地文档站点：

```bash
npm run docs:dev
```

构建静态站点：

```bash
npm run docs:build
```

全书内容按独立章节维护在 `cn/00.md` 至 `cn/15.md`，以及 `cn/02-1.md`、`cn/06-1.md`；废弃文档存放在 `deprecated/`。

## 生成 PDF

安装 PDF 处理依赖：

```bash
python -m pip install -r requirements.txt
```

矢量公式需要 pdflatex，推荐免 sudo 的 [TinyTeX](https://yihui.org/tinytex/)，安装后执行 `tlmgr install standalone xcolor lmodern cm-super`。

运行构建脚本生成合订 PDF：

```bash
python scripts/minimax_pdf/build.py
```

PDF 默认输出并覆盖根目录的 `PNG图像格式解码算法与工程实现.pdf`。正文不插入额外的详细目录页；脚本会生成覆盖一至四级标题的完整 PDF 书签并验证跳转目标与版面，公式通过 pdflatex 排版为矢量可复制文本，Mermaid 通过 Playwright 渲染为图形后写入 PDF。

可用 `--output` 指定输出路径，`--accent` 覆盖主色，`--math-engine latex|katex|matplotlib` 选择公式引擎：

```bash
python scripts/minimax_pdf/build.py --output png-handbook.pdf --accent "#00BFFF"
```

配色、字体、章节顺序等设计令牌集中在 `scripts/minimax_pdf/config.json`，更多说明见 `scripts/minimax_pdf/README.md`。
