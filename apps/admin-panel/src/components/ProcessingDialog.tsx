import { useCallback, useEffect, useRef, useState } from 'react'
import { Loader2, Play, RefreshCw, Trash2 } from 'lucide-react'

import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from 'components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from 'components/ui/select'
import { Button } from 'components/ui/button'
import { Label } from 'components/ui/label'
import { Badge } from 'components/ui/badge'
import { Progress } from 'components/ui/progress'
import { Alert, AlertDescription } from 'components/ui/alert'
import {
  triggerProcessing,
  getProcessingStatus,
  deleteAIData,
  getStatusLabel,
  type ProcessingJobType,
  type ProcessingStatusResponse,
} from 'lib/processing'

interface ProcessingDialogProps {
  open: boolean
  onClose: () => void
  bookId: number
  bookTitle: string
  token: string | null
  tokenType: string | null
}

const statusBadgeVariant = (status: string) => {
  switch (status) {
    case 'completed': return 'success' as const
    case 'processing': case 'queued': return 'default' as const
    case 'failed': return 'destructive' as const
    case 'partial': return 'warning' as const
    default: return 'secondary' as const
  }
}

export function ProcessingDialog({ open, onClose, bookId, bookTitle, token, tokenType }: ProcessingDialogProps) {
  const [jobType, setJobType] = useState<ProcessingJobType>('full')
  const [status, setStatus] = useState<ProcessingStatusResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchStatus = useCallback(async () => {
    if (!token || !tokenType) return
    try {
      const s = await getProcessingStatus(bookId, token, tokenType)
      setStatus(s)
    } catch {
      // Book may not have processing status yet
    }
  }, [bookId, token, tokenType])

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }, [])

  const startPolling = useCallback(() => {
    stopPolling()
    pollingRef.current = setInterval(fetchStatus, 3000)
  }, [fetchStatus, stopPolling])

  useEffect(() => {
    if (open) {
      fetchStatus()
    } else {
      stopPolling()
      setStatus(null)
      setError(null)
      setSuccess(null)
      setJobType('full')
    }
    return stopPolling
  }, [open, fetchStatus, stopPolling])

  useEffect(() => {
    if (status?.status === 'processing' || status?.status === 'queued') {
      startPolling()
    } else {
      stopPolling()
    }
  }, [status?.status, startPolling, stopPolling])

  const isProcessing = status?.status === 'processing' || status?.status === 'queued'

  const hasTextExtraction = () => {
    if (!status) return false
    return status.current_step !== 'text_extraction' && status.status !== 'queued'
  }

  const hasLLMAnalysis = () => {
    if (!status) return false
    const completedSteps = ['llm_analysis', 'audio_generation', 'vocabulary_extraction']
    return completedSteps.some((s) => status.current_step === s) || status.status === 'completed'
  }

  const handleTrigger = async () => {
    if (!token || !tokenType) return
    setLoading(true)
    setError(null)
    setSuccess(null)
    try {
      await triggerProcessing(bookId, token, tokenType, { job_type: jobType, admin_override: true })
      setSuccess('Processing started!')
      fetchStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start processing')
    } finally {
      setLoading(false)
    }
  }

  const handleClearAndReprocess = async () => {
    if (!token || !tokenType) return
    setLoading(true)
    setError(null)
    setSuccess(null)
    try {
      await deleteAIData(bookId, token, tokenType, true)
      setSuccess('Data cleared and reprocessing started!')
      fetchStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear and reprocess')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="truncate">Processing: {bookTitle}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {status && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Status</span>
                <Badge variant={statusBadgeVariant(status.status)}>
                  {getStatusLabel(status.status)}
                </Badge>
              </div>
              {isProcessing && (
                <div className="space-y-1">
                  <Progress value={status.progress} />
                  <p className="text-xs text-muted-foreground">
                    {status.progress}% — {status.current_step.replace(/_/g, ' ')}
                  </p>
                </div>
              )}
              {status.error_message && (
                <Alert variant="destructive">
                  <AlertDescription className="text-xs">{status.error_message}</AlertDescription>
                </Alert>
              )}
            </div>
          )}

          <div className="space-y-2">
            <Label>Processing Type</Label>
            <Select
              value={jobType}
              onValueChange={(v) => setJobType(v as ProcessingJobType)}
              disabled={isProcessing}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="full">Full Process (Text + AI + Audio)</SelectItem>
                <SelectItem value="text_only">Text Extraction Only</SelectItem>
                <SelectItem value="llm_only" disabled={!hasTextExtraction()}>
                  AI Analysis Only
                </SelectItem>
                <SelectItem value="audio_only" disabled={!hasLLMAnalysis()}>
                  Audio Generation Only
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {success && (
            <Alert>
              <AlertDescription>{success}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          {status && (
            <Button
              variant="destructive"
              size="sm"
              onClick={handleClearAndReprocess}
              disabled={loading || isProcessing}
              className="mr-auto"
            >
              <Trash2 className="h-4 w-4" />
              Clear & Reprocess
            </Button>
          )}
          <Button variant="ghost" size="icon" onClick={fetchStatus} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Button onClick={handleTrigger} disabled={loading || isProcessing}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Start
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default ProcessingDialog
