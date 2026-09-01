#!/usr/bin/env node
/**
 * render_cover.mjs — Render cover.html to a single-page PDF via playwright.
 * usage: node render_cover.mjs <cover.html> <cover.pdf>
 */
import path from 'node:path'
import { statSync } from 'node:fs'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)

function loadPlaywright() {
  try { return require('playwright') } catch (_) {}
  const { execSync } = require('child_process')
  const root = execSync('npm root -g', { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim()
  return require(path.join(root, 'playwright'))
}

const [inputFile, outFile] = process.argv.slice(2)
if (!inputFile || !outFile) {
  console.error('usage: node render_cover.mjs <cover.html> <cover.pdf>')
  process.exit(1)
}

const { chromium } = loadPlaywright()
const browser = await chromium.launch()
const page = await browser.newPage()

await page.goto('file://' + path.resolve(inputFile), { waitUntil: 'networkidle' })
await page.waitForTimeout(600)

await page.pdf({
  path: outFile,
  width: '794px',
  height: '1123px',
  printBackground: true,
  pageRanges: '1',
})

await browser.close()

const size = statSync(outFile).size
if (size < 5000) {
  console.error(JSON.stringify({ status: 'error', error: 'cover.pdf suspiciously small' }))
  process.exit(3)
}
console.log(JSON.stringify({ status: 'ok', out: outFile, size_kb: Math.round(size / 1024) }))
