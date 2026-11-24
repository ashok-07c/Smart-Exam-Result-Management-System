import { Repeat2 } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { StatCard } from '@/components/common/StatCard';
import { ErrorPanel } from '@/components/common/ErrorPanel';
import { Alert, Badge, CardContent, DataTable, type DataTableColumn } from '@/components/ui';
import { useApiQuery } from '@/lib/hooks';
import type { Backlog } from '@/lib/types';

export function StudentBacklogs() {
  const backlogs = useApiQuery<Backlog[]>('student-backlogs', '/students/me/backlogs');
  const active = (backlogs.data ?? []).filter((item) => !item.is_cleared);

  const columns: DataTableColumn<Backlog>[] = [
    { key: 'subject', header: 'Subject', render: (row) => <><span className="font-medium">{row.subject_code}</span><span className="block text-xs text-muted-foreground">{row.subject_name}</span></> },
    { key: 'sem', header: 'Semester', render: (row) => `Sem ${row.semester_number}` },
    { key: 'year', header: 'Academic year', render: (row) => row.academic_year_name },
    { key: 'credits', header: 'Credits', render: (row) => row.credits },
    { key: 'attempts', header: 'Attempts', render: (row) => row.attempts },
    { key: 'status', header: 'Status', render: (row) => <Badge variant={row.is_cleared ? 'success' : 'destructive'}>{row.is_cleared ? 'CLEARED' : 'ACTIVE'}</Badge> },
    { key: 'supplementary', header: 'Supplementary', render: (row) => row.supplementary_exam_id ? 'Available' : 'Not scheduled' },
  ];

  return (
    <>
      <PageHeader eyebrow="Student portal" title="Backlog Subjects" description="Subjects that must be cleared through a supplementary examination." />
      <ErrorPanel error={backlogs.error} onRetry={() => void backlogs.refetch()} />
      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <StatCard label="Active backlogs" value={active.length} icon={Repeat2} tone="destructive" />
        <StatCard label="Cleared" value={(backlogs.data ?? []).length - active.length} icon={Repeat2} tone="success" />
        <StatCard label="Credits at risk" value={active.reduce((sum, item) => sum + item.credits, 0)} icon={Repeat2} tone="warning" />
      </div>
      {active.length > 0 && (
        <Alert variant="warning" title="Registration requirement">
          Supplementary registration requires an active backlog. Eligibility is validated by the server when you register.
        </Alert>
      )}
      <div className="mt-5">
        <DataTable columns={columns} data={backlogs.data ?? []} rowKey={(row) => row.id} empty="You have no recorded backlogs." />
      </div>
      <CardContent className="px-0 text-xs text-muted-foreground">
        Backlog status is updated only after an Examination Admin processes results or a supplementary attempt.
      </CardContent>
    </>
  );
}
