import { useState } from 'react'
import { Undo2 } from 'lucide-react'

interface Props {
  criticFeedback: string
  disabled: boolean
  onSend: (gaps: string) => void
}

/** The Critic's last gaps, which the analyst edits and sends back for another research pass. */
const prefill = (feedback: string) =>
  feedback.startsWith('NEEDS_REVISION') ? feedback.replace(/^NEEDS_REVISION:\s*/, '').split(' | ').join('\n') : ''

export default function SendBack({ criticFeedback, disabled, onSend }: Props) {
  const [gaps, setGaps] = useState(() => prefill(criticFeedback))

  return (
    <section aria-labelledby="sendback-h" className="card mt-[13px] px-5 md:px-8 py-5 no-print">
      <span aria-hidden className="tab bg-verm" />
      <h2 id="sendback-h" className="display text-xl [font-variation-settings:'wdth'_80]">Send back to the Researcher</h2>
      <p className="text-sm text-ink-2 mt-1 max-w-[70ch]">
        List what the report missed or got wrong. The Researcher works these gaps first, the Critic checks the result,
        and the new report is filed as a revision of this one.
      </p>
      <label htmlFor="sendback-gaps" className="label block mt-4">Gaps to address</label>
      <textarea id="sendback-gaps" rows={3} value={gaps} maxLength={2000} onChange={e => setGaps(e.target.value)}
        placeholder="e.g. No EPSS score; no affected versions; mitigations are generic"
        className="field w-full mt-1.5 px-3 py-2 resize-y leading-relaxed" />
      <button type="button" onClick={() => onSend(gaps.trim())} disabled={disabled || !gaps.trim()} className="btn-act mt-3">
        <Undo2 size={15} /> Send back
      </button>
    </section>
  )
}
