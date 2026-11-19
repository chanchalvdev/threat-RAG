import { defineConfig } from 'vitest/config'

// Kept apart from vite.config.ts: Vitest bundles its own Vite, and mixing the two configs
// makes their plugin types disagree.
export default defineConfig({
  esbuild: { jsx: 'automatic' },
  test: { environment: 'jsdom', include: ['src/**/*.test.{ts,tsx}'] },
})
