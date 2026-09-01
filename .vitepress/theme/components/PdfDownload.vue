<script setup lang="ts">
import { ref } from 'vue'

const PDF_URL =
  'https://raw.githubusercontent.com/babybandf/PNG-Handbook/main/'
  + 'PNG%E5%9B%BE%E5%83%8F%E6%A0%BC%E5%BC%8F%E8%A7%A3%E7%A0%81%E7%AE%97%E6%B3%95'
  + '%E4%B8%8E%E5%B7%A5%E7%A8%8B%E5%AE%9E%E7%8E%B0.pdf'
const FILENAME = 'PNG图像格式解码算法与工程实现.pdf'

const busy = ref(false)

async function download() {
  if (busy.value) return
  busy.value = true
  try {
    const res = await fetch(PDF_URL, { cache: 'no-store' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const blob = new Blob([await res.blob()], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = FILENAME
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 10_000)
  } catch {
    window.open(PDF_URL, '_blank', 'noopener')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="pdf-download">
    <span class="divider" aria-hidden="true" />
    <button
      class="pdf-btn"
      type="button"
      :disabled="busy"
      :title="FILENAME"
      @click="download"
    >
      {{ busy ? '下载中…' : 'PDF 下载' }}
    </button>
  </div>
</template>

<style scoped>
.pdf-download {
  display: flex;
  align-items: center;
}

.divider {
  width: 1px;
  height: 24px;
  margin: 0 8px 0 16px;
  background-color: var(--vp-c-divider);
}

.pdf-btn {
  display: flex;
  align-items: center;
  padding: 0 12px;
  line-height: var(--vp-nav-height);
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  color: var(--vp-c-text-1);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: color 0.25s;
  white-space: nowrap;
}

.pdf-btn:hover:not(:disabled) {
  color: var(--vp-c-brand-1);
}

.pdf-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
