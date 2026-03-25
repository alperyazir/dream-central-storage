import { useEffect, useState } from 'react'
import { Loader2, Plus, Trash2, Copy, Check, Key, Eye, EyeOff } from 'lucide-react'

import { Card, CardContent } from 'components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from 'components/ui/table'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from 'components/ui/dialog'
import { Input } from 'components/ui/input'
import { Label } from 'components/ui/label'
import { Textarea } from 'components/ui/textarea'
import { Button } from 'components/ui/button'
import { Badge } from 'components/ui/badge'
import { Alert, AlertDescription } from 'components/ui/alert'
import { useAuthStore } from 'stores/auth'
import { listApiKeys, createApiKey, revokeApiKey, type ApiKeyRead, type ApiKeyCreated } from 'lib/apiKeys'

const fmtDate = (s: string | null) =>
  s ? new Date(s).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'

const isExpired = (s: string | null) => s ? new Date(s) < new Date() : false

const ApiKeysPage = () => {
  const { token, tokenType } = useAuthStore()
  const tt = tokenType ?? 'Bearer'

  const [keys, setKeys] = useState<ApiKeyRead[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Create dialog
  const [createOpen, setCreateOpen] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [rateLimit, setRateLimit] = useState(100)
  const [creating, setCreating] = useState(false)

  // Created key display
  const [createdKey, setCreatedKey] = useState<ApiKeyCreated | null>(null)
  const [showKey, setShowKey] = useState(false)
  const [copied, setCopied] = useState(false)

  // Revoke dialog
  const [revokeTarget, setRevokeTarget] = useState<ApiKeyRead | null>(null)
  const [revoking, setRevoking] = useState(false)

  const load = async () => {
    if (!token) return
    setLoading(true); setError(null)
    try {
      const r = await listApiKeys(token, tt)
      setKeys(r.api_keys)
    } catch (e) { setError(e instanceof Error ? e.message : 'Failed to load') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [token])

  const handleCreate = async () => {
    if (!token || !name.trim()) return
    setCreating(true); setError(null)
    try {
      const created = await createApiKey({
        name: name.trim(),
        description: description.trim() || undefined,
        rate_limit: rateLimit,
      }, token, tt)
      setCreatedKey(created)
      setCreateOpen(false)
      setName(''); setDescription(''); setRateLimit(100)
      load()
    } catch (e) { setError(e instanceof Error ? e.message : 'Failed to create') }
    finally { setCreating(false) }
  }

  const handleRevoke = async () => {
    if (!token || !revokeTarget) return
    setRevoking(true)
    try {
      await revokeApiKey(revokeTarget.id, token, tt)
      setRevokeTarget(null)
      load()
    } catch (e) { setError(e instanceof Error ? e.message : 'Failed to revoke') }
    finally { setRevoking(false) }
  }

  const handleCopy = async (text: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin" /></div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">API Keys</h1>
          <p className="text-muted-foreground">Manage API keys for external service authentication (e.g. LMS integration).</p>
        </div>
        <Button onClick={() => setCreateOpen(true)}><Plus className="h-4 w-4" /> Create Key</Button>
      </div>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      {/* Created key banner - shown once after creation */}
      {createdKey && (
        <Alert>
          <Key className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-2">
              <p className="font-medium">API key created! Copy it now — it won't be shown again.</p>
              <div className="flex items-center gap-2">
                <code className="flex-1 rounded bg-muted px-3 py-2 text-sm font-mono">
                  {showKey ? createdKey.key : '•'.repeat(40)}
                </code>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setShowKey(!showKey)}>
                  {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleCopy(createdKey.key)}>
                  {copied ? <Check className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
                </Button>
              </div>
              <Button variant="outline" size="sm" onClick={() => setCreatedKey(null)}>Dismiss</Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Key Prefix</TableHead>
                <TableHead>Rate Limit</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Last Used</TableHead>
                <TableHead>Expires</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {!keys.length ? (
                <TableRow><TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
                  <Key className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  No API keys created yet
                </TableCell></TableRow>
              ) : keys.map(k => (
                <TableRow key={k.id}>
                  <TableCell className="font-medium">{k.name}</TableCell>
                  <TableCell><code className="text-xs bg-muted px-1.5 py-0.5 rounded">{k.key_prefix}</code></TableCell>
                  <TableCell>{k.rate_limit}/min</TableCell>
                  <TableCell className="text-xs">{fmtDate(k.created_at)}</TableCell>
                  <TableCell className="text-xs">{fmtDate(k.last_used_at)}</TableCell>
                  <TableCell className="text-xs">{k.expires_at ? fmtDate(k.expires_at) : 'Never'}</TableCell>
                  <TableCell>
                    {!k.is_active ? (
                      <Badge variant="destructive">Revoked</Badge>
                    ) : isExpired(k.expires_at) ? (
                      <Badge variant="warning">Expired</Badge>
                    ) : (
                      <Badge variant="success">Active</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    {k.is_active && (
                      <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setRevokeTarget(k)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={createOpen} onOpenChange={o => !creating && !o && setCreateOpen(false)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create API Key</DialogTitle>
            <DialogDescription>Create a new key for external service authentication.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="key-name">Name *</Label>
              <Input id="key-name" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. LMS Production" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="key-desc">Description</Label>
              <Textarea id="key-desc" value={description} onChange={e => setDescription(e.target.value)} placeholder="What is this key used for?" rows={2} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="key-rate">Rate Limit (requests/min)</Label>
              <Input id="key-rate" type="number" min={1} max={10000} value={rateLimit} onChange={e => setRateLimit(Number(e.target.value))} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)} disabled={creating}>Cancel</Button>
            <Button onClick={handleCreate} disabled={creating || !name.trim()}>
              {creating && <Loader2 className="h-4 w-4 animate-spin" />} Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Revoke Dialog */}
      <Dialog open={!!revokeTarget} onOpenChange={() => !revoking && setRevokeTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Revoke API Key?</DialogTitle>
            <DialogDescription>Revoke &quot;{revokeTarget?.name}&quot;? Any services using this key will lose access immediately.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRevokeTarget(null)} disabled={revoking}>Cancel</Button>
            <Button variant="destructive" onClick={handleRevoke} disabled={revoking}>
              {revoking ? 'Revoking...' : 'Revoke Key'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default ApiKeysPage
