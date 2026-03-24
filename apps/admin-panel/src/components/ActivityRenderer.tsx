import { useCallback, useRef, useState } from 'react'
import { Play, Square, Volume2 } from 'lucide-react'

import { Button } from 'components/ui/button'
import { Badge } from 'components/ui/badge'
import { type AIContentRead, getAIContentAudioUrl } from 'lib/aiContent'
import { buildAuthHeaders } from 'lib/http'

interface ContentItem {
  item_id?: string
  correct_sentence?: string
  sentence?: string
  text?: string
  question?: string
  prompt?: string
  words?: string[]
  word_count?: number
  audio_url?: string
  audio_status?: string
  audio_data?: { audio_base64: string; duration_seconds?: number }
  difficulty?: string
  answer?: string
  correct_answer?: string | number
  blank?: string
  options?: string[]
  explanation?: string
  word?: string
  translation?: string
  definition?: string
  pairs?: Array<{ term: string; match: string }>
}

interface StorageAudioFile {
  filename: string
  path: string
  size?: number
}

interface ActivityRendererProps {
  content: AIContentRead
  bookId: number
  token: string
  tokenType: string
}

const diffBadge = (d: string | null) => {
  if (!d) return null
  const v = d.toLowerCase()
  const variant = v === 'easy' || v === 'beginner' ? 'success' as const
    : v === 'hard' || v === 'advanced' ? 'destructive' as const
    : 'warning' as const
  return <Badge variant={variant} className="text-xs">{d}</Badge>
}

export function ActivityRenderer({ content, bookId, token, tokenType }: ActivityRendererProps) {
  const [playingKey, setPlayingKey] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const stopAudio = useCallback(() => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null }
    setPlayingKey(null)
  }, [])

  const playBase64 = useCallback((key: string, base64: string) => {
    stopAudio()
    if (playingKey === key) return
    const audio = new Audio(`data:audio/mp3;base64,${base64}`)
    audio.onended = stopAudio
    audio.onerror = stopAudio
    audio.play().catch(stopAudio)
    audioRef.current = audio
    setPlayingKey(key)
  }, [playingKey, stopAudio])

  const playStorageAudio = useCallback(async (key: string, filename: string) => {
    stopAudio()
    if (playingKey === key) return
    const url = getAIContentAudioUrl(bookId, content.content_id, filename)
    try {
      const resp = await fetch(url, { headers: buildAuthHeaders(token, tokenType) })
      if (!resp.ok) return
      const blob = await resp.blob()
      const objUrl = URL.createObjectURL(blob)
      const audio = new Audio(objUrl)
      audio.onended = () => { stopAudio(); URL.revokeObjectURL(objUrl) }
      audio.onerror = () => { stopAudio(); URL.revokeObjectURL(objUrl) }
      audio.play().catch(stopAudio)
      audioRef.current = audio
      setPlayingKey(key)
    } catch { stopAudio() }
  }, [playingKey, stopAudio, bookId, content.content_id, token, tokenType])

  const AudioBtn = ({ audioKey, onPlay }: { audioKey: string; onPlay: () => void }) => (
    <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={e => { e.stopPropagation(); playingKey === audioKey ? stopAudio() : onPlay() }}>
      {playingKey === audioKey ? <Square className="h-3.5 w-3.5 text-primary" /> : <Play className="h-3.5 w-3.5" />}
    </Button>
  )

  const data = content.content as Record<string, unknown>
  const items = (data.items ?? data.questions ?? data.sentences ?? data.words ?? []) as ContentItem[]
  const passage = data.passage as string | undefined
  const storageAudio = (data.audio_files ?? data.storage_audio ?? []) as StorageAudioFile[]

  return (
    <div className="space-y-3">
      {/* Passage text if present */}
      {passage && (
        <div className="rounded-md bg-muted p-3 text-sm italic text-muted-foreground whitespace-pre-wrap max-h-[120px] overflow-auto">
          {passage}
        </div>
      )}

      {/* Items */}
      {items.length > 0 && (
        <div className="space-y-1.5">
          {items.map((item, i) => {
            const audioKey = `${content.content_id}:${i}`
            const hasBase64 = !!item.audio_data?.audio_base64
            const label = item.correct_sentence ?? item.sentence ?? item.question ?? item.text ?? item.prompt ?? item.word ?? ''

            return (
              <div key={item.item_id ?? i} className="flex items-start gap-2 rounded-md bg-muted/50 p-2.5 text-sm">
                <span className="text-muted-foreground min-w-[20px] pt-0.5">{i + 1}.</span>
                <div className="flex-1 space-y-1.5">
                  {/* Main text */}
                  <p className="font-medium">{label}</p>

                  {/* Translation / definition */}
                  {item.translation && <p className="text-xs text-muted-foreground">Translation: {item.translation}</p>}
                  {item.definition && <p className="text-xs text-muted-foreground">Definition: {item.definition}</p>}

                  {/* Options (MCQ / fill-blank) */}
                  {item.options && item.options.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {item.options.map((opt, j) => {
                        const isCorrect = item.correct_answer === opt || item.correct_answer === j || item.answer === opt || Number(item.answer) === j
                        return (
                          <Badge key={j} variant={isCorrect ? 'success' : 'outline'} className="text-xs">
                            {String.fromCharCode(65 + j)}) {opt} {isCorrect && '✓'}
                          </Badge>
                        )
                      })}
                    </div>
                  )}

                  {/* Answer for fill-blank */}
                  {item.answer && !item.options?.length && (
                    <Badge variant="success" className="text-xs">Answer: {item.answer}</Badge>
                  )}

                  {/* Word chips (sentence builder) */}
                  {item.words && item.words.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {item.words.map((w, j) => <Badge key={j} variant="outline" className="text-xs">{w}</Badge>)}
                    </div>
                  )}

                  {/* Matching pairs */}
                  {item.pairs && item.pairs.length > 0 && (
                    <div className="space-y-0.5">
                      {item.pairs.map((p, j) => (
                        <div key={j} className="flex items-center gap-2 text-xs">
                          <span className="font-medium">{p.term}</span>
                          <span className="text-muted-foreground">→</span>
                          <span>{p.match}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Explanation */}
                  {item.explanation && <p className="text-xs italic text-muted-foreground">{item.explanation}</p>}

                  {/* Duration */}
                  {item.audio_data?.duration_seconds != null && (
                    <span className="text-xs text-muted-foreground">{item.audio_data.duration_seconds.toFixed(1)}s</span>
                  )}
                </div>

                {/* Difficulty */}
                {diffBadge(item.difficulty ?? null)}

                {/* Play base64 audio */}
                {hasBase64 && (
                  <AudioBtn audioKey={audioKey} onPlay={() => playBase64(audioKey, item.audio_data!.audio_base64)} />
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Storage audio files */}
      {storageAudio.length > 0 && (
        <div className="space-y-1">
          <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
            <Volume2 className="h-3.5 w-3.5" /> Audio Files ({storageAudio.length})
          </div>
          {storageAudio.map((af, i) => {
            const audioKey = `storage:${content.content_id}:${af.filename}`
            return (
              <div key={i} className="flex items-center gap-2 rounded-md bg-muted/50 p-2 text-xs">
                <AudioBtn audioKey={audioKey} onPlay={() => playStorageAudio(audioKey, af.filename)} />
                <span className="flex-1 truncate">{af.filename}</span>
                {af.size != null && <span className="text-muted-foreground">{(af.size / 1024).toFixed(0)} KB</span>}
              </div>
            )
          })}
        </div>
      )}

      {/* Fallback if no items and no audio */}
      {items.length === 0 && storageAudio.length === 0 && !passage && (
        <pre className="max-h-[150px] overflow-auto rounded-md bg-muted p-2 text-xs whitespace-pre-wrap">
          {JSON.stringify(data, null, 2).slice(0, 1500)}
        </pre>
      )}
    </div>
  )
}

export default ActivityRenderer
