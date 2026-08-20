import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const sourcePath = resolve(root, 'PNG图像格式解码算法与工程实现.md')
const outputDir = resolve(root, 'cn')
const source = await readFile(sourcePath, 'utf8')

const boundaries = [
  '# 第一篇　建立整体认识',
  '# 第二篇　PNG 文件格式与 Chunk',
  '# 第三篇　像素与 Scanline',
  '# 第四篇　完整 Decoder 数据流',
  '# 第五篇　zlib',
  '# 第六篇　DEFLATE 解码',
  '# 第七篇　Scanline Filter 与重建',
  '# 第八篇　Adam7',
  '# 第九篇　颜色、Alpha 与输出',
  '# 第十篇　编码器',
  '# 第十一篇　硬件架构',
  '# 第十二篇　错误、安全与验证',
  '# 第十三篇　贯通实例',
  '# 附录 A　速查公式',
]

const offsets = boundaries.map((heading) => {
  const offset = source.indexOf(heading)
  if (offset === -1) throw new Error(`找不到章节标题：${heading}`)
  return offset
})

if (offsets.some((offset, index) => index > 0 && offset <= offsets[index - 1])) {
  throw new Error('章节标题顺序异常')
}

const chapters = offsets.map((offset, index) =>
  source.slice(offset, offsets[index + 1] ?? source.length),
)
const files = [source.slice(0, offsets[0]), ...chapters]

if (files.join('') !== source) throw new Error('拆分校验失败：重组内容与原文不一致')

await mkdir(outputDir, { recursive: true })
await Promise.all(
  files.map((content, index) =>
    writeFile(resolve(outputDir, `${String(index).padStart(2, '0')}.md`), content, 'utf8'),
  ),
)

console.log(`已生成 ${files.length} 个章节文件，重组校验通过。`)