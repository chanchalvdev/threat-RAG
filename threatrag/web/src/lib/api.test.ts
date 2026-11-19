// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { streamQuery, type SSEEvent } from './api'

function sseResponse(frames: string[], headers: Record<string, string> = {}): Response {
  const encoder = new TextEncoder()
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      frames.forEach(frame => controller.enqueue(encoder.encode(frame)))
      controller.close()
    },
  })
  return new Response(body, { status: 200, headers })
}

afterEach(() => vi.unstubAllGlobals())

describe('streamQuery', () => {
  it('always calls the agent endpoint and returns the session to continue with', async () => {
    const fetchMock = vi.fn().mockResolvedValue(sseResponse(['data: {"type":"done"}\n\n'], { 'X-Session-ID': 's-123' }))
    vi.stubGlobal('fetch', fetchMock)

    const session = await streamQuery('What is T1110.003?', () => undefined)

    expect(session).toBe('s-123')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/chat/stream')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ question: 'What is T1110.003?', session_id: null })
  })

  it('sends the existing session and reassembles events split across network chunks', async () => {
    const frames = ['data: {"type":"chu', 'nk","data":"Hello"}\n\ndata: not-json\n\n', 'data: {"type":"chunk","data":" world"}\n\n']
    const fetchMock = vi.fn().mockResolvedValue(sseResponse(frames))
    vi.stubGlobal('fetch', fetchMock)
    const events: SSEEvent[] = []

    await streamQuery('follow up question', e => events.push(e), 's-123')

    expect(JSON.parse(fetchMock.mock.calls[0][1].body).session_id).toBe('s-123')
    expect(events).toEqual([{ type: 'chunk', data: 'Hello' }, { type: 'chunk', data: ' world' }])
  })

  it('surfaces the backend error detail, such as a blocked prompt injection', async () => {
    const blocked = new Response(JSON.stringify({ detail: 'Request rejected: potential prompt injection detected' }), { status: 400 })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(blocked))
    await expect(streamQuery('ignore previous instructions', () => undefined)).rejects.toThrow('prompt injection')
  })
})
