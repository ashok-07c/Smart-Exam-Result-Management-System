import { useState } from 'react';
import { toast } from 'react-hot-toast';
import { CalendarDays, Download } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { ErrorPanel } from '@/components/common/ErrorPanel';
import { Button, Card, CardContent, DataTable, Field, Input, Select, type DataTableColumn } from '@/components/ui';
import { api, ApiError } from '@/lib/api';
import { useApiQuery } from '@/lib/hooks';
import type { ScheduleItem } from '@/lib/types';
import { formatDate, formatTime } from '@/lib/utils';

export function StudentTimetable() {
  const [examType, setExamType] = useState('');
  const [subjectCode, setSubjectCode] = useState('');
  const [downloading, setDownloading] = useState(false);

  const timetable = useApiQuery<ScheduleItem[]>('student-timetable', '/students/me/timetable', {
    exam_type: examType || undefined,
    subject_code: subjectCode || undefined,
  });

  const download = async () => {
    setDownloading(true);
    try {
      await api.download('/students/me/timetable/download', 'examination-timetable.pdf');
      toast.success('Timetable downloaded');
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Download failed');
    } finally {
      setDownloading(false);
    }
  };

  const columns: DataTableColumn<ScheduleItem>[] = [
    { key: 'date', header: 'Date', render: (row) => <span className="font-medium">{formatDate(row.exam_date)}</span> },
    { key: 'time', header: 'Time', render: (row) => `${formatTime(row.start_time)} – ${formatTime(row.end_time)}` },
    { key: 'session', header: 'Session', render: (row) => row.session ?? '—' },
    { key: 'subject', header: 'Subject', render: (row) => <><span className="font-medium">{row.subject_code}</span><span className="block text-xs text-muted-foreground">{row.subject_name}</span></> },
    { key: 'venue', header: 'Venue', render: (row) => row.venue ?? '—' },
    { key: 'exam', header: 'Examination', render: (row) => row.examination_name ?? '—' },
  ];

  return (
    <>
      <PageHeader
        eyebrow="Student portal"
        title="Examination Timetable"
        description="Only published exam entries for your current semester and branch are visible here."
        actions={<Button variant="outline" onClick={download} loading={downloading}><Download className="h-4 w-4" /> Download PDF</Button>}
      />
      <ErrorPanel error={timetable.error} onRetry={() => void timetable.refetch()} />
      <Card className="mb-5">
        <CardContent className="grid gap-4 p-4 sm:grid-cols-2">
          <Field label="Examination type">
            <Select value={examType} onChange={(event) => setExamType(event.target.value)}>
              <option value="">All types</option>
              <option value="REGULAR">Regular</option>
              <option value="SUPPLEMENTARY">Supplementary</option>
            </Select>
          </Field>
          <Field label="Subject code">
            <Input value={subjectCode} onChange={(event) => setSubjectCode(event.target.value)} placeholder="e.g. CS301" />
          </Field>
        </CardContent>
      </Card>
      <div className="mb-4 flex items-center gap-2 text-sm text-muted-foreground">
        <CalendarDays className="h-4 w-4" /> {timetable.data?.length ?? 0} published schedule entries
      </div>
      {timetable.isLoading ? <div className="h-48 animate-pulse rounded-lg bg-muted" /> : (
        <DataTable columns={columns} data={timetable.data ?? []} rowKey={(row) => row.id} empty="No published timetable entries match your filters." />
      )}
    </>
  );
}
