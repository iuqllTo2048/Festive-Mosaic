import { ref } from 'vue'

type Theme = 'dark' | 'light'
const preference = window.matchMedia('(prefers-color-scheme: dark)')
const storageKey = 'verifiatlas-theme'
const theme = ref<Theme>(document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light')
let followsSystem = true
try {
  const saved = localStorage.getItem(storageKey)
  followsSystem = saved !== 'dark' && saved !== 'light'
} catch { /* Theme switching works even when browser storage is disabled. */ }

function applyTheme(value: Theme) {
  theme.value = value
  document.documentElement.dataset.theme = value
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', value === 'dark' ? '#0d131b' : '#f4f6f8')
}

applyTheme(theme.value)
preference.addEventListener('change', (event) => {
  if (followsSystem) applyTheme(event.matches ? 'dark' : 'light')
})

export function useTheme() {
  function toggleTheme() {
    followsSystem = false
    applyTheme(theme.value === 'dark' ? 'light' : 'dark')
    try { localStorage.setItem(storageKey, theme.value) } catch { /* Optional persistence. */ }
  }
  return { theme, toggleTheme }
}
