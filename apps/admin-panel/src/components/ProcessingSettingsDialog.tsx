import { useCallback, useEffect, useState } from 'react';
import { Loader2, Save } from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from 'components/ui/dialog';
import { Card, CardContent, CardHeader, CardTitle } from 'components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from 'components/ui/select';
import { Input } from 'components/ui/input';
import { Label } from 'components/ui/label';
import { Switch } from 'components/ui/switch';
import { Slider } from 'components/ui/slider';
import { Button } from 'components/ui/button';
import { Alert, AlertDescription } from 'components/ui/alert';
import {
  getProcessingSettings,
  updateProcessingSettings,
} from 'lib/processing';

const AUDIO_LANGS = ['en', 'tr', 'de', 'fr', 'es'];

interface ProcessingSettingsDialogProps {
  open: boolean;
  onClose: () => void;
  token: string | null;
  tokenType: string;
}

export function ProcessingSettingsDialog({
  open,
  onClose,
  token,
  tokenType,
}: ProcessingSettingsDialogProps) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [autoProcess, setAutoProcess] = useState(false);
  const [skipExisting, setSkipExisting] = useState(false);
  const [llmPrimary, setLlmPrimary] = useState('');
  const [llmFallback, setLlmFallback] = useState('');
  const [ttsPrimary, setTtsPrimary] = useState('');
  const [ttsFallback, setTtsFallback] = useState('');
  const [queueConcurrency, setQueueConcurrency] = useState(2);
  const [vocabMaxWords, setVocabMaxWords] = useState(50);
  const [audioLangs, setAudioLangs] = useState<string[]>([]);
  const [audioConcurrency, setAudioConcurrency] = useState(3);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const s = await getProcessingSettings(token, tokenType);
      setAutoProcess(s.ai_auto_process_on_upload);
      setSkipExisting(s.ai_auto_process_skip_existing);
      setLlmPrimary(s.llm_primary_provider);
      setLlmFallback(s.llm_fallback_provider);
      setTtsPrimary(s.tts_primary_provider);
      setTtsFallback(s.tts_fallback_provider);
      setQueueConcurrency(s.queue_max_concurrency);
      setVocabMaxWords(s.vocabulary_max_words_per_module);
      setAudioLangs(s.audio_generation_languages.split(',').filter(Boolean));
      setAudioConcurrency(s.audio_generation_concurrency);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  }, [token, tokenType]);

  useEffect(() => {
    if (open) load();
  }, [open, load]);

  const handleSave = async () => {
    if (!token) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await updateProcessingSettings(
        {
          ai_auto_process_on_upload: autoProcess,
          ai_auto_process_skip_existing: skipExisting,
          llm_primary_provider: llmPrimary,
          llm_fallback_provider: llmFallback,
          tts_primary_provider: ttsPrimary,
          tts_fallback_provider: ttsFallback,
          queue_max_concurrency: queueConcurrency,
          vocabulary_max_words_per_module: vocabMaxWords,
          audio_generation_languages: audioLangs.join(','),
          audio_generation_concurrency: audioConcurrency,
        },
        token,
        tokenType
      );
      setSuccess('Settings saved!');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const toggleLang = (l: string) =>
    setAudioLangs((p) =>
      p.includes(l) ? p.filter((x) => x !== l) : [...p, l]
    );

  return (
    <Dialog open={open} onOpenChange={(o) => !saving && !o && onClose()}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Processing Settings</DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Card>
              <CardHeader className="p-4 pb-2">
                <CardTitle className="text-sm">Auto-Processing</CardTitle>
              </CardHeader>
              <CardContent className="p-4 pt-0 space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="text-xs">Process on upload</Label>
                  <Switch
                    checked={autoProcess}
                    onCheckedChange={setAutoProcess}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label className="text-xs">Skip already processed</Label>
                  <Switch
                    checked={skipExisting}
                    onCheckedChange={setSkipExisting}
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="p-4 pb-2">
                <CardTitle className="text-sm">Queue</CardTitle>
              </CardHeader>
              <CardContent className="p-4 pt-0 space-y-2">
                <Label className="text-xs">Max Concurrency</Label>
                <Input
                  type="number"
                  min={1}
                  max={10}
                  value={queueConcurrency}
                  onChange={(e) => setQueueConcurrency(Number(e.target.value))}
                  className="h-8"
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="p-4 pb-2">
                <CardTitle className="text-sm">LLM Providers</CardTitle>
              </CardHeader>
              <CardContent className="p-4 pt-0 space-y-3">
                <div className="space-y-1">
                  <Label className="text-xs">Primary</Label>
                  <Select value={llmPrimary} onValueChange={setLlmPrimary}>
                    <SelectTrigger className="h-8">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="deepseek">DeepSeek</SelectItem>
                      <SelectItem value="gemini">Gemini</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Fallback</Label>
                  <Select value={llmFallback} onValueChange={setLlmFallback}>
                    <SelectTrigger className="h-8">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="deepseek">DeepSeek</SelectItem>
                      <SelectItem value="gemini">Gemini</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="p-4 pb-2">
                <CardTitle className="text-sm">TTS Providers</CardTitle>
              </CardHeader>
              <CardContent className="p-4 pt-0 space-y-3">
                <div className="space-y-1">
                  <Label className="text-xs">Primary</Label>
                  <Select value={ttsPrimary} onValueChange={setTtsPrimary}>
                    <SelectTrigger className="h-8">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="edge">Edge TTS</SelectItem>
                      <SelectItem value="azure">Azure TTS</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Fallback</Label>
                  <Select value={ttsFallback} onValueChange={setTtsFallback}>
                    <SelectTrigger className="h-8">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="edge">Edge TTS</SelectItem>
                      <SelectItem value="azure">Azure TTS</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="p-4 pb-2">
                <CardTitle className="text-sm">Vocabulary</CardTitle>
              </CardHeader>
              <CardContent className="p-4 pt-0 space-y-3">
                <Label className="text-xs">
                  Max Words per Module: {vocabMaxWords}
                </Label>
                <Slider
                  value={[vocabMaxWords]}
                  onValueChange={(v) => setVocabMaxWords(v[0])}
                  min={10}
                  max={100}
                  step={5}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="p-4 pb-2">
                <CardTitle className="text-sm">Audio Generation</CardTitle>
              </CardHeader>
              <CardContent className="p-4 pt-0 space-y-3">
                <div className="space-y-1">
                  <Label className="text-xs">Languages</Label>
                  <div className="flex flex-wrap gap-1.5">
                    {AUDIO_LANGS.map((l) => (
                      <Button
                        key={l}
                        type="button"
                        variant={audioLangs.includes(l) ? 'default' : 'outline'}
                        size="sm"
                        className="h-7 text-xs"
                        onClick={() => toggleLang(l)}
                      >
                        {l.toUpperCase()}
                      </Button>
                    ))}
                  </div>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Concurrency</Label>
                  <Input
                    type="number"
                    min={1}
                    max={20}
                    value={audioConcurrency}
                    onChange={(e) =>
                      setAudioConcurrency(Number(e.target.value))
                    }
                    className="h-8"
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        )}

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

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>
            Close
          </Button>
          <Button onClick={handleSave} disabled={saving || loading}>
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}{' '}
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default ProcessingSettingsDialog;
