import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'
import footnote from 'markdown-it-footnote'
import ins from 'markdown-it-ins'
import mark from 'markdown-it-mark'
import sub from 'markdown-it-sub'
import sup from 'markdown-it-sup'

const chapters = [
  { text: '00. 前言', link: '/cn/00' },
  { text: '01. 建立整体认识', link: '/cn/01' },
  { text: '02. PNG 文件格式与 Chunk', link: '/cn/02' },
  { text: '02-1 Grayscale 转 RGB', link: '/cn/02-1' },
  { text: '03. 像素与 Scanline', link: '/cn/03' },
  { text: '04. 完整 Decoder 数据流', link: '/cn/04' },
  { text: '05. zlib', link: '/cn/05' },
  { text: '06. DEFLATE Decoder - RFC 1951', link: '/cn/06' },
  { text: '06-1 PNG Huffman 编码详解', link: '/cn/06-1' },
  { text: '07. Scanline Filter 与重建', link: '/cn/07' },
  { text: '08. Adam7 原理与解码流程', link: '/cn/08' },
  { text: '09. 颜色、Alpha 与输出', link: '/cn/09' },
  { text: '10. 编码器', link: '/cn/10' },
  { text: '11. 硬件架构', link: '/cn/11' },
  { text: '12. 错误、安全与验证', link: '/cn/12' },
  { text: '13. 贯通实例', link: '/cn/13' },
  { text: '14. PNG 图像测试集与验证资源汇总', link: '/cn/14' },
  { text: '14-1 PngSuite 测试集分类与图片说明', link: '/cn/14-1' },
  { text: '15. 附录与结语', link: '/cn/15' },
]

const base = process.env.GITHUB_ACTIONS ? '/PNG-Handbook/' : '/'

export default withMermaid(
  defineConfig({
    base,
    lang: 'zh-CN',
    title: 'PNG 图像格式、解码算法与工程实现',
    description: '从 PNG 文件格式到软硬件解码器实现的系统手册',
    vite: {
      optimizeDeps: {
        include: ['fastdom', 'fastdom/extensions/fastdom-promised.js'],
      },
    },
    cleanUrls: true,
    lastUpdated: true,
    themeConfig: {
      nav: [
        { text: '首页', link: '/' },
        { text: '开始阅读', link: '/cn/00' },
        {
          text: '全书目录',
          items: chapters,
        },
      ],
      sidebar: {
        '/cn/': chapters,
      },
      outline: {
        level: [2, 3],
        label: '本页目录',
      },
      docFooter: {
        prev: '上一章',
        next: '下一章',
      },
      lastUpdated: {
        text: '最后更新',
      },
      search: {
        provider: 'local',
      },
    },
    markdown: {
      math: true,
      config(md) {
        md.use(footnote)
        md.use(ins)
        md.use(mark)
        md.use(sub)
        md.use(sup)
      },
      toc: {
        level: [1, 2, 3],
      },
    },
    srcExclude: [
      '**/README.md',
      'scripts/**',
    ],
  }),
)