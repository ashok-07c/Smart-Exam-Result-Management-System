import { Link } from 'react-router-dom';
import { ClipboardCheck } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { ErrorPanel } from '@/components/common/ErrorPanel';
import { Badge, Button, Card, CardContent, DataTable, StatusBadge, type DataTableColumn } from '@/components/ui';
import { useApiQuery } from '@/lib/hooks';
import type { InternalMark } from '@/lib/types';
import { formatDate } from '@/lib/utils';

export function StudentInternalMarks() {
  const marks = useApiQuery<InternalMark[]>('student-marks', '/students/me/internal-marks');

  const columns: DataTableColumn<InternalMark>[] = [
    { key: 'subject', header: 'Subject', render: (row) => <><span className="font-medium">{row.subject_code}</span><span className="block text-xs text-muted-foreground">{row.subject_name}</span></> },
    {
      key: 'components',
      header: 'MID-1 / MID-2 / Assignments',
      render: (row) => (
        <div className="flex flex-wrap gap-1">
          <Badge variant="outline" className="font-normal">MID-1: {row.mid1_marks}/25</Badge>
          <Badge variant="outline" className="font-normal">MID-2: {row.mid2_marks}/25</Badge>
          <Badge variant="outline" className="font-normal">Assignments: {row.assignments_marks}/5</Badge>
        </div>
      ),
    },
    { key: 'total', header: 'Total', render: (row) => <span className="font-semibold">{row.total_marks}/{row.max_marks}</span> },
    { key: 'status', header: 'Status', render: (row) => <StatusBadge value={row.status} /> },
    { key: 'submitted', header: 'Submitted', render: (row) => formatDate(row.submitted_at) },
  ];

  return (
    <>
      <PageHeader
        eyebrow="Student portal"
        title="Internal Marks"
        description="Faculty-entered and verified internal assessment marks. Discrepancies can be reported for review."
        actions={<Link to="/student/corrections"><Button variant="outline" size="sm"><ClipboardCheck className="h-4 w-4" /> Report an issue</Button></Link>}
      />
      <ErrorPanel error={marks.error} onRetry={() => void marks.refetch()} />
      <Card className="mb-4 border-primary/20 bg-primary/5 p-4 text-sm">
        Total internal marks are calculated by the server as (best MID × 0.8) + (other MID × 0.2) + Assignments, out of 30. Changes are only possible through a reviewed correction request.
      </Card>
      <DataTable columns={columns} data={marks.data ?? []} rowKey={(row) => row.id} empty="No internal marks have been published for your account yet." />
      <CardContent className="mt-4 px-0 text-xs text-muted-foreground">
        Records are grouped by the subject and examination configured by the Examination Admin.
      </CardContent>
    </>
  );
}
