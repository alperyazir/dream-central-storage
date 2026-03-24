import { useEffect, useMemo, useState } from 'react'
import { BookOpen, AppWindow, Building2, HardDrive, Loader2 } from 'lucide-react'

import { Card, CardContent } from 'components/ui/card'
import { Button } from 'components/ui/button'
import { Alert, AlertDescription } from 'components/ui/alert'

import { fetchBooks, type BookRecord } from 'lib/books'
import { SUPPORTED_APP_PLATFORMS, toPlatformSlug } from 'lib/platforms'
import { listAppContents, type StorageNode } from 'lib/storage'
import { listTemplates, listBundles, type TemplateInfo, type BundleInfo } from 'lib/standaloneApps'
import { useAuthStore } from 'stores/auth'
import UploadDialog from 'components/UploadDialog'

const fmtBytes = (n?: number) => {
  if (!n) return '0 B'
  const u = ['B', 'KB', 'MB', 'GB', 'TB']
  const e = Math.min(Math.floor(Math.log(n) / Math.log(1024)), u.length - 1)
  const v = n / Math.pow(1024, e)
  return `${v.toFixed(v >= 10 || e === 0 ? 0 : 1)} ${u[e]}`
}

const sumStorageTree = (node: StorageNode | undefined): number => {
  if (!node) return 0
  if (node.type === 'file') return node.size ?? 0
  return (node.children ?? []).reduce((acc, c) => acc + sumStorageTree(c), 0)
}

const DashboardPage = () => {
  const { token, tokenType, isAuthenticated } = useAuthStore()
  const tt = tokenType ?? 'Bearer'

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [books, setBooks] = useState<BookRecord[]>([])
  const [templates, setTemplates] = useState<TemplateInfo[]>([])
  const [bundles, setBundles] = useState<BundleInfo[]>([])
  const [appStorageSize, setAppStorageSize] = useState(0)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setBooks([]); setTemplates([]); setBundles([]); setAppStorageSize(0); setLoading(false)
      return
    }
    let alive = true
    setLoading(true); setError(null)
    Promise.all([
      fetchBooks(token, tt),
      listTemplates(token, tt).catch(() => ({ templates: [] as TemplateInfo[] })),
      listBundles(token, tt).catch(() => ({ bundles: [] as BundleInfo[] })),
      ...SUPPORTED_APP_PLATFORMS.map(p => listAppContents(toPlatformSlug(p), token, tt).catch(() => undefined))
    ]).then(([bks, tpls, bnds, ...appTrees]) => {
      if (!alive) return
      setBooks(bks as BookRecord[])
      setTemplates((tpls as { templates: TemplateInfo[] }).templates)
      setBundles((bnds as { bundles: BundleInfo[] }).bundles)
      setAppStorageSize((appTrees as (StorageNode | undefined)[]).reduce((acc, t) => acc + sumStorageTree(t), 0))
    }).catch(e => { if (alive) setError(e instanceof Error ? e.message : 'Failed to load') })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [isAuthenticated, token, tt, refresh])

  const publishers = useMemo(() => new Set(books.map(b => b.publisher)).size, [books])
  const appBuildCount = templates.length + bundles.length

  const totalBookSize = useMemo(() => books.reduce((a, b) => a + (b.total_size || 0), 0), [books])
  const totalTemplateSize = useMemo(() => templates.reduce((a, b) => a + b.file_size, 0), [templates])
  const totalBundleSize = useMemo(() => bundles.reduce((a, b) => a + b.file_size, 0), [bundles])
  const totalStorage = totalBookSize + totalTemplateSize + totalBundleSize + appStorageSize

  const uploadOpts = useMemo(() => books.map(b => ({ id: b.id, title: b.book_name, publisher: b.publisher })), [books])

  if (loading && !books.length) return (
    <div className="flex items-center justify-center py-20 gap-2">
      <Loader2 className="h-6 w-6 animate-spin text-primary" />
      <span className="text-muted-foreground">Loading dashboard...</span>
    </div>
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-muted-foreground">Review stored content at a glance.</p>
        </div>
        <Button onClick={() => setUploadOpen(true)}>Upload</Button>
      </div>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { icon: BookOpen, label: 'Total Books', value: String(books.length), color: 'bg-teal-600' },
          { icon: AppWindow, label: 'App Builds', value: String(appBuildCount), color: 'bg-blue-600' },
          { icon: Building2, label: 'Publishers', value: String(publishers), color: 'bg-green-600' },
          { icon: HardDrive, label: 'Total Storage', value: fmtBytes(totalStorage), color: 'bg-amber-500' },
        ].map(s => (
          <Card key={s.label}>
            <CardContent className="flex items-center gap-3 p-4">
              <div className={`${s.color} text-white p-2.5 rounded-lg`}>
                <s.icon className="h-5 w-5" />
              </div>
              <div>
                <div className="text-2xl font-bold">{s.value}</div>
                <div className="text-xs text-muted-foreground">{s.label}</div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <UploadDialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        books={uploadOpts}
        platforms={SUPPORTED_APP_PLATFORMS}
        token={token}
        tokenType={tt}
        onSuccess={() => setRefresh(v => v + 1)}
      />
    </div>
  )
}

export default DashboardPage
