import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { FileText, Plus } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { ErrorPanel } from '@/components/common/ErrorPanel';
import { Button, DataTable, Field, Input, Modal, Select, StatusBadge, Textarea, type DataTableColumn } from '@/components/ui';
import { api, ApiError } from '@/lib/api';
import { useApiQuery } from '@/lib/hooks';
import type { CorrectionRequest, InternalMark } from '@/lib/types';
import { formatDate } from '@/lib/utils';

const schema = z.object({
  subject_code: z.string().min(1, 'Select a subject'),
  reported_marks: z.coerce.number().min(0, 'Reported marks cannot be negative'),
  suggested_marks: z.coerce.number().min(0, 'Suggested marks cannot be negative'),
  explanation: z.string().min(5, 'Explain the discrepancy (at least 5 characters)'),
});
type FormValues = z.infer<typeof schema>;

export function StudentCorrections() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const requests = useApiQuery<CorrectionRequest[]>('student-corrections', '/students/me/mark-correction-requests');
  const marks = useApiQuery<InternalMark[]>('student-marks', '/students/me/internal-marks');
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const submit = async (values: FormValues) => {
    try {
      const response = await api.post('/students/me/mark-correction-requests', {
        subject_code: values.subject_code,
        reported_marks: values.reported_marks,
        suggested_marks: values.suggested_marks,
        explanation: values.explanation,
      });
      toast.success(response.message);
      setOpen(false);
      reset();
      void requests.refetch();
      void queryClient.invalidateQueries({ queryKey: ['faculty-corrections'] });
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not submit request');
    }
  };

  const columns: DataTableColumn<CorrectionRequest>[] = [
    { key: 'subject', header: 'Subject', render: (row) => <><span className="font-medium">{row.subject_code}</span><span className="block text-xs text-muted-foreground">{row.subject_name}</span></> },
    { key: 'reported', header: 'Reported / suggested', render: (row) => `${row.reported_marks} → ${row.suggested_marks ?? '—'}` },
    { key: 'explanation', header: 'Explanation', render: (row) => <span className="max-w-xs truncate">{row.explanation}</span> },
    { key: 'date', header: 'Submitted', render: (row) => formatDate(row.created_at) },
    { key: 'status', header: 'Status', render: (row) => <StatusBadge value={row.request_status} /> },
    { key: 'response', header: 'Faculty response', render: (row) => row.faculty_response ?? '—' },
  ];

  return (
    <>
      <PageHeader
        eyebrow="Student portal"
        title="Marks Correction Requests"
        description="Report a discrepancy in internal marks. The assigned faculty member reviews and resolves it."
        actions={<Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" /> New request</Button>}
      />
      <ErrorPanel error={requests.error ?? marks.error} onRetry={() => { void requests.refetch(); void marks.refetch(); }} />
      <DataTable columns={columns} data={requests.data ?? []} rowKey={(row) => row.id} empty="You have not reported any marks discrepancies." />

      <Modal open={open} onClose={() => setOpen(false)} title="Report a marks discrepancy" description="Include the values you believe are correct." size="lg">
        <form onSubmit={handleSubmit(submit)} className="space-y-4">
          <Field label="Subject" error={errors.subject_code?.message}>
            <Select {...register('subject_code')}>
              <option value="">Select subject</option>
              {(marks.data ?? []).map((mark) => <option key={mark.subject_id} value={mark.subject_code}>{mark.subject_code} — {mark.subject_name}</option>)}
            </Select>
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Reported marks" error={errors.reported_marks?.message}>
              <Input type="number" min={0} step="0.01" {...register('reported_marks')} />
            </Field>
            <Field label="Suggested marks" error={errors.suggested_marks?.message}>
              <Input type="number" min={0} step="0.01" {...register('suggested_marks')} />
            </Field>
          </div>
          <p className="text-xs text-muted-foreground">Enter the reported and corrected total marks. The server validates both against the subject maximum.</p>
          <Field label="Explanation" error={errors.explanation?.message}>
            <Textarea placeholder="Describe why these marks appear incorrect…" {...register('explanation')} />
          </Field>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={isSubmitting}><FileText className="h-4 w-4" /> Submit request</Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
