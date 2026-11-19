import { defineConfig, devices } from '@playwright/test'

// Full-stack browser tests: nothing is mocked. The browser talks to the deployed web image
// (nginx), which proxies to the real API, Qdrant, Postgres and Redis. Start the stack first:
//   docker compose -f ../infra/docker-compose.yml up -d --wait backend frontend
// STACK_URL points elsewhere (e.g. http://localhost:5173 for `npm run dev` + a local API).
// STACK_LLM=1 also runs the test that needs a model key and an ingested corpus.
export default defineConfig({
  testDir: './e2e-stack',
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  use: { baseURL: process.env.STACK_URL ?? 'http://localhost:3000', trace: 'retain-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] }, metadata: { llm: Boolean(process.env.STACK_LLM) } }],
})
