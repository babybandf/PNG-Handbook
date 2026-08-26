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

运行 Python 脚本生成合订 PDF：

```bash
python scripts/build_pdf.py
```

PDF 默认输出并覆盖根目录的 `PNG图像格式解码算法与工程实现.pdf`。正文不插入额外的详细目录页；脚本会生成覆盖一至三级标题的完整 PDF 书签，并验证每个书签都能跳转到正确页面。Mermaid 会通过 VitePress 和本机 Edge/Chrome 渲染为图形后写入 PDF。

可用 `--output` 指定输出路径：

```bash
python scripts/build_pdf.py --output png-handbook.pdf
```
