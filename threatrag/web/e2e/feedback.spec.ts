import { expect, test } from '@playwright/test'
import { mockApi, sse, SOURCE } from './mocks'

const REPORT_ID = '6c1e0d3a-1111-4222-8333-444455556666'

test('an analyst down-votes an answer and files a note', async ({ page }) => {
  await mockApi(page)
  const votes: Record<string, unknown>[] = []
  await page.route('**/api/v1/feedback', async route => {
    votes.push(route.request().postDataJSON())
    await route.fulfill({ json: { id: 'f1', ...votes[votes.length - 1], created_at: 'now' } })
  })
  await page.route('**/api/v1/chat/stream', route => route.fulfill({
    headers: { 'Content-Type': 'text/event-stream', 'X-Session-ID': 'session-1', 'Access-Control-Expose-Headers': 'X-Session-ID' },
    body: sse([{ type: 'source', data: SOURCE }, { type: 'chunk', data: 'T1110.003 is Password Spraying.' }, { type: 'done', session_id: 'session-1' }]),
  }))

  await page.goto('/chat')
  await page.getByRole('textbox', { name: 'Message' }).fill('What is T1110.003?')
  await page.getByRole('button', { name: 'Send message' }).click()
  await page.getByRole('button', { name: 'Not helpful' }).click()
  await page.getByRole('textbox', { name: 'What was wrong?' }).fill('No mitigations listed')
  await page.getByRole('button', { name: 'File note' }).click()
  await expect(page.getByRole('button', { name: 'Note filed' })).toBeVisible()

  expect(votes[0]).toMatchObject({ target: 'answer', target_id: 'session-1:1', rating: -1, question: 'What is T1110.003?' })
  expect(votes[1]).toMatchObject({ rating: -1, note: 'No mitigations listed' })   // the note replaces the bare vote
})

test('a filed report is sent back with the Critic gaps prefilled', async ({ page }) => {
  await mockApi(page)
  const runs: Record<string, unknown>[] = []
  await page.route('**/api/v1/investigate/stream', async route => {
    runs.push(route.request().postDataJSON())
    await route.fulfill({
      headers: { 'Content-Type': 'text/event-stream' },
      body: sse([
        { type: 'node_start', node: 'researcher', iteration: 1 },
        { type: 'report_chunk', data: '# Threat Intelligence Report: CVE-2021-44228\n\n## Executive Summary\nCritical.' },
        { type: 'done', report_id: runs.length === 1 ? REPORT_ID : null, iterations: 2, sources: [], similar: [], tool_calls: [],
          critic_feedback: 'NEEDS_REVISION: no EPSS score | no affected versions' },
      ]),
    })
  })

  await page.goto('/investigate')
  await page.getByRole('textbox', { name: 'Indicator' }).fill('CVE-2021-44228')
  await page.getByRole('button', { name: 'Investigate' }).click()
  const gaps = page.getByRole('textbox', { name: 'Gaps to address' })
  await expect(gaps).toHaveValue('no EPSS score\nno affected versions')
  await gaps.fill('no EPSS score')
  await page.getByRole('button', { name: 'Send back' }).click()

  await expect.poll(() => runs.length).toBe(2)
  expect(runs[0]).toMatchObject({ ioc: 'CVE-2021-44228', ioc_type: 'cve' })
  expect(runs[1]).toMatchObject({ ioc: 'CVE-2021-44228', analyst_gaps: 'no EPSS score', parent_id: REPORT_ID })
})

test('analytics shows analyst feedback', async ({ page }) => {
  await mockApi(page)
  await page.goto('/analytics')
  await expect(page.getByText('4 up / 1 down')).toBeVisible()
  await expect(page.getByText('80% helpful')).toBeVisible()
  await expect(page.getByText('“missed APT29”')).toBeVisible()
})
