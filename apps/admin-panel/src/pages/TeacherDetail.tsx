import { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Loader2,
  Pencil,
  FileText,
  Image,
  Music,
  Video,
  File,
} from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from 'components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from 'components/ui/table';
import { Input } from 'components/ui/input';
import { Button } from 'components/ui/button';
import { Badge } from 'components/ui/badge';
import { Progress } from 'components/ui/progress';
import { Alert, AlertDescription } from 'components/ui/alert';
import TeacherFormDialog from 'components/TeacherFormDialog';
import { useAuthStore } from 'stores/auth';
import {
  fetchTeacher,
  fetchTeacherStorageStats,
  fetchTeacherMaterials,
  formatBytes,
  getAIStatusLabel,
  type Teacher,
  type Material,
  type StorageStats,
} from 'lib/teacherManagement';

type SortField =
  | 'material_name'
  | 'file_type'
  | 'size'
  | 'ai_processing_status'
  | 'created_at';
type SortDir = 'asc' | 'desc';

const fileIcon = (t: string) => {
  if (/pdf/i.test(t)) return <FileText className="h-4 w-4" />;
  if (/doc|docx|ppt/i.test(t)) return <FileText className="h-4 w-4" />;
  if (/image|jpg|jpeg|png|gif/i.test(t)) return <Image className="h-4 w-4" />;
  if (/audio|mp3|wav/i.test(t)) return <Music className="h-4 w-4" />;
  if (/video|mp4/i.test(t)) return <Video className="h-4 w-4" />;
  return <File className="h-4 w-4" />;
};

const aiStatusVariant = (s: string) => {
  if (s === 'completed') return 'success' as const;
  if (s === 'processing' || s === 'queued') return 'default' as const;
  if (s === 'failed') return 'destructive' as const;
  return 'secondary' as const;
};

const fmtDate = (s: string) =>
  new Date(s).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });

const TeacherDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { token, tokenType } = useAuthStore();
  const tt = tokenType ?? 'Bearer';

  const [teacher, setTeacher] = useState<Teacher | null>(null);
  const [stats, setStats] = useState<StorageStats | null>(null);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<{ f: SortField; d: SortDir }>({
    f: 'created_at',
    d: 'desc',
  });

  const load = async () => {
    if (!token || !id) return;
    setLoading(true);
    setError('');
    try {
      const [t, s, m] = await Promise.all([
        fetchTeacher(Number(id), token, tt),
        fetchTeacherStorageStats(Number(id), token, tt).catch(() => null),
        fetchTeacherMaterials(Number(id), token, tt).catch(() => []),
      ]);
      setTeacher(t);
      setStats(s);
      setMaterials(m);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [token, id]);

  const filtered = useMemo(() => {
    let d = materials;
    if (search) {
      const q = search.toLowerCase();
      d = d.filter(
        (m) =>
          m.material_name.toLowerCase().includes(q) ||
          m.display_name?.toLowerCase().includes(q) ||
          m.file_type.toLowerCase().includes(q)
      );
    }
    const dir = sort.d === 'asc' ? 1 : -1;
    return [...d].sort((a, b) => {
      if (sort.f === 'size') return (a.size - b.size) * dir;
      if (sort.f === 'created_at')
        return (
          (new Date(a.created_at).getTime() -
            new Date(b.created_at).getTime()) *
          dir
        );
      return (
        String(// eslint-disable-next-line @typescript-eslint/no-explicit-any
      (a as any)[sort.f] ?? '').localeCompare(
          String(// eslint-disable-next-line @typescript-eslint/no-explicit-any
      (b as any)[sort.f] ?? '')
        ) * dir
      );
    });
  }, [materials, search, sort]);

  const toggleSort = (f: SortField) =>
    setSort((c) => ({ f, d: c.f === f && c.d === 'asc' ? 'desc' : 'asc' }));

  if (loading)
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  if (!teacher)
    return (
      <Alert variant="destructive">
        <AlertDescription>{error || 'Teacher not found'}</AlertDescription>
      </Alert>
    );

  const SortHead = ({ field, label }: { field: SortField; label: string }) => (
    <TableHead
      className="cursor-pointer select-none"
      onClick={() => toggleSort(field)}
    >
      {label} {sort.f === field && (sort.d === 'asc' ? '↑' : '↓')}
    </TableHead>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate('/teachers')}
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-2xl font-semibold flex-1">
          {teacher.display_name || teacher.teacher_id}
        </h1>
        <Button variant="outline" onClick={() => setFormOpen(true)}>
          <Pencil className="h-4 w-4" /> Edit
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Teacher Info</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div>
              <span className="text-muted-foreground">ID:</span>{' '}
              {teacher.teacher_id}
            </div>
            <div>
              <span className="text-muted-foreground">Name:</span>{' '}
              {teacher.display_name || '—'}
            </div>
            <div>
              <span className="text-muted-foreground">Email:</span>{' '}
              {teacher.email || '—'}
            </div>
            <div>
              <span className="text-muted-foreground">Status:</span>{' '}
              <Badge
                variant={teacher.status === 'active' ? 'success' : 'secondary'}
              >
                {teacher.status}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {stats && (
          <Card>
            <CardHeader>
              <CardTitle>Storage Insights</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="text-lg font-semibold text-primary">
                {formatBytes(stats.total_size)}
              </div>
              <div className="text-xs text-muted-foreground">
                {stats.total_count} files total
              </div>
              {Object.entries(stats.by_type).map(([type, info]) => (
                <div
                  key={type}
                  className="flex items-center justify-between text-sm"
                >
                  <div className="flex items-center gap-2">
                    {fileIcon(type)} <span>{type.toUpperCase()}</span>
                  </div>
                  <span>
                    {info.count} files ({formatBytes(info.size)})
                  </span>
                </div>
              ))}
              <div className="pt-2 border-t space-y-1">
                <div className="flex justify-between text-xs">
                  <span>AI Processable</span>
                  <span>{stats.ai_processable_count}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span>AI Processed</span>
                  <span>{stats.ai_processed_count}</span>
                </div>
                {stats.ai_processable_count > 0 && (
                  <Progress
                    value={
                      (stats.ai_processed_count / stats.ai_processable_count) *
                      100
                    }
                  />
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Materials ({materials.length})</CardTitle>
          <Input
            placeholder="Search materials..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-xs"
          />
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8" />
                <SortHead field="material_name" label="Name" />
                <SortHead field="file_type" label="Type" />
                <SortHead field="size" label="Size" />
                <SortHead field="created_at" label="Uploaded" />
                <SortHead field="ai_processing_status" label="AI Status" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {!filtered.length ? (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="text-center py-8 text-muted-foreground"
                  >
                    No materials found
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell>{fileIcon(m.file_type)}</TableCell>
                    <TableCell className="font-medium">
                      {m.display_name || m.material_name}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {m.file_type.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell>{formatBytes(m.size)}</TableCell>
                    <TableCell>{fmtDate(m.created_at)}</TableCell>
                    <TableCell>
                      <Badge variant={aiStatusVariant(m.ai_processing_status)}>
                        {getAIStatusLabel(m.ai_processing_status)}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <TeacherFormDialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSuccess={() => {
          setFormOpen(false);
          load();
        }}
        teacher={teacher}
        token={token}
        tokenType={tt}
      />
    </div>
  );
};

export default TeacherDetailPage;
