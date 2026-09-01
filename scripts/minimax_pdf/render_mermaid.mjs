#!/usr/bin/env node
/**
 * render_mermaid.mjs — Render mermaid manifest [{id, code}] to PNG via playwright.
 * usage: node render_mermaid.mjs <manifest.json> <outDir> <page.html>
 */
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)

function loadPlaywright() {
  try { return require('playwright') } catch (_) {}
  const { execSync } = require('child_process')
  const root = execSync('npm root -g', { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim()
  return require(path.join(root, 'playwright'))
}

const [manifestPath, outDir, pageHtml] = process.argv.slice(2)
if (!manifestPath || !outDir || !pageHtml) {
  console.error('usage: node render_mermaid.mjs <manifest.json> <outDir> <page.html>')
  process.exit(1)
}

const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'))
const { chromium } = loadPlaywright()
const browser = await chromium.launch()
const page = await browser.newPage({
  viewport: { width: 1800, height: 2400 },
  deviceScaleFactor: 2,
})

await page.goto('file://' + path.resolve(pageHtml), { waitUntil: 'load' })
await page.waitForFunction(() => window.__ready === true, null, { timeout: 30000 })

for (const item of manifest) {
  const size = await page.evaluate((code) => window.renderDiagram(code), item.code)
  await page.waitForTimeout(120)
  const el = page.locator('#out svg')
  await el.screenshot({ path: path.join(outDir, `${item.id}.png`), animations: 'disabled' })
  console.log(`${item.id}: ${size.w}x${size.h} -> ${item.id}.png`)
}

await browser.close()
console.log(`done: ${manifest.length} diagrams`)
