// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import SourceCard from './SourceCard'

const source = {
  text: 'Adversaries may use a single password against many accounts.',
  source: 'MITRE ATT&CK Enterprise',
  doc_type: 'mitre_attack',
  score: 0.874,
  ref_id: 'T1110.003',
}

afterEach(cleanup)

describe('SourceCard', () => {
  it('shows the technique ID, source, doc type and rounded relevance', () => {
    render(<SourceCard source={source} index={1} />)
    expect(screen.getByText('T1110.003')).toBeTruthy()
    expect(screen.getByText('MITRE ATT&CK Enterprise')).toBeTruthy()
    expect(screen.getByText('mitre attack')).toBeTruthy()
    expect(screen.getByText('sim 87%')).toBeTruthy()
  })

  it('keeps the passage collapsed until the header is clicked', () => {
    render(<SourceCard source={source} index={1} />)
    expect(screen.queryByText(source.text)).toBeNull()
    fireEvent.click(screen.getAllByRole('button')[0])
    expect(screen.getByText(source.text)).toBeTruthy()
  })

  it('labels an exact ID match instead of showing a similarity score', () => {
    render(<SourceCard source={{ ...source, exact: true }} index={1} />)
    expect(screen.getByText('exact ID match')).toBeTruthy()
    expect(screen.queryByText('sim 87%')).toBeNull()
  })

  it('omits the ID badge when the chunk has none', () => {
    render(<SourceCard source={{ ...source, ref_id: '' }} index={2} defaultExpanded />)
    expect(screen.queryByText('T1110.003')).toBeNull()
    expect(screen.getByText(source.text)).toBeTruthy()
  })
})
