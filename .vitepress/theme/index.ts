import { h } from 'vue'
import DefaultTheme from 'vitepress/theme'
import PdfDownload from './components/PdfDownload.vue'
import './custom.css'

export default {
  extends: DefaultTheme,
  Layout: () =>
    h(DefaultTheme.Layout, null, {
      'nav-bar-content-after': () => h(PdfDownload),
    }),
}
