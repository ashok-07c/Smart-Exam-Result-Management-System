import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'react-hot-toast';
import { Plus, ScrollText } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { ErrorPanel } from '@/components/common/ErrorPanel';
import { Alert, Button, Card, CardContent, DataTable, Field, Modal, Select, StatusBadge, Textarea, type DataTableColumn } from '@/components/ui';
import { api, ApiError } from '@/lib/api';
import { useApiQuery } from '@/lib/hooks';
import type { RecountingRequest, SemesterResult } from '@/lib/types';
import { formatDate } from '@/lib/utils';

const schema = z.object({
  result_id: z.string().min(1, 'Select a published result'),
  subject_id: z.string().min(1, 'Select a subject'),
  reason: z.string().min(5, 'Provide a reason (at least 5 characters)'),
});
type FormValues = z.infer<typeof schema>;

export function StudentRecounting() {
  const [open, setOpen] = useState(false);
  const requests = useApiQuery<RecountingRequest[]>('student-recounting', '/students/me/recounting-requests');
  const results = useApiQuery<SemesterResult[]>('student-results', '/students/me/results');
  const {
    register, handleSubmit, reset, watch, setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });
  const selectedResultId = watch('result_id');
  const selectedResult = (results.data ?? []).find((result) => result.id === selectedResultId);
  const subjectOptions = selectedResult?.subject_results ?? [];

  const submit = async (values: FormValues) => {
    const result = (results.data ?? []).find((item) => item.id === values.result_id);
    if (!result?.examination_id) {
      toast.error('The selected result has no examination reference');
      return;
    }
    try {
      const response = await api.post('/students/me/recounting-requests', {
        result_id: values.result_id,
        examination_id: result.examination_id,
        subject_id: values.subject_id,
        reason: values.reason,
      });
      toast.success(response.message);
      setOpen(false);
      reset();
      void requests.refetch();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not submit recounting request');
    }
  };

  const columns: DataTableColumn<RecountingRequest>[] = [
    { key: 'exam', header: 'Examination', render: (row) => row.examination_name ?? '—' },
    { key: 'subject', header: 'Subject', render: (row) => <><span className="font-medium">{row.subject_code}</span><span className="block text-xs text-muted-foreground">{row.subject_name}</span></> },
    { key: 'marks', header: 'Original / revised', render: (row) => `${row.original_marks} / ${row.revised_marks ?? '—'}` },
    { key: 'reason', header: 'Reason', render: (row) => <span className="max-w-xs truncate">{row.reason ?? '—'}</span> },
    { key: 'date', header: 'Submitted', render: (row) => formatDate(row.created_at) },
    { key: 'status', header: 'Status', render: (row) => <StatusBadge value={row.request_status} /> },
    { key: 'response', header: 'Admin response', render: (row) => row.admin_response ?? '—' },
  ];

  return (
    <>
      <PageHeader
        eyebrow="Student portal"
        title="Recounting Requests"
        description="Request a recount of external marks for a published result within the announcement window."
        actions={<Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" /> New request</Button>}
      />
      <ErrorPanel error={requests.error ?? results.error} onRetry={() => { void requests.refetch(); void results.refetch(); }} />
      <Card className="mb-5 border-primary/20 bg-primary/5 p-4 text-sm">
        <div className="flex items-start gap-3">
          <ScrollText className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
          <p>A request is reviewed by the Examination Admin. If marks change, grades, SGPA, CGPA and backlog state are recalculated server-side and the result returns to review before republication.</p>
        </div>
      </Card>
      <DataTable columns={columns} data={requests.data ?? []} rowKey={(row) => row.id} empty="You have not requested a recount yet." />
      <CardContent className="px-0 text-xs text-muted-foreground">
        {requests.data?.length ?? 0} request(s) on record. Decisions are appended to your audit history.
      </CardContent>

      <Modal open={open} onClose={() => setOpen(false)} title="Request external marks recount" description="Select a published result and the subject to be recounted." size="lg">
        <form onSubmit={handleSubmit(submit)} className="space-y-4">
          <Field label="Published result" error={errors.result_id?.message}>
            <Select
              {...register('result_id', {
                onChange: () => {
                  setValue('subject_id', '');
                },
              })}
            >
              <option value="">Select result</option>
              {(results.data ?? []).map((result) => (
                <option key={result.id} value={result.id}>
                  Semester {result.semester_number} · {result.academic_year_name} · {result.examination_name ?? 'Published result'} · {formatDate(result.published_at)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Subject" error={errors.subject_id?.message}>
            <Select {...register('subject_id')} disabled={!selectedResult}>
              <option value="">{selectedResult ? 'Select subject' : 'Select a result first'}</option>
              {subjectOptions.map((subject) => (
                <option key={subject.subject_id} value={subject.subject_id}>
                  {subject.subject_code} — {subject.subject_name} · total {subject.total_marks}/{subject.max_marks}
                </option>
              ))}
            </Select>
          </Field>
          {selectedResult && subjectOptions.length === 0 && (
            <Alert variant="warning">This published result has no subject records available for recounting.</Alert>
          )}
          <Field label="Reason" error={errors.reason?.message}>
            <Textarea placeholder="Explain why you are requesting a recount…" {...register('reason')} />
          </Field>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={isSubmitting}>Submit request</Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
