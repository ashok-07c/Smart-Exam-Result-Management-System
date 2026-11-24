import { useState } from 'react';
import { toast } from 'react-hot-toast';
import { Download, Eye, Ticket } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { ErrorPanel } from '@/components/common/ErrorPanel';
import { Badge, Button, Card, CardContent, DataTable, Modal, type DataTableColumn } from '@/components/ui';
import { api, ApiError } from '@/lib/api';
import { useApiQuery } from '@/lib/hooks';
import type { DataRecord, HallTicket } from '@/lib/types';
import { formatDate, formatTime } from '@/lib/utils';

export function StudentHallTickets() {
  const [preview, setPreview] = useState<HallTicket | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const tickets = useApiQuery<HallTicket[]>('student-tickets', '/students/me/hall-tickets');
  const previewQuery = useApiQuery<DataRecord>(
    'hall-ticket-preview',
    preview ? `/students/me/hall-tickets/${preview.id}` : '',
    undefined,
    { enabled: Boolean(preview) },
  );

  const download = async (ticket: HallTicket) => {
    setBusy(ticket.id);
    try {
      await api.download(`/students/me/hall-tickets/${ticket.id}/download`, `hall-ticket-${ticket.ticket_number}.pdf`);
      toast.success('Hall ticket downloaded');
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Download failed');
    } finally {
      setBusy(null);
    }
  };

  const columns: DataTableColumn<HallTicket>[] = [
    { key: 'number', header: 'Ticket number', render: (row) => <span className="font-mono font-medium">{row.ticket_number}</span> },
    { key: 'exam', header: 'Examination', render: (row) => row.examination_name ?? '—' },
    { key: 'type', header: 'Type', render: (row) => <Badge variant="outline">{row.exam_type ?? '—'}</Badge> },
    { key: 'issued', header: 'Issued', render: (row) => formatDate(row.issued_at) },
    {
      key: 'actions',
      header: 'Actions',
      render: (row) => (
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => setPreview(row)}><Eye className="h-4 w-4" /> Preview</Button>
          <Button variant="outline" size="sm" loading={busy === row.id} onClick={() => download(row)}>
            <Download className="h-4 w-4" /> PDF
          </Button>
        </div>
      ),
    },
  ];

  return (
    <>
      <PageHeader eyebrow="Student portal" title="Hall Tickets" description="Download or preview hall tickets issued for your registered examinations." />
      <ErrorPanel error={tickets.error} onRetry={() => void tickets.refetch()} />
      <Card className="mb-5 border-primary/20 bg-primary/5 p-4 text-sm">
        <div className="flex items-start gap-3">
          <Ticket className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
          <p>Carry a printed hall ticket and a valid photo ID to every examination. Regenerated tickets invalidate older copies.</p>
        </div>
      </Card>
      <DataTable columns={columns} data={tickets.data ?? []} rowKey={(row) => row.id} empty="No hall tickets have been issued yet." />

      <Modal open={Boolean(preview)} onClose={() => setPreview(null)} title="Hall ticket preview" description={preview?.ticket_number} size="lg">
        {previewQuery.isLoading ? <div className="h-40 animate-pulse rounded bg-muted" /> : (
          <div className="space-y-5">
            <div className="rounded-lg border border-border bg-muted/30 p-4 text-center">
              <p className="text-xs uppercase tracking-widest text-muted-foreground">Smart Examination System</p>
              <p className="mt-1 text-xl font-bold">{previewQuery.data?.examination ?? preview?.examination_name}</p>
              <p className="font-mono text-sm">{preview?.ticket_number}</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                ['Student', previewQuery.data?.student_name],
                ['Roll number', previewQuery.data?.roll_number],
                ['Branch', previewQuery.data?.branch],
                ['Semester', previewQuery.data?.semester],
                ['Academic year', previewQuery.data?.academic_year],
                ['Issue date', previewQuery.data?.issue_date],
              ].map(([label, value]) => (
                <CardContent key={String(label)} className="rounded-lg border border-border p-3">
                  <p className="text-xs text-muted-foreground">{label}</p>
                  <p className="font-medium">{String(value ?? '—')}</p>
                </CardContent>
              ))}
            </div>
            <div>
              <p className="mb-2 text-sm font-semibold">Registered subjects</p>
              <div className="overflow-x-auto rounded-lg border border-border">
                <table className="w-full text-left text-sm">
                  <thead className="bg-muted/60 text-xs uppercase text-muted-foreground">
                    <tr><th className="p-2">Code</th><th className="p-2">Subject</th><th className="p-2">Date</th><th className="p-2">Time</th><th className="p-2">Venue</th></tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {(previewQuery.data?.subjects as DataRecord[] | undefined)?.map((item) => (
                      <tr key={String(item.code)}>
                        <td className="p-2 font-medium">{String(item.code)}</td>
                        <td className="p-2">{String(item.name)}</td>
                        <td className="p-2">{formatDate(String(item.date))}</td>
                        <td className="p-2">{formatTime(String(item.start_time))} – {formatTime(String(item.end_time))}</td>
                        <td className="p-2">{String(item.venue)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            {preview && <div className="flex justify-end"><Button onClick={() => download(preview)} loading={busy === preview.id}><Download className="h-4 w-4" /> Download PDF</Button></div>}
          </div>
        )}
      </Modal>
    </>
  );
}
