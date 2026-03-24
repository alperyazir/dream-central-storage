import { useEffect, useState } from 'react'
import { ChevronDown, ChevronUp, Loader2, RotateCcw } from 'lucide-react'

import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from 'components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from 'components/ui/select'
import { Button } from 'components/ui/button'
import { Input } from 'components/ui/input'
import { Label } from 'components/ui/label'
import { Switch } from 'components/ui/switch'
import { Separator } from 'components/ui/separator'
import { Alert, AlertDescription } from 'components/ui/alert'
import {
  createTeacher,
  updateTeacher,
  type Teacher,
  type TeacherListItem,
} from 'lib/teacherManagement'

interface TeacherFormDialogProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  teacher?: TeacherListItem | Teacher | null
  token: string | null
  tokenType: string | null
}

export function TeacherFormDialog({ open, onClose, onSuccess, teacher, token, tokenType }: TeacherFormDialogProps) {
  const isEdit = !!teacher

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showAISettings, setShowAISettings] = useState(false)

  const [teacherId, setTeacherId] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState('active')

  // AI settings
  const [aiAutoProcessEnabled, setAiAutoProcessEnabled] = useState<boolean | null>(null)
  const [aiProcessingPriority, setAiProcessingPriority] = useState('')
  const [aiAudioLanguages, setAiAudioLanguages] = useState('')

  useEffect(() => {
    if (!open) return
    if (teacher) {
      setTeacherId(teacher.teacher_id)
      setDisplayName(teacher.display_name || '')
      setEmail(teacher.email || '')
      setStatus(teacher.status)
      setAiAutoProcessEnabled(teacher.ai_auto_process_enabled)
      setAiProcessingPriority(teacher.ai_processing_priority || '')
      setAiAudioLanguages(teacher.ai_audio_languages || '')
      setShowAISettings(
        teacher.ai_auto_process_enabled !== null ||
        !!teacher.ai_processing_priority ||
        !!teacher.ai_audio_languages
      )
    } else {
      setTeacherId('')
      setDisplayName('')
      setEmail('')
      setStatus('active')
      setAiAutoProcessEnabled(null)
      setAiProcessingPriority('')
      setAiAudioLanguages('')
      setShowAISettings(false)
    }
    setError('')
  }, [open, teacher])

  const handleSubmit = async () => {
    if (!teacherId.trim()) { setError('Teacher ID is required'); return }
    if (!token || !tokenType) return

    setLoading(true)
    setError('')

    try {
      if (isEdit && teacher) {
        await updateTeacher(teacher.id, {
          display_name: displayName.trim() || undefined,
          email: email.trim() || undefined,
          status,
          ai_auto_process_enabled: aiAutoProcessEnabled,
          ai_processing_priority: aiProcessingPriority || null,
          ai_audio_languages: aiAudioLanguages.trim() || null,
        }, token, tokenType)
      } else {
        await createTeacher({
          teacher_id: teacherId.trim(),
          display_name: displayName.trim() || undefined,
          email: email.trim() || undefined,
          ai_auto_process_enabled: aiAutoProcessEnabled,
          ai_processing_priority: aiProcessingPriority || undefined,
          ai_audio_languages: aiAudioLanguages.trim() || undefined,
        }, token, tokenType)
      }
      onSuccess()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save teacher')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-md max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Teacher' : 'New Teacher'}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="teacher-id">Teacher ID *</Label>
            <Input
              id="teacher-id"
              value={teacherId}
              onChange={(e) => setTeacherId(e.target.value)}
              disabled={isEdit}
              placeholder={isEdit ? '' : 'e.g., teacher-001'}
            />
            <p className="text-xs text-muted-foreground">
              {isEdit ? 'Teacher ID cannot be changed' : 'Unique identifier for this teacher'}
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="teacher-name">Display Name</Label>
            <Input id="teacher-name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="e.g., John Smith" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="teacher-email">Email</Label>
            <Input id="teacher-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="teacher@school.com" />
          </div>
          {isEdit && (
            <div className="space-y-2">
              <Label>Status</Label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                  <SelectItem value="suspended">Suspended</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          <Separator />

          <button
            type="button"
            onClick={() => setShowAISettings(!showAISettings)}
            className="flex w-full items-center justify-between text-sm font-medium hover:text-primary transition-colors"
          >
            AI Processing Settings
            {showAISettings ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>

          {showAISettings && (
            <div className="space-y-4 pl-1">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Auto-process</Label>
                  <p className="text-xs text-muted-foreground">
                    {aiAutoProcessEnabled === null ? '(using default)' : aiAutoProcessEnabled ? 'Enabled' : 'Disabled'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {aiAutoProcessEnabled !== null && (
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setAiAutoProcessEnabled(null)}>
                      <RotateCcw className="h-3 w-3" />
                    </Button>
                  )}
                  <Switch
                    checked={aiAutoProcessEnabled ?? false}
                    onCheckedChange={(c) => setAiAutoProcessEnabled(c)}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Processing Priority</Label>
                <Select value={aiProcessingPriority || 'default'} onValueChange={(v) => setAiProcessingPriority(v === 'default' ? '' : v)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="default">Use default</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="normal">Normal</SelectItem>
                    <SelectItem value="low">Low</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Audio Languages</Label>
                <Input
                  value={aiAudioLanguages}
                  onChange={(e) => setAiAudioLanguages(e.target.value)}
                  placeholder="e.g., en,tr"
                />
                <p className="text-xs text-muted-foreground">Comma-separated language codes</p>
              </div>
            </div>
          )}
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={loading || !teacherId.trim()}>
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {isEdit ? 'Save Changes' : 'Create Teacher'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default TeacherFormDialog
