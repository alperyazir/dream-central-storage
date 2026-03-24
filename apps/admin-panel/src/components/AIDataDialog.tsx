import { useCallback, useEffect, useState } from 'react'
import { Loader2, CheckCircle, XCircle, Clock, Play, Square, Trash2, ChevronDown, ChevronRight } from 'lucide-react'

import { Dialog, DialogContent, DialogHeader, DialogTitle } from 'components/ui/dialog'
import { Card, CardContent, CardHeader, CardTitle } from 'components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from 'components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from 'components/ui/table'
import { Button } from 'components/ui/button'
import { Badge } from 'components/ui/badge'
import {
  getAIMetadata, getAIModules, getAIModuleDetail, getAIVocabulary,
  type AIMetadata, type ModuleSummary, type ModuleDetail, type VocabularyWord
} from 'lib/processing'
import {
  listAIContent, getAIContent, deleteAIContent,
  type ManifestRead, type AIContentRead
} from 'lib/aiContent'
import { Alert, AlertDescription } from 'components/ui/alert'
import ActivityRenderer from 'components/ActivityRenderer'

const fmtDate = (s: string | null) => s ? new Date(s).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'

const stageIcon = (s: string) => {
  if (s === 'completed') return <CheckCircle className="h-4 w-4 text-green-600" />
  if (s === 'failed') return <XCircle className="h-4 w-4 text-destructive" />
  if (s === 'processing') return <Loader2 className="h-4 w-4 animate-spin text-primary" />
  return <Clock className="h-4 w-4 text-muted-foreground" />
}

interface AIDataDialogProps {
  open: boolean
  onClose: () => void
  bookId: number
  bookTitle: string
  token: string | null
  tokenType: string
}

export function AIDataDialog({ open, onClose, bookId, bookTitle, token, tokenType }: AIDataDialogProps) {
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('metadata')
  const [metadata, setMetadata] = useState<AIMetadata | null>(null)
  const [modules, setModules] = useState<ModuleSummary[]>([])
  const [expandedModule, setExpandedModule] = useState<number | null>(null)
  const [moduleDetails, setModuleDetails] = useState<Record<number, ModuleDetail>>({})
  const [vocabulary, setVocabulary] = useState<VocabularyWord[]>([])
  const [playingWord, setPlayingWord] = useState<string | null>(null)
  const [audioEl, setAudioEl] = useState<HTMLAudioElement | null>(null)
  const [activities, setActivities] = useState<ManifestRead[]>([])
  const [expandedActivity, setExpandedActivity] = useState<string | null>(null)
  const [activityDetails, setActivityDetails] = useState<Record<string, AIContentRead>>({})
  const [deleteTarget, setDeleteTarget] = useState<ManifestRead | null>(null)
  const [deleting, setDeleting] = useState(false)

  const loadData = useCallback(async () => {
    if (!token || !bookId) return
    setLoading(true)
    setMetadata(null); setModules([]); setVocabulary([]); setActivities([])
    setExpandedModule(null); setModuleDetails({}); setExpandedActivity(null); setActivityDetails({})
    try {
      const [meta, mods, vocab, acts] = await Promise.all([
        getAIMetadata(bookId, token, tokenType).catch(() => null),
        getAIModules(bookId, token, tokenType).catch(() => ({ modules: [] as ModuleSummary[] })),
        getAIVocabulary(bookId, token, tokenType).catch(() => ({ words: [] as VocabularyWord[] })),
        listAIContent(bookId, token, tokenType).catch(() => [] as ManifestRead[])
      ])
      setMetadata(meta); setModules(mods.modules); setVocabulary(vocab.words); setActivities(acts)
    } catch {}
    finally { setLoading(false) }
  }, [bookId, token, tokenType])

  useEffect(() => {
    if (open) { setTab('metadata'); loadData() }
    else { if (audioEl) { audioEl.pause(); setAudioEl(null) }; setPlayingWord(null) }
  }, [open, loadData])

  const toggleModule = async (moduleId: number) => {
    if (expandedModule === moduleId) { setExpandedModule(null); return }
    setExpandedModule(moduleId)
    if (!moduleDetails[moduleId] && token) {
      try {
        const d = await getAIModuleDetail(bookId, moduleId, token, tokenType)
        setModuleDetails(p => ({ ...p, [moduleId]: d }))
      } catch {}
    }
  }

  const playAudio = (word: string, src: string | null) => {
    if (audioEl) { audioEl.pause(); setAudioEl(null) }
    if (playingWord === word || !src) { setPlayingWord(null); return }
    const audio = new Audio(src)
    audio.onended = () => { setPlayingWord(null); setAudioEl(null) }
    audio.play().catch(() => {})
    setPlayingWord(word); setAudioEl(audio)
  }

  const toggleActivity = async (contentId: string) => {
    if (expandedActivity === contentId) { setExpandedActivity(null); return }
    setExpandedActivity(contentId)
    if (!activityDetails[contentId] && token) {
      try {
        const d = await getAIContent(bookId, contentId, token, tokenType)
        setActivityDetails(p => ({ ...p, [contentId]: d }))
      } catch {}
    }
  }

  const handleDeleteActivity = async () => {
    if (!deleteTarget || !token) return
    setDeleting(true)
    try {
      await deleteAIContent(bookId, deleteTarget.content_id, token, tokenType)
      setActivities(p => p.filter(a => a.content_id !== deleteTarget.content_id))
      setDeleteTarget(null)
    } catch {}
    finally { setDeleting(false) }
  }

  const difficultyColor = (d: string | null) => {
    if (!d) return 'secondary' as const
    if (d.toLowerCase() === 'easy') return 'success' as const
    if (d.toLowerCase() === 'hard') return 'destructive' as const
    return 'warning' as const
  }

  return (
    <Dialog open={open} onOpenChange={o => !o && onClose()}>
      <DialogContent className="sm:max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>AI Data: {bookTitle}</DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin" /></div>
        ) : (
          <Tabs value={tab} onValueChange={setTab}>
            <TabsList>
              <TabsTrigger value="metadata">Metadata</TabsTrigger>
              <TabsTrigger value="modules">Modules ({modules.length})</TabsTrigger>
              <TabsTrigger value="vocabulary">Vocabulary ({vocabulary.length})</TabsTrigger>
              <TabsTrigger value="activities">Activities ({activities.length})</TabsTrigger>
            </TabsList>

            <TabsContent value="metadata">
              {!metadata ? <p className="py-4 text-center text-sm text-muted-foreground">No metadata available</p> : (
                <div className="space-y-4">
                  <Card>
                    <CardHeader className="p-4 pb-2"><CardTitle className="text-sm">Overview</CardTitle></CardHeader>
                    <CardContent className="grid grid-cols-2 gap-3 p-4 pt-0 text-sm md:grid-cols-3">
                      <div><span className="text-muted-foreground">Status:</span> <Badge>{metadata.processing_status}</Badge></div>
                      <div><span className="text-muted-foreground">Pages:</span> {metadata.total_pages}</div>
                      <div><span className="text-muted-foreground">Modules:</span> {metadata.total_modules}</div>
                      <div><span className="text-muted-foreground">Vocabulary:</span> {metadata.total_vocabulary}</div>
                      <div><span className="text-muted-foreground">Audio:</span> {metadata.total_audio_files}</div>
                      <div><span className="text-muted-foreground">Language:</span> {metadata.primary_language}</div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="p-4 pb-2"><CardTitle className="text-sm">Processing Stages</CardTitle></CardHeader>
                    <CardContent className="p-0">
                      <Table>
                        <TableHeader><TableRow><TableHead>Stage</TableHead><TableHead>Status</TableHead><TableHead>Completed</TableHead><TableHead>Error</TableHead></TableRow></TableHeader>
                        <TableBody>
                          {Object.entries(metadata.stages).map(([name, stage]) => (
                            <TableRow key={name}>
                              <TableCell className="font-medium capitalize text-xs">{name.replace(/_/g, ' ')}</TableCell>
                              <TableCell><div className="flex items-center gap-1.5 text-xs">{stageIcon(stage.status)} {stage.status}</div></TableCell>
                              <TableCell className="text-xs">{fmtDate(stage.completed_at)}</TableCell>
                              <TableCell className="text-xs text-destructive max-w-[150px] truncate">{stage.error_message || '—'}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </CardContent>
                  </Card>
                </div>
              )}
            </TabsContent>

            <TabsContent value="modules">
              {!modules.length ? <p className="py-4 text-center text-sm text-muted-foreground">No modules</p> : (
                <div className="space-y-1">
                  {modules.map(m => (
                    <div key={m.module_id}>
                      <button className="flex w-full items-center justify-between rounded-md p-2.5 text-sm hover:bg-muted transition-colors text-left" onClick={() => toggleModule(m.module_id)}>
                        <div><span className="font-medium">{m.title}</span><span className="ml-2 text-xs text-muted-foreground">Pages: {m.pages.join(', ')} | Words: {m.word_count}</span></div>
                        <span className="text-xs">{expandedModule === m.module_id ? '▼' : '▶'}</span>
                      </button>
                      {expandedModule === m.module_id && moduleDetails[m.module_id] && (
                        <div className="ml-4 space-y-2 border-l pl-4 pb-2 text-sm">
                          {moduleDetails[m.module_id].topics.length > 0 && <div className="flex flex-wrap gap-1">{moduleDetails[m.module_id].topics.map(t => <Badge key={t} variant="outline" className="text-xs">{t}</Badge>)}</div>}
                          {moduleDetails[m.module_id].grammar_points.length > 0 && <div className="flex flex-wrap gap-1">{moduleDetails[m.module_id].grammar_points.map(g => <Badge key={g} variant="secondary" className="text-xs">{g}</Badge>)}</div>}
                          {moduleDetails[m.module_id].summary && <p className="text-xs text-muted-foreground">{moduleDetails[m.module_id].summary}</p>}
                          {moduleDetails[m.module_id].text && <pre className="max-h-[150px] overflow-auto rounded-md bg-muted p-2 text-xs whitespace-pre-wrap">{moduleDetails[m.module_id].text.slice(0, 500)}</pre>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="vocabulary">
              {!vocabulary.length ? <p className="py-4 text-center text-sm text-muted-foreground">No vocabulary</p> : (
                <Table>
                  <TableHeader><TableRow>
                    <TableHead>Word</TableHead><TableHead>Translation</TableHead><TableHead>POS</TableHead><TableHead>Level</TableHead><TableHead>Audio</TableHead>
                  </TableRow></TableHeader>
                  <TableBody>
                    {vocabulary.map(w => (
                      <TableRow key={w.id}>
                        <TableCell className="font-medium text-xs">{w.word}</TableCell>
                        <TableCell className="text-xs">{w.translation}</TableCell>
                        <TableCell><Badge variant="outline" className="text-xs">{w.part_of_speech}</Badge></TableCell>
                        <TableCell><Badge variant="default" className="text-xs">{w.level}</Badge></TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            {w.audio?.word && (
                              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => playAudio(`word-${w.id}`, w.audio!.word)}>
                                {playingWord === `word-${w.id}` ? <Square className="h-3 w-3" /> : <Play className="h-3 w-3" />}
                              </Button>
                            )}
                            {w.audio?.translation && (
                              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => playAudio(`trans-${w.id}`, w.audio!.translation)}>
                                {playingWord === `trans-${w.id}` ? <Square className="h-3 w-3 text-secondary" /> : <Play className="h-3 w-3 text-secondary" />}
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </TabsContent>
            <TabsContent value="activities">
              {!activities.length ? <p className="py-4 text-center text-sm text-muted-foreground">No activities</p> : (
                <div className="space-y-1">
                  {activities.map(a => (
                    <div key={a.content_id} className="rounded-md border">
                      <button className="flex w-full items-center gap-2 p-2.5 text-sm hover:bg-muted transition-colors text-left" onClick={() => toggleActivity(a.content_id)}>
                        {expandedActivity === a.content_id ? <ChevronDown className="h-4 w-4 shrink-0" /> : <ChevronRight className="h-4 w-4 shrink-0" />}
                        <span className="font-medium flex-1 truncate">{a.title}</span>
                        <Badge variant="outline" className="text-xs">{a.activity_type}</Badge>
                        {a.difficulty && <Badge variant={difficultyColor(a.difficulty)} className="text-xs">{a.difficulty}</Badge>}
                        <span className="text-xs text-muted-foreground">{a.item_count} items</span>
                        <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0" onClick={e => { e.stopPropagation(); setDeleteTarget(a) }}>
                          <Trash2 className="h-3 w-3 text-destructive" />
                        </Button>
                      </button>
                      {expandedActivity === a.content_id && (
                        <div className="border-t p-3 space-y-2">
                          <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                            <Badge variant="outline" className="text-xs">{a.activity_type.replace(/[_-]/g, ' ')}</Badge>
                            <span>Language: {a.language}</span>
                            {a.has_audio && <Badge variant="outline" className="text-xs">Audio</Badge>}
                            {a.has_passage && <Badge variant="outline" className="text-xs">Passage</Badge>}
                            {a.created_by && <span>By: {a.created_by.slice(0, 12)}</span>}
                            {a.created_at && <span>{fmtDate(a.created_at)}</span>}
                          </div>
                          {activityDetails[a.content_id] ? (
                            <ActivityRenderer content={activityDetails[a.content_id]} bookId={bookId} token={token!} tokenType={tokenType} />
                          ) : (
                            <div className="flex items-center gap-2 text-xs text-muted-foreground"><Loader2 className="h-3 w-3 animate-spin" /> Loading...</div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
        )}

        {deleteTarget && (
          <Alert variant="destructive" className="mt-2">
            <AlertDescription className="flex items-center justify-between">
              <span>Delete &quot;{deleteTarget.title}&quot;?</span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setDeleteTarget(null)} disabled={deleting}>Cancel</Button>
                <Button variant="destructive" size="sm" onClick={handleDeleteActivity} disabled={deleting}>{deleting ? 'Deleting...' : 'Delete'}</Button>
              </div>
            </AlertDescription>
          </Alert>
        )}
      </DialogContent>
    </Dialog>
  )
}

export default AIDataDialog
