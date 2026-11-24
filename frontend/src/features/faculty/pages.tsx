import { useEffect, useMemo, useState } from 'react';
import { toast } from 'react-hot-toast';
import {
  BookOpen, ClipboardCheck, FileText, GraduationCap, Save, Send, Users,
} from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { StatCard } from '@/components/common/StatCard';
import { ErrorPanel } from '@/components/common/ErrorPanel';
import {
  Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle, DataTable,
  Field, Input, LoadingState, Modal, Select, Skeleton, StatusBadge, Textarea,
  type DataTableColumn,
} from '@/components/ui';
import { api, ApiError } from '@/lib/api';
import { useApiQuery } from '@/lib/hooks';
import type {
  CorrectionRequest, DataRecord, FacultyAssignment, FacultyStudent, InternalMark,
  Page as PageData, ScheduleItem,
} from '@/lib/types';
import { formatDate, formatTime } from '@/lib/utils';
import { useAuth } from '@/providers/auth-context';

function useFacultyAssignments() {
  return useApiQuery<FacultyAssignment[]>('faculty-assignments', '/faculty/me/assignments');
}

export function FacultyDashboard() {
  const { user } = useAuth();
  const profile = useApiQuery<DataRecord>('faculty-profile', '/faculty/me');
  const assignments = useFacultyAssignments();
  const submissions = useApiQuery<DataRecord[]>('faculty-submissions', '/faculty/me/marks-submissions');
  const corrections = useApiQuery<CorrectionRequest[]>('faculty-corrections', '/faculty/me/correction-requests');
  const timetable = useApiQuery<ScheduleItem[]>('faculty-timetable', '/faculty/me/timetable');
  const error = profile.error ?? assignments.error ?? submissions.error ?? corrections.error;

  if (assignments.isLoading) return <LoadingState label="Loading your workspace…" />;

  const pending = (corrections.data ?? []).filter((item) => !['RESOLVED', 'REJECTED'].includes(item.request_status));
  return (
    <>
      <PageHeader
        eyebrow="Faculty portal"
        title={`Welcome, ${user?.full_name ?? 'faculty'}`}
        description="Enter internal marks, submit them for verification and respond to student correction requests."
        actions={<Badge variant="outline">{profile.data?.faculty_id ?? 'Faculty'}</Badge>}
      />
      <ErrorPanel error={error} onRetry={() => { void profile.refetch(); void assignments.refetch(); void submissions.refetch(); void corrections.refetch(); }} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Assigned subjects" value={assignments.data?.length ?? 0} icon={BookOpen} />
        <StatCard label="Marks submissions" value={submissions.data?.length ?? 0} icon={ClipboardCheck} tone="success" />
        <StatCard label="Pending corrections" value={pending.length} icon={FileText} tone="warning" />
        <StatCard label="Upcoming exams" value={timetable.data?.length ?? 0} icon={GraduationCap} tone="primary" />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>My assigned subjects</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {(assignments.data ?? []).map((assignment) => (
              <div key={assignment.id} className="flex items-center justify-between rounded-lg border border-border p-3">
                <div>
                  <p className="font-medium">{assignment.subject_code} — {assignment.subject_name}</p>
                  <p className="text-xs text-muted-foreground">{assignment.credits} credits · Section {assignment.section ?? '—'}</p>
                </div>
                <StatusBadge value={assignment.assignment_status} />
              </div>
            ))}
            {!assignments.data?.length && <Alert>No active subject assignments are configured for your account.</Alert>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Recent marks submissions</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {(submissions.data ?? []).slice(0, 5).map((submission) => (
              <div key={String(submission.id)} className="flex items-center justify-between rounded-lg border border-border p-3">
                <div>
                  <p className="font-medium">{String(submission.subject_code)}</p>
                  <p className="text-xs text-muted-foreground">{formatDate(String(submission.submitted_at), true)}</p>
                </div>
                <StatusBadge value={String(submission.status)} />
              </div>
            ))}
            {!submissions.data?.length && <p className="text-sm text-muted-foreground">No marks submitted yet.</p>}
          </CardContent>
        </Card>
      </div>
    </>
  );
}

export function FacultyAssignments() {
  const assignments = useFacultyAssignments();
  const columns: DataTableColumn<FacultyAssignment>[] = [
    { key: 'code', header: 'Code', render: (row) => <span className="font-medium">{row.subject_code}</span> },
    { key: 'name', header: 'Subject', render: (row) => row.subject_name },
    { key: 'credits', header: 'Credits', render: (row) => row.credits },
    { key: 'section', header: 'Section', render: (row) => row.section ?? '—' },
    { key: 'internal', header: 'Internal max', render: (row) => row.internal_max_marks ?? '—' },
    { key: 'external', header: 'External max', render: (row) => row.external_max_marks ?? '—' },
    { key: 'status', header: 'Status', render: (row) => <StatusBadge value={row.assignment_status} /> },
  ];
  return (
    <>
      <PageHeader eyebrow="Faculty portal" title="My Assignments" description="Subjects you are authorised to enter marks for. Access is verified by the backend on every request." />
      <ErrorPanel error={assignments.error} onRetry={() => void assignments.refetch()} />
      <DataTable columns={columns} data={assignments.data ?? []} rowKey={(row) => row.id} empty="No active assignments found." />
    </>
  );
}

export function FacultyClasses() {
  const assignments = useFacultyAssignments();
  const [subjectId, setSubjectId] = useState('');
  const [search, setSearch] = useState('');
  const classes = useApiQuery<DataRecord[]>('faculty-classes', '/faculty/me/classes');
  const students = useApiQuery<PageData<FacultyStudent>>(
    'faculty-students',
    '/faculty/me/students',
    { subject_id: subjectId || undefined, search: search || undefined, page_size: 100 },
  );
  const items = (students.data as { items: FacultyStudent[] } | undefined)?.items ?? [];

  const columns: DataTableColumn<FacultyStudent>[] = [
    { key: 'roll', header: 'Roll number', render: (row) => <span className="font-medium">{row.roll_number}</span> },
    { key: 'name', header: 'Student', render: (row) => <>{row.full_name}<span className="block text-xs text-muted-foreground">{row.email}</span></> },
    { key: 'branch', header: 'Branch', render: (row) => row.branch ?? '—' },
    { key: 'sem', header: 'Semester', render: (row) => row.semester },
    { key: 'section', header: 'Section', render: (row) => row.section ?? '—' },
  ];

  return (
    <>
      <PageHeader eyebrow="Faculty portal" title="Classes & Students" description="Students visible here are scoped to your active faculty assignments." />
      <ErrorPanel error={classes.error ?? students.error ?? assignments.error} onRetry={() => { void classes.refetch(); void students.refetch(); }} />
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {(classes.data ?? []).map((item, index) => (
          <Card key={index} className="p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Assigned class {index + 1}</p>
            <p className="mt-2 text-2xl font-bold">{String(item.student_count ?? 0)}</p>
            <p className="text-xs text-muted-foreground">students · Section {String(item.section ?? '—')}</p>
          </Card>
        ))}
      </div>
      <Card className="mb-5">
        <CardContent className="grid gap-4 p-4 sm:grid-cols-2">
          <Field label="Filter by subject">
            <Select value={subjectId} onChange={(event) => setSubjectId(event.target.value)}>
              <option value="">All assigned subjects</option>
              {(assignments.data ?? []).map((assignment) => <option key={assignment.id} value={assignment.subject_id}>{assignment.subject_code} — {assignment.subject_name}</option>)}
            </Select>
          </Field>
          <Field label="Search students">
            <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Name or roll number" />
          </Field>
        </CardContent>
      </Card>
      <DataTable columns={columns} data={items} rowKey={(row) => row.id} empty="No students match the selected assignment scope." />
    </>
  );
}

const INTERNAL_COMPONENTS = [
  { key: 'mid1', name: 'MID-1', max: 25, field: 'mid1_marks' },
  { key: 'mid2', name: 'MID-2', max: 25, field: 'mid2_marks' },
  { key: 'assignments', name: 'Assignments', max: 5, field: 'assignments_marks' },
] as const;
type ComponentKey = (typeof INTERNAL_COMPONENTS)[number]['key'];
type MarkGrid = Record<string, Record<ComponentKey, number>>;

const round2 = (value: number) => Math.round((value + Number.EPSILON) * 100) / 100;

function internalTotal(row?: Record<ComponentKey, number>): number {
  if (!row) return 0;
  const best = Math.max(row.mid1, row.mid2);
  const other = Math.min(row.mid1, row.mid2);
  return Math.ceil(round2(best * 0.8 + other * 0.2 + row.assignments));
}

export function FacultyMarksEntry() {
  const assignments = useFacultyAssignments();
  const [subjectId, setSubjectId] = useState('');
  const [grid, setGrid] = useState<MarkGrid>({});
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const assignment = (assignments.data ?? []).find((item) => item.subject_id === subjectId);

  const students = useApiQuery<{ items: FacultyStudent[] }>(
    'faculty-students',
    '/faculty/me/students',
    { subject_id: subjectId || undefined, page_size: 100 },
    { enabled: Boolean(subjectId) },
  );
  const existing = useApiQuery<InternalMark[]>(
    'faculty-marks',
    '/faculty/me/internal-marks',
    { subject_id: subjectId || undefined },
    { enabled: Boolean(subjectId) },
  );

  useEffect(() => {
    if (!existing.data) return;
    const next: MarkGrid = {};
    existing.data.forEach((mark) => {
      next[mark.student_id] = {
        mid1: Number(mark.mid1_marks ?? mark.component_marks?.['MID-1'] ?? 0),
        mid2: Number(mark.mid2_marks ?? mark.component_marks?.['MID-2'] ?? 0),
        assignments: Number(mark.assignments_marks ?? mark.component_marks?.['Assignments'] ?? 0),
      };
    });
    setGrid(next);
  }, [existing.data]);

  const entries = useMemo(() => (students.data?.items ?? []).map((student) => ({
    student_id: student.id,
    subject_id: subjectId,
    mid1_marks: Number(grid[student.id]?.mid1 ?? 0),
    mid2_marks: Number(grid[student.id]?.mid2 ?? 0),
    assignments_marks: Number(grid[student.id]?.assignments ?? 0),
    save_as_draft: true,
  })), [students.data, subjectId, grid]);

  const payload = () => ({
    subject_id: subjectId,
    examination_id: assignment?.examination_id || undefined,
    entries,
  });

  const save = async (submit: boolean) => {
    if (!subjectId || entries.length === 0) {
      toast.error('Select an assigned subject with students first');
      return;
    }
    if (submit) setSubmitting(true); else setSaving(true);
    try {
      const response = submit
        ? await api.post('/faculty/me/marks-submissions', payload())
        : await api.post('/faculty/me/internal-marks', payload());
      toast.success(response.message);
      void existing.refetch();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not save marks');
    } finally {
      setSaving(false);
      setSubmitting(false);
    }
  };

  const setMark = (studentId: string, key: ComponentKey, value: string, maximum: number) => {
    const numeric = Number(value);
    if (Number.isNaN(numeric) || numeric < 0 || numeric > maximum) return;
    setGrid((current) => ({
      ...current,
      [studentId]: { ...(current[studentId] ?? { mid1: 0, mid2: 0, assignments: 0 }), [key]: numeric },
    }));
  };

  return (
    <>
      <PageHeader
        eyebrow="Faculty portal"
        title="Internal Marks Entry"
        description="Fixed structure: MID-1 out of 25, MID-2 out of 25 and Assignments out of 5. The server calculates the authoritative total."
        actions={<Button variant="outline" onClick={() => void existing.refetch()}>Refresh marks</Button>}
      />
      <ErrorPanel error={assignments.error ?? students.error ?? existing.error} onRetry={() => { void assignments.refetch(); void students.refetch(); void existing.refetch(); }} />
      <Card className="mb-5">
        <CardContent className="p-4">
          <Field label="Assigned subject" className="max-w-xl">
            <Select value={subjectId} onChange={(event) => { setSubjectId(event.target.value); setGrid({}); }}>
              <option value="">Select a subject</option>
              {(assignments.data ?? []).map((item) => <option key={item.id} value={item.subject_id}>{item.subject_code} — {item.subject_name}</option>)}
            </Select>
          </Field>
          {assignment && (
            <p className="mt-2 text-xs text-muted-foreground">
              Internal maximum {assignment.internal_max_marks ?? 30} · External maximum {assignment.external_max_marks ?? '—'}
            </p>
          )}
        </CardContent>
      </Card>

      {!subjectId ? <Alert variant="info">Choose an assigned subject to load its students and marks sheet.</Alert> : (
        students.isLoading || existing.isLoading ? <LoadingState label="Loading marks sheet…" /> : (
          <>
            <div className="w-full overflow-x-auto rounded-lg border border-border">
              <table className="w-full border-collapse text-left text-sm">
                <thead className="bg-muted/70 text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="whitespace-nowrap px-4 py-3">Roll no.</th>
                    <th className="whitespace-nowrap px-4 py-3">Student</th>
                    {INTERNAL_COMPONENTS.map((component) => (
                      <th key={component.key} className="whitespace-nowrap px-3 py-3">{component.name} / {component.max}</th>
                    ))}
                    <th className="whitespace-nowrap px-3 py-3">Total / 30</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border bg-card">
                  {(students.data?.items ?? []).map((student) => {
                    const total = internalTotal(grid[student.id]);
                    return (
                      <tr key={student.id}>
                        <td className="whitespace-nowrap px-4 py-2 font-medium">{student.roll_number}</td>
                        <td className="whitespace-nowrap px-4 py-2">{student.full_name}</td>
                        {INTERNAL_COMPONENTS.map((component) => (
                          <td key={component.key} className="px-3 py-2">
                            <Input
                              type="number"
                              min={0}
                              max={component.max}
                              value={grid[student.id]?.[component.key] ?? 0}
                              onChange={(event) => setMark(student.id, component.key, event.target.value, component.max)}
                              className="h-9 w-20"
                              aria-label={`${component.name} for ${student.roll_number}`}
                            />
                          </td>
                        ))}
                        <td className={`whitespace-nowrap px-3 py-2 font-semibold ${total > 30 ? 'text-destructive' : 'text-primary'}`}>
                          {total}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => save(false)} loading={saving}><Save className="h-4 w-4" /> Save as draft</Button>
              <Button onClick={() => save(true)} loading={submitting}><Send className="h-4 w-4" /> Submit for verification</Button>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              Total preview is (best MID × 0.8) + (other MID × 0.2) + Assignments, rounded up to the next whole number. The server recomputes and stores this authoritative value; totals above 30 are rejected.
            </p>
          </>
        )
      )}
    </>
  );
}

export function FacultySubmissions() {
  const submissions = useApiQuery<DataRecord[]>('faculty-submissions', '/faculty/me/marks-submissions');
  const columns: DataTableColumn<DataRecord>[] = [
    { key: 'code', header: 'Subject', render: (row) => <span className="font-medium">{String(row.subject_code)}</span> },
    { key: 'name', header: 'Subject name', render: (row) => String(row.subject_name) },
    { key: 'submitted', header: 'Submitted', render: (row) => formatDate(String(row.submitted_at), true) },
    { key: 'note', header: 'Review note', render: (row) => String(row.review_note ?? '—') },
    { key: 'status', header: 'Status', render: (row) => <StatusBadge value={String(row.status)} /> },
  ];
  return (
    <>
      <PageHeader eyebrow="Faculty portal" title="Marks Submissions" description="Track the verification status of submitted internal marks." />
      <ErrorPanel error={submissions.error} onRetry={() => void submissions.refetch()} />
      <DataTable columns={columns} data={submissions.data ?? []} rowKey={(row) => String(row.id)} empty="No marks submissions recorded." />
    </>
  );
}

export function FacultyCorrections() {
  const requests = useApiQuery<CorrectionRequest[]>('faculty-corrections', '/faculty/me/correction-requests');
  const [active, setActive] = useState<CorrectionRequest | null>(null);
  const [action, setAction] = useState('approve');
  const [response, setResponse] = useState('');
  const [correctedMarks, setCorrectedMarks] = useState('');
  const [busy, setBusy] = useState(false);

  const review = async () => {
    if (!active) return;
    if (action === 'correct' && correctedMarks === '') {
      toast.error('Enter the corrected total before saving');
      return;
    }
    setBusy(true);
    try {
      const result = await api.patch(`/faculty/me/correction-requests/${active.id}`, {
        action,
        faculty_response: response,
        ...(action === 'correct' ? { corrected_marks: Number(correctedMarks) } : {}),
      });
      toast.success(result.message);
      setActive(null);
      setResponse('');
      setCorrectedMarks('');
      void requests.refetch();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not review request');
    } finally {
      setBusy(false);
    }
  };

  const columns: DataTableColumn<CorrectionRequest>[] = [
    { key: 'student', header: 'Student', render: (row) => <><span className="font-medium">{row.roll_number}</span><span className="block text-xs text-muted-foreground">{row.student_name}</span></> },
    { key: 'subject', header: 'Subject', render: (row) => `${row.subject_code} — ${row.subject_name}` },
    { key: 'reason', header: 'Explanation', render: (row) => <span className="max-w-xs truncate">{row.explanation}</span> },
    { key: 'date', header: 'Submitted', render: (row) => formatDate(row.created_at) },
    { key: 'status', header: 'Status', render: (row) => <StatusBadge value={row.request_status} /> },
    {
      key: 'action',
      header: '',
      render: (row) => ['RESOLVED', 'REJECTED'].includes(row.request_status) ? <span className="text-xs text-muted-foreground">Closed</span> : (
        <Button variant="outline" size="sm" onClick={() => { setActive(row); setAction('approve'); setCorrectedMarks(''); }}>Review</Button>
      ),
    },
  ];

  return (
    <>
      <PageHeader eyebrow="Faculty portal" title="Correction Requests" description="Review student-reported discrepancies in internal marks." />
      <ErrorPanel error={requests.error} onRetry={() => void requests.refetch()} />
      <DataTable columns={columns} data={requests.data ?? []} rowKey={(row) => row.id} empty="No correction requests are assigned to you." />

      <Modal open={Boolean(active)} onClose={() => setActive(null)} title="Review correction request" description={active ? `${active.subject_code} · ${active.roll_number}` : undefined}>
        {active && (
          <div className="space-y-4">
            <Alert variant="info">{active.explanation}</Alert>
            <div className="grid gap-3 sm:grid-cols-2">
              <Card className="p-3">
                <p className="text-xs text-muted-foreground">Reported total marks</p>
                <p className="mt-1 text-xl font-bold">{active.reported_marks}</p>
              </Card>
              <Card className="p-3">
                <p className="text-xs text-muted-foreground">Suggested total marks</p>
                <p className="mt-1 text-xl font-bold">{active.suggested_marks ?? '—'}</p>
              </Card>
            </div>
            <Field label="Decision">
              <Select value={action} onChange={(event) => setAction(event.target.value)}>
                <option value="approve">Approve / resolve</option>
                <option value="correct">Apply corrected total</option>
                <option value="under_review">Mark under review</option>
                <option value="reject">Reject</option>
              </Select>
            </Field>
            {action === 'correct' && (
              <Field label="Corrected total marks" hint="The server validates this against the subject maximum and resets verification.">
                <Input type="number" min={0} step="0.01" value={correctedMarks} onChange={(event) => setCorrectedMarks(event.target.value)} />
              </Field>
            )}
            <Field label="Response to student">
              <Textarea value={response} onChange={(event) => setResponse(event.target.value)} placeholder="Explain your decision…" />
            </Field>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setActive(null)}>Cancel</Button>
              <Button onClick={review} loading={busy}>Save review</Button>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}

export function FacultyTimetable() {
  const timetable = useApiQuery<ScheduleItem[]>('faculty-timetable', '/faculty/me/timetable');
  const columns: DataTableColumn<ScheduleItem>[] = [
    { key: 'date', header: 'Date', render: (row) => <span className="font-medium">{formatDate(row.exam_date)}</span> },
    { key: 'time', header: 'Time', render: (row) => `${formatTime(row.start_time)} – ${formatTime(row.end_time)}` },
    { key: 'subject', header: 'Subject', render: (row) => <>{row.subject_code}<span className="block text-xs text-muted-foreground">{row.subject_name}</span></> },
    { key: 'venue', header: 'Venue', render: (row) => row.venue ?? '—' },
    { key: 'session', header: 'Session', render: (row) => row.session ?? '—' },
  ];
  return (
    <>
      <PageHeader eyebrow="Faculty portal" title="Examination Timetable" description="Published exam schedules for subjects assigned to you." />
      <ErrorPanel error={timetable.error} onRetry={() => void timetable.refetch()} />
      <DataTable columns={columns} data={timetable.data ?? []} rowKey={(row) => row.id} empty="No published timetable entries for your subjects." />
    </>
  );
}

export function FacultyProfile() {
  const profile = useApiQuery<DataRecord>('faculty-profile', '/faculty/me');
  if (profile.isLoading) return <LoadingState label="Loading profile…" />;
  const fields: Array<[string, unknown]> = [
    ['Faculty ID', profile.data?.faculty_id],
    ['Full name', profile.data?.full_name],
    ['Email', profile.data?.email],
    ['Department', profile.data?.department],
    ['Designation', profile.data?.designation],
    ['Account status', profile.data?.account_status],
  ];
  return (
    <>
      <PageHeader eyebrow="Faculty portal" title="My Profile" description="Profile information is maintained by the Examination Admin." />
      <ErrorPanel error={profile.error} onRetry={() => void profile.refetch()} />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="p-5 lg:col-span-2">
          <h2 className="mb-4 flex items-center gap-2 text-base font-semibold"><Users className="h-5 w-5 text-primary" /> Faculty details</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {fields.map(([label, value]) => (
              <div key={label} className="rounded-lg border border-border p-3">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="font-medium">{String(value ?? '—')}</p>
              </div>
            ))}
          </div>
        </Card>
        <Card className="p-5">
          <h2 className="mb-3 flex items-center gap-2 text-base font-semibold"><BookOpen className="h-5 w-5 text-primary" /> Assigned subjects</h2>
          <div className="space-y-2">
            {(profile.data?.assigned_subjects as DataRecord[] | undefined)?.map((subject) => (
              <div key={String(subject.id)} className="rounded-lg border border-border p-3 text-sm">
                <p className="font-medium">{String(subject.subject_code)}</p>
                <p className="text-xs text-muted-foreground">{String(subject.subject_name)} · Section {String(subject.section ?? '—')}</p>
              </div>
            ))}
            {!(profile.data?.assigned_subjects as unknown[] | undefined)?.length && <Skeleton className="h-20 w-full" />}
          </div>
        </Card>
      </div>
    </>
  );
}
