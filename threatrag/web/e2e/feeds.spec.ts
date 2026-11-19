import { expect, test } from '@playwright/test'
import { mockApi } from './mocks'

test('the knowledge base shows what the last feed refresh did', async ({ page }) => {
  await mockApi(page)
  await page.route('**/api/v1/ingest/feeds', route => route.fulfill({ json: {
    at: '2026-11-20T02:00:00+00:00', ok: false, regressed: false, steps: {
      mitre: { changed: true, latest_change: '2026-10-13', chunks: 3479 },
      kev: { error: 'ConnectError: CISA unreachable' },
      taxii: { skipped: 'TAXII_URL not set' },
      eval: { 'hit@6': 0.95, previous: 0.95, regressed: false },
    },
  } }))
  await page.goto('/knowledge-base')
  await expect(page.getByText('re-indexed the release last changed 2026-10-13: 3,479 passages')).toBeVisible()
  await expect(page.getByText('ConnectError: CISA unreachable')).toBeVisible()
  await expect(page.getByText('hit@6 0.95 (was 0.95)')).toBeVisible()
})

test('the knowledge base says how to start feeds that never ran', async ({ page }) => {
  await mockApi(page)
  await page.goto('/knowledge-base')
  await expect(page.getByText(/Feeds have not run/)).toBeVisible()
})
