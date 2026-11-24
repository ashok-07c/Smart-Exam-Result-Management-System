import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { ClipboardList, Download, FileCheck2 } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { ErrorPanel } from '@/components/common/ErrorPanel';
import {
  Alert, Badge, Button, Card, CardContent, Checkbox, Input,
  DataTable, LoadingState, Modal, StatusBadge, type DataTableColumn,
} from '@/components/ui';
import { api, ApiError } from '@/lib/api';
import { useApiQuery } from '@/lib/hooks';
import type { EligibleSubject, Examination, Registration } from '@/lib/types';
import { formatDate } from '@/lib/utils';

export function StudentExaminations() {
  const queryClient = useQueryClient();
  const exams = useApiQuery<Examination[]>('student-exams', '/students/me/examinations');
  const registrations = useApiQuery<Registration[]>('student-registrations', '/students/me/registrations');
  const [activeExam, setActiveExam] = useState<Examination | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [receipt, setReceipt] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const subjects = useApiQuery<EligibleSubject[]>(
    'eligible-subjects',
    activeExam ? `/students/me/examinations/${activeExam.id}/subjects` : '',
    undefined,
    { enabled: Boolean(activeExam) },
  );

  const refresh = () => {
    void exams.refetch();
    void registrations.refetch();
    void queryClient.invalidateQueries({ queryKey: ['admin-registrations'] });
  };

  const openRegister = (exam: Examination) => {
    setActiveExam(exam);
    setSelected([]);
    setReceipt(null);
  };

  const submit = async () => {
    if (!activeExam || selected.length === 0) {
      toast.error('Select at least one subject');
      return;
    }
    if (!receipt) {
      toast.error('Upload the SBI Collect Fee Payment Receipt');
      return;
    }
    const form = new FormData();
    form.append('examination_id', activeExam.id);
    selected.forEach((id) => form.append('subject_ids', id));
    form.append('fee_receipt', receipt);
    setSubmitting(true);
    try {
      const response = await api.post('/students/me/registrations', form);
      toast.success(response.message);
      setActiveExam(null);
      refresh();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Registration failed');
    } finally {
      setSubmitting(false);
    }
  };

  const downloadReceipt = async (row: Registration) => {
    try {
      await api.download(`/students/me/registrations/${row.id}/receipt`, row.fee_receipt_filename ?? 'fee-receipt');
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not download receipt');
    }
  };

  const registrationColumns: DataTableColumn<Registration>[] = [
    { key: 'exam', header: 'Examination', render: (row) => <span className="font-medium">{row.examination_name}</span> },
    { key: 'type', header: 'Type', render: (row) => <StatusBadge value={row.exam_type} /> },
    { key: 'subjects', header: 'Subjects', render: (row) => row.subjects.map((s) => s.subject_code).join(', ') || '—' },
    { key: 'submitted', header: 'Submitted', render: (row) => formatDate(row.submitted_at) },
    { key: 'status', header: 'Status', render: (row) => <StatusBadge value={row.status} /> },
    {
      key: 'receipt',
      header: 'Fee receipt',
      render: (row) => row.has_fee_receipt ? (
        <Button variant="ghost" size="sm" onClick={() => void downloadReceipt(row)}>
          <Download className="h-3.5 w-3.5" /> Receipt
        </Button>
      ) : <span className="text-xs text-destructive">Missing</span>,
    },
  ];

  if (exams.isLoading || registrations.isLoading) return <LoadingState label="Loading examinations…" />;

  return (
    <>
      <PageHeader
        eyebrow="Student portal"
        title="Examinations & Registration"
        description="Eligibility, deadlines and subject selection are enforced by the server."
      />
      <ErrorPanel error={exams.error ?? registrations.error} onRetry={refresh} />

      <div className="grid gap-6 xl:grid-cols-2">
        <section>
          <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold"><ClipboardList className="h-5 w-5 text-primary" /> Available examinations</h2>
          <div className="space-y-3">
            {(exams.data ?? []).map((exam) => (
              <Card key={exam.id}>
                <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium">{exam.name}</p>
                      <StatusBadge value={exam.exam_type} />
                      {exam.registered && <Badge variant="success">Registered</Badge>}
                    </div>
                    <p className="mt-1.5 text-sm text-muted-foreground">
                      Registration: {formatDate(exam.registration_start)} – {formatDate(exam.registration_deadline)}
                    </p>
                    <p className={`mt-1 text-xs ${exam.eligible ? 'text-success' : 'text-destructive'}`}>
                      {exam.eligibility_reason}
                    </p>
                  </div>
                  <Button
                    size="sm"
                    disabled={!exam.eligible || exam.registered}
                    onClick={() => openRegister(exam)}
                  >
                    {exam.registered ? 'Registered' : 'Register'}
                  </Button>
                </CardContent>
              </Card>
            ))}
            {!exams.data?.length && <Alert>No examinations have been configured.</Alert>}
          </div>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold">My registrations</h2>
          <DataTable columns={registrationColumns} data={registrations.data ?? []} rowKey={(row) => row.id} empty="You have not registered for any examination yet." />
        </section>
      </div>

      <Modal
        open={Boolean(activeExam)}
        onClose={() => setActiveExam(null)}
        title="Select examination subjects"
        description={activeExam?.name}
        size="lg"
      >
        {subjects.isLoading ? <LoadingState label="Loading eligible subjects…" /> : (
          <>
            <ErrorPanel error={subjects.error} onRetry={() => void subjects.refetch()} />
            <div className="space-y-2">
              {(subjects.data ?? []).map((subject) => (
                <label
                  key={subject.subject_id}
                  className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors ${
                    selected.includes(subject.subject_id) ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/40'
                  }`}
                >
                  <Checkbox
                    className="mt-1"
                    checked={selected.includes(subject.subject_id)}
                    disabled={subject.already_registered}
                    onChange={(event) => setSelected((current) =>
                      event.target.checked
                        ? [...current, subject.subject_id]
                        : current.filter((id) => id !== subject.subject_id),
                    )}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block font-medium">{subject.subject_code} — {subject.subject_name}</span>
                    <span className="mt-0.5 block text-xs text-muted-foreground">
                      {subject.credits} credits · Internal {subject.internal_max_marks} · External {subject.external_max_marks}
                      {subject.already_registered ? ' · Already registered' : ''}
                    </span>
                  </span>
                </label>
              ))}
              {!subjects.data?.length && <Alert variant="warning">No eligible subjects are available for this examination.</Alert>}
            </div>
            <div className="mt-5 rounded-lg border border-dashed border-border bg-muted/30 p-4">
              <p className="mb-2 flex items-center gap-2 text-sm font-semibold"><FileCheck2 className="h-4 w-4 text-primary" /> SBI Collect Fee Payment Receipt <span className="text-destructive">*</span></p>
              <Input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
                onChange={(event) => setReceipt(event.target.files?.[0] ?? null)}
                aria-label="SBI Collect Fee Payment Receipt"
              />
              <p className="mt-2 text-xs text-muted-foreground">Mandatory · PDF, JPG or PNG · maximum 5 MB. Stored privately and linked to this registration.</p>
              {receipt && <p className="mt-2 text-xs font-medium text-success">Selected: {receipt.name}</p>}
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setActiveExam(null)}>Cancel</Button>
              <Button onClick={submit} loading={submitting} disabled={selected.length === 0 || !receipt}>Submit registration</Button>
            </div>
          </>
        )}
      </Modal>
    </>
  );
}
