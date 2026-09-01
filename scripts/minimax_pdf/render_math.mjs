#!/usr/bin/env node
/**
 * render_math.mjs — Render LaTeX formulas to PNG via KaTeX + playwright.
 * usage: node render_math.mjs <manifest.json> <outDir> <page.html> <metaOut.json>
 * manifest: [{ id, expr }]
 */
import { readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)

function loadPlaywright() {
  try { return require('playwright') } catch (_) {}
  const { execSync } = require('child_process')
  const root = execSync('npm root -g', { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim()
  return require(path.join(root, 'playwright'))
}

const [manifestPath, outDir, pageHtml, metaOut] = process.argv.slice(2)
if (!manifestPath || !outDir || !pageHtml || !metaOut) {
  console.error('usage: node render_math.mjs <manifest.json> <outDir> <page.html> <metaOut.json>')
  process.exit(1)
}

const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'))
const { chromium } = loadPlaywright()
const browser = await chromium.launch()
const page = await browser.newPage({
  viewport: { width: 1400, height: 900 },
  deviceScaleFactor: 3,
})

await page.goto('file://' + path.resolve(pageHtml), { waitUntil: 'load' })
await page.waitForFunction(() => window.__ready === true, null, { timeout: 30000 })

const meta = {}
const failed = []
for (const item of manifest) {
  try {
    const size = await page.evaluate(({ expr }) => window.renderMath(expr), item)
    await page.waitForTimeout(60)
    const el = page.locator('#out')
    await el.screenshot({ path: path.join(outDir, `${item.id}.png`), animations: 'disabled' })
    meta[item.id] = size
    console.log(`${item.id}: ${size.w}x${size.h}css -> ${item.id}.png`)
  } catch (e) {
    failed.push(item.id)
    console.error(`${item.id}: FAILED ${e.message}`)
  }
}

writeFileSync(metaOut, JSON.stringify(meta, null, 1))
await browser.close()
console.log(`done: ${Object.keys(meta).length} rendered, ${failed.length} failed`)
if (failed.length) process.exit(4)
