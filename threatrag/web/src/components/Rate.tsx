import { useState } from 'react'
import { ThumbsUp, ThumbsDown } from 'lucide-react'
import { cn } from '../lib/cn'
import { sendFeedback, type FeedbackTarget } from '../lib/feedback'

interface Props {
  target: FeedbackTarget
  targetId: string
  question: string
  answer: string
}

/** Thumbs on an answer or report. A down-vote opens a note field; voting again replaces the vote. */
export default function Rate({ target, targetId, question, answer }: Props) {
  const [rating, setRating] = useState<1 | -1 | null>(null)
  const [note, setNote] = useState('')
  const [noteSaved, setNoteSaved] = useState(false)
  const [failed, setFailed] = useState(false)

  const send = async (value: 1 | -1, withNote = '') => {
    setFailed(false)
    try {
      await sendFeedback({ target, target_id: targetId, rating: value, note: withNote, question, answer })
      setRating(value)
      return true
    } catch {
      setFailed(true)
      return false
    }
  }

  const vote = (value: 1 | -1) => { setNoteSaved(false); send(value, value === -1 ? note : '') }
  const saveNote = async () => { if (await send(-1, note.trim())) setNoteSaved(true) }

  return (
    <div className="no-print text-xs">
      <div className="flex items-center gap-1">
        <span className="text-ink-3 mr-1">{rating === null ? 'Was this useful?' : 'Feedback filed'}</span>
        <button type="button" aria-label="Helpful" aria-pressed={rating === 1} onClick={() => vote(1)}
          className={cn('btn-text p-1.5', rating === 1 && 'text-green')}>
          <ThumbsUp size={14} />
        </button>
        <button type="button" aria-label="Not helpful" aria-pressed={rating === -1} onClick={() => vote(-1)}
          className={cn('btn-text p-1.5', rating === -1 && 'text-verm')}>
          <ThumbsDown size={14} />
        </button>
        {failed && <span role="alert" className="text-verm ml-2">Not saved: feedback storage is unavailable</span>}
      </div>
      {rating === -1 && (
        <div className="flex flex-wrap items-center gap-2 mt-2 animate-file-in">
          <label htmlFor={`note-${target}-${targetId}`} className="sr-only">What was wrong?</label>
          <input id={`note-${target}-${targetId}`} value={note} maxLength={2000}
            onChange={e => { setNote(e.target.value); setNoteSaved(false) }}
            placeholder="What was wrong or missing?" className="field flex-1 min-w-[14rem] px-2.5 py-1.5" />
          <button type="button" onClick={saveNote} disabled={!note.trim() || noteSaved} className="btn-line text-xs">
            {noteSaved ? 'Note filed' : 'File note'}
          </button>
        </div>
      )}
    </div>
  )
}
