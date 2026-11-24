import { useState } from 'react';
import { toast } from 'react-hot-toast';
import { Award, Download, FileText } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { ErrorPanel } from '@/components/common/ErrorPanel';
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle, DataTable, StatusBadge, type DataTableColumn } from '@/components/ui';
import { api, ApiError } from '@/lib/api';
import { useApiQuery } from '@/lib/hooks';
import type { SemesterResult, SubjectResult } from '@/lib/types';
import { formatDate } from '@/lib/utils';

export function StudentResults() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const results = useApiQuery<SemesterResult[]>('student-results', '/students/me/results');
  const selected = (results.data ?? []).find((result) => result.id === selectedId) ?? results.data?.[results.data.length - 1];

  const downloadCertificate = async () => {
    if (!selected) return;
    setBusy(true);
    try {
      await api.download(`/students/me/certificates/${selected.id}/download`, `grade-certificate-sem-${selected.semester_number}.pdf`);
      toast.success('Certificate downloaded');
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Download failed');
    } finally {
      setBusy(false);
    }
  };

  const resultColumns: DataTableColumn<SemesterResult>[] = [
    { key: 'semester', header: 'Semester', render: (row) => <span className="font-medium">Semester {row.semester_number}</span> },
    { key: 'year', header: 'Academic year', render: (row) => row.academic_year_name },
    { key: 'sgpa', header: 'SGPA', render: (row) => row.sgpa ?? '—' },
    { key: 'cgpa', header: 'CGPA', render: (row) => row.cgpa ?? '—' },
    { key: 'credits', header: 'Credits', render: (row) => `${row.earned_credits}/${row.total_credits}` },
    { key: 'status', header: 'Status', render: (row) => <StatusBadge value={row.status} /> },
    {
      key: 'action',
      header: '',
      render: (row) => <Button variant={selected?.id === row.id ? 'default' : 'outline'} size="sm" onClick={() => setSelectedId(row.id)}>View</Button>,
    },
  ];

  const subjectColumns: DataTableColumn<SubjectResult>[] = [
    { key: 'code', header: 'Code', render: (row) => <span className="font-medium">{row.subject_code}</span> },
    { key: 'name', header: 'Subject', render: (row) => row.subject_name },
    { key: 'credits', header: 'Credits', render: (row) => row.credits },
    { key: 'internal', header: 'Internal', render: (row) => `${row.internal_marks}` },
    { key: 'external', header: 'External', render: (row) => `${row.external_marks}` },
    { key: 'total', header: 'Total', render: (row) => <span className="font-semibold">{row.total_marks}/{row.max_marks}</span> },
    { key: 'grade', header: 'Grade', render: (row) => <Badge variant="outline">{row.grade}</Badge> },
    { key: 'result', header: 'Result', render: (row) => <StatusBadge value={row.result_status} /> },
  ];

  return (
    <>
      <PageHeader
        eyebrow="Student portal"
        title="Published Results"
        description="Only results approved and published by the Examination Admin are visible."
      />
      <ErrorPanel error={results.error} onRetry={() => void results.refetch()} />
      <Alert variant="info" title="Central grading">
        Grades S / A / B / C / D / E / Fail are calculated by the server from the percentage of maximum marks. A result below 40% is Fail; 40% and above passes. The grade shown here and on your certificate is authoritative.
      </Alert>
      <div className="h-4" />
      <DataTable columns={resultColumns} data={results.data ?? []} rowKey={(row) => row.id} empty="No results have been published yet." />

      {selected && (
        <Card className="mt-6">
          <CardHeader className="flex flex-col gap-3 space-y-0 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="flex items-center gap-2"><Award className="h-5 w-5 text-primary" /> Semester {selected.semester_number} result</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">Published {formatDate(selected.published_at)} · {selected.subject_results.length} subjects</p>
            </div>
            <Button onClick={downloadCertificate} loading={busy}><Download className="h-4 w-4" /> Download certificate</Button>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-4">
            <div className="rounded-lg bg-muted/50 p-3"><p className="text-xs text-muted-foreground">SGPA</p><p className="text-xl font-bold">{selected.sgpa ?? '—'}</p></div>
            <div className="rounded-lg bg-muted/50 p-3"><p className="text-xs text-muted-foreground">CGPA</p><p className="text-xl font-bold">{selected.cgpa ?? '—'}</p></div>
            <div className="rounded-lg bg-muted/50 p-3"><p className="text-xs text-muted-foreground">Credits earned</p><p className="text-xl font-bold">{selected.earned_credits}/{selected.total_credits}</p></div>
            <div className="rounded-lg bg-muted/50 p-3"><p className="text-xs text-muted-foreground">Status</p><p className="mt-1"><StatusBadge value={selected.status} /></p></div>
          </CardContent>
          <CardContent>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold"><FileText className="h-4 w-4" /> Subject-wise performance</h3>
            <DataTable columns={subjectColumns} data={selected.subject_results} rowKey={(row) => row.id} compact />
          </CardContent>
        </Card>
      )}
    </>
  );
}
