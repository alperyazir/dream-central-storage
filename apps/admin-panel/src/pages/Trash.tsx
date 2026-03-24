import { useEffect, useMemo, useState } from 'react'
import { Loader2, RotateCcw, Trash2 } from 'lucide-react'

import { Card, CardContent } from 'components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from 'components/ui/table'
import { Button } from 'components/ui/button'
import { Badge } from 'components/ui/badge'
import { Alert, AlertDescription } from 'components/ui/alert'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from 'components/ui/dialog'
import { useAuthStore } from 'stores/auth'
import { listTrashEntries, restoreTrashEntry, deleteTrashEntry, type TrashEntry } from 'lib/storage'

const fmtBytes = (n: number) => {
  if (!n) return '0 B'
  const u = ['B','KB','MB','GB']
  const e = Math.min(Math.floor(Math.log(n)/Math.log(1024)), u.length-1)
  const v = n/Math.pow(1024,e)
  return `${v.toFixed(v>=10||e===0?0:1)} ${u[e]}`
}

const typeLabel = (t: string) => {
  switch (t) { case 'book': return 'Book'; case 'app': return 'App'; case 'teacher_material': return 'Teacher Material'; default: return t }
}

const getEntryLabel = (e: TrashEntry) => {
  const m = e.metadata
  if (e.item_type === 'book') {
    const pub = m?.publisher || m?.Publisher || ''
    const name = m?.book_name || m?.bookName || ''
    if (pub && name) return `${pub} / ${name}`
  }
  if (e.item_type === 'app') {
    const plat = m?.platform || m?.Platform || ''
    const ver = m?.version || m?.Version || ''
    if (plat) return `${plat} ${ver}`.trim()
  }
  if (e.item_type === 'teacher_material') {
    const tid = m?.teacher_id || m?.teacherId || ''
    if (tid) return `Teacher: ${tid}`
  }
  return e.path || e.key
}

const TrashPage = () => {
  const { token, tokenType } = useAuthStore()
  const tt = tokenType ?? 'Bearer'

  const [entries, setEntries] = useState<TrashEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [typeFilter, setTypeFilter] = useState('')
  const [restoreTarget, setRestoreTarget] = useState<TrashEntry | null>(null)
  const [restoring, setRestoring] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<TrashEntry | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [notification, setNotification] = useState<{ message: string; severity: 'success'|'error' } | null>(null)
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    if (!token) return
    setLoading(true); setError(null)
    listTrashEntries(token, tt).then(setEntries).catch(e => setError(e instanceof Error ? e.message : 'Failed to load')).finally(() => setLoading(false))
  }, [token, tt, refresh])

  const filtered = useMemo(() => {
    const d = typeFilter ? entries.filter(e => e.item_type === typeFilter) : entries
    return [...d].sort((a, b) => getEntryLabel(a).localeCompare(getEntryLabel(b)))
  }, [entries, typeFilter])

  const doRestore = async () => {
    if (!restoreTarget || !token) return
    setRestoring(true)
    try { await restoreTrashEntry(restoreTarget.key, token, tt); setNotification({ message: 'Restored!', severity: 'success' }); setRestoreTarget(null); setRefresh(v => v+1) }
    catch { setNotification({ message: 'Restore failed', severity: 'error' }) }
    finally { setRestoring(false) }
  }

  const doDelete = async () => {
    if (!deleteTarget || !token) return
    setDeleting(true)
    try { await deleteTrashEntry(deleteTarget.key, token, tt, undefined, { force: true }); setNotification({ message: 'Permanently deleted', severity: 'success' }); setDeleteTarget(null); setRefresh(v => v+1) }
    catch { setNotification({ message: 'Delete failed', severity: 'error' }) }
    finally { setDeleting(false) }
  }

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin" /></div>

  const types = [
    { value: '', label: 'All' },
    { value: 'book', label: 'Books' },
    { value: 'app', label: 'Apps' },
    { value: 'teacher_material', label: 'Teacher Materials' },
  ]

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Trash</h1>
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
      {notification && <Alert variant={notification.severity === 'error' ? 'destructive' : 'default'}><AlertDescription>{notification.message}</AlertDescription></Alert>}

      <div className="flex gap-2">
        {types.map(t => (
          <Button key={t.value} variant={typeFilter === t.value ? 'default' : 'outline'} size="sm" onClick={() => setTypeFilter(t.value)}>
            {t.label}
          </Button>
        ))}
      </div>

      <Card><CardContent className="p-0">
        <Table>
          <TableHeader><TableRow>
            <TableHead>Name</TableHead><TableHead>Type</TableHead><TableHead className="text-center">Objects</TableHead><TableHead>Size</TableHead><TableHead className="text-right">Actions</TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {!filtered.length ? (
              <TableRow><TableCell colSpan={5} className="text-center py-8 text-muted-foreground">Trash is empty</TableCell></TableRow>
            ) : filtered.map(e => (
              <TableRow key={e.key}>
                <TableCell className="font-medium">{getEntryLabel(e)}</TableCell>
                <TableCell><Badge variant="outline">{typeLabel(e.item_type)}</Badge></TableCell>
                <TableCell className="text-center">{e.object_count}</TableCell>
                <TableCell>{fmtBytes(e.total_size)}</TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-1">
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setRestoreTarget(e)}><RotateCcw className="h-4 w-4" /></Button>
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setDeleteTarget(e)}><Trash2 className="h-4 w-4 text-destructive" /></Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent></Card>

      <Dialog open={!!restoreTarget} onOpenChange={() => !restoring && setRestoreTarget(null)}>
        <DialogContent><DialogHeader><DialogTitle>Restore Item?</DialogTitle><DialogDescription>Restore &quot;{restoreTarget ? getEntryLabel(restoreTarget) : ''}&quot;?</DialogDescription></DialogHeader>
        <DialogFooter><Button variant="outline" onClick={() => setRestoreTarget(null)} disabled={restoring}>Cancel</Button><Button onClick={doRestore} disabled={restoring}>{restoring ? 'Restoring...' : 'Restore'}</Button></DialogFooter></DialogContent>
      </Dialog>
      <Dialog open={!!deleteTarget} onOpenChange={() => !deleting && setDeleteTarget(null)}>
        <DialogContent><DialogHeader><DialogTitle>Permanently Delete?</DialogTitle><DialogDescription>Permanently delete &quot;{deleteTarget ? getEntryLabel(deleteTarget) : ''}&quot;? This cannot be undone.</DialogDescription></DialogHeader>
        <DialogFooter><Button variant="outline" onClick={() => setDeleteTarget(null)} disabled={deleting}>Cancel</Button><Button variant="destructive" onClick={doDelete} disabled={deleting}>{deleting ? 'Deleting...' : 'Delete Forever'}</Button></DialogFooter></DialogContent>
      </Dialog>
    </div>
  )
}

export default TrashPage
