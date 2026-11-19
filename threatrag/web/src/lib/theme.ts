import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'
const KEY = 'threatrag-theme'

const current = (): Theme => (document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light')

/** Theme set before paint by index.html; this keeps React in sync and persists the viewer's choice. */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(current)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    window.dispatchEvent(new Event('themechange'))
  }, [theme])

  const toggle = () => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    try { localStorage.setItem(KEY, next) } catch { /* storage blocked: theme still applies for this visit */ }
    setTheme(next)
  }
  return { theme, toggle }
}

/** Resolved token colours for SVG charts, re-read whenever the theme flips. */
export function useTokens() {
  const read = () => {
    const css = getComputedStyle(document.documentElement)
    const v = (n: string) => `rgb(${css.getPropertyValue('--' + n).trim().split(/\s+/).join(',')})`
    return {
      ink: v('ink'), ink3: v('ink3'), rule: v('rule'), card: v('card'),
      verm: v('verm'), cobalt: v('cobalt'), ochre: v('ochre'), green: v('green'),
    }
  }
  const [tokens, setTokens] = useState(read)
  useEffect(() => {
    const update = () => setTokens(read())
    window.addEventListener('themechange', update)
    const mq = matchMedia('(prefers-color-scheme: dark)')
    mq.addEventListener('change', update)
    return () => { window.removeEventListener('themechange', update); mq.removeEventListener('change', update) }
  }, [])
  return tokens
}
