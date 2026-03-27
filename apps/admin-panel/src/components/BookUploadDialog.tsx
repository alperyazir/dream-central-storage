import { useCallback, useEffect, useState, DragEvent } from 'react';
import { Loader2, Upload, X, CheckCircle, XCircle } from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from 'components/ui/dialog';
import { Button } from 'components/ui/button';
import { Checkbox } from 'components/ui/checkbox';
import { Label } from 'components/ui/label';
import { Alert, AlertDescription } from 'components/ui/alert';
import { Badge } from 'components/ui/badge';
import { Progress } from 'components/ui/progress';
import {
  uploadNewBookArchive,
  uploadBulkBookArchives,
  type BulkUploadResult,
} from 'lib/uploads';

interface BookUploadDialogProps {
  open: boolean;
  onClose: () => void;
  token: string | null;
  tokenType: string | null;
  onSuccess: () => void;
}

export function BookUploadDialog({
  open,
  onClose,
  token,
  tokenType,
  onSuccess,
}: BookUploadDialogProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [feedback, setFeedback] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);
  const [uploadResults, setUploadResults] = useState<BulkUploadResult[]>([]);
  const [overrideExisting, setOverrideExisting] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    if (!open) {
      setFiles([]);
      setUploading(false);
      setFeedback(null);
      setUploadResults([]);
      setOverrideExisting(false);
      setDragOver(false);
    }
  }, [open]);

  const handleDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = Array.from(e.dataTransfer.files).filter((f) =>
      f.name.endsWith('.zip')
    );
    if (dropped.length) setFiles((prev) => [...prev, ...dropped].slice(0, 50));
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || []);
    setFiles((prev) => [...prev, ...selected].slice(0, 50));
    e.target.value = '';
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (!files.length || !token || !tokenType) return;
    setUploading(true);
    setFeedback(null);
    setUploadResults([]);

    try {
      if (files.length === 1) {
        await uploadNewBookArchive(files[0], token, tokenType, undefined, {
          override: overrideExisting,
        });
        setFeedback({
          type: 'success',
          message: 'Book uploaded successfully!',
        });
        onSuccess();
        setTimeout(onClose, 1500);
      } else {
        const response = await uploadBulkBookArchives(
          files,
          token,
          tokenType,
          undefined,
          { override: overrideExisting }
        );
        setUploadResults(response.results);
        if (response.failed === 0) {
          setFeedback({
            type: 'success',
            message: `All ${response.successful} books uploaded successfully!`,
          });
          onSuccess();
          setTimeout(onClose, 2000);
        } else {
          setFeedback({
            type: 'error',
            message: `${response.successful} succeeded, ${response.failed} failed out of ${response.total} uploads.`,
          });
          onSuccess();
        }
      }
    } catch (error) {
      setFeedback({
        type: 'error',
        message: error instanceof Error ? error.message : 'Upload failed.',
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Upload Books</DialogTitle>
        </DialogHeader>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`flex min-h-[120px] cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors ${
            dragOver
              ? 'border-primary bg-primary/5'
              : 'border-muted-foreground/25'
          }`}
          onClick={() => document.getElementById('book-file-input')?.click()}
        >
          <Upload className="mb-2 h-8 w-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Drag & drop .zip files here, or click to browse
          </p>
          <p className="text-xs text-muted-foreground mt-1">Up to 50 files</p>
          <input
            id="book-file-input"
            type="file"
            accept=".zip"
            multiple
            onChange={handleFileInput}
            className="hidden"
          />
        </div>

        {files.length > 0 && (
          <div className="space-y-2">
            <Label>{files.length} file(s) selected</Label>
            <div className="flex flex-wrap gap-1.5">
              {files.map((f, i) => (
                <Badge key={i} variant="secondary" className="gap-1">
                  {f.name}
                  <button
                    onClick={() => removeFile(i)}
                    className="ml-1 hover:text-destructive"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center space-x-2">
          <Checkbox
            id="override"
            checked={overrideExisting}
            onCheckedChange={(c) => setOverrideExisting(c === true)}
          />
          <Label htmlFor="override" className="text-sm font-normal">
            Delete existing books and replace with new uploads
          </Label>
        </div>

        {uploading && <Progress value={undefined} className="animate-pulse" />}

        {uploadResults.length > 0 && (
          <div className="max-h-40 space-y-1 overflow-auto rounded-md border p-2">
            {uploadResults.map((r, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                {r.success ? (
                  <CheckCircle className="h-4 w-4 text-green-600 shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 text-destructive shrink-0" />
                )}
                <span className="truncate">
                  {r.filename}
                  {r.publisher && ` — ${r.publisher}`}
                  {r.book_name && ` / ${r.book_name}`}
                </span>
                {r.error && (
                  <span className="text-xs text-destructive truncate">
                    {r.error}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}

        {feedback && (
          <Alert
            variant={feedback.type === 'error' ? 'destructive' : 'default'}
          >
            <AlertDescription>{feedback.message}</AlertDescription>
          </Alert>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={uploading}>
            Cancel
          </Button>
          <Button onClick={handleUpload} disabled={!files.length || uploading}>
            {uploading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            Upload {files.length > 1 ? `${files.length} Files` : ''}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default BookUploadDialog;
