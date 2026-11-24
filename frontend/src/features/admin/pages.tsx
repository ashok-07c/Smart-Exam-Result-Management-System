import { useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import {
  Activity, Award, CheckCircle2, ClipboardCheck, Download, FileText, GraduationCap,
  LockKeyhole, PlayCircle, RefreshCw, Send, ShieldCheck, Users,
} from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { StatCard } from '@/components/common/StatCard';
import { ErrorPanel } from '@/components/common/ErrorPanel';
import {
  Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle, Checkbox, DataTable,
  Field, Input, Modal, Pagination, Select, StatusBadge, Tabs, Textarea,
  type DataTableColumn,
} from '@/components/ui';
import { api, ApiError } from '@/lib/api';
import { useApiEnvelope, useApiQuery } from '@/lib/hooks';
import type { DataRecord, Page as PageType } from '@/lib/types';
import { formatDate, formatTime, titleCase } from '@/lib/utils';

const text = (key: string, header: string, className?: string): DataTableColumn<DataRecord> => ({
  key,
  header,
  className,
  render: (row) => <span>{String(row[key] ?? '—')}</span>,
});
const status = (key: string, header = 'Status'): DataTableColumn<DataRecord> => ({
  key,
  header,
  render: (row) => <StatusBadge value={String(row[key] ?? '')} />,
});
const dateCol = (key: string, header: string): DataTableColumn<DataRecord> => ({
  key,
  header,
  render: (row) => formatDate(String(row[key] ?? ''), true),
});
const action = (key: string, label: string, onClick: (row: DataRecord) => void): DataTableColumn<DataRecord> => ({
  key,
  header: '',
  render: (row) => <Button variant="outline" size="sm" onClick={() => onClick(row)}>{label}</Button>,
});

function describeError(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Operation failed';
  const first = error.details?.[0] as Record<string, unknown> | undefined;
  if (first) {
    const issues = Array.isArray(first.issues) ? first.issues : [];
    const detail = [first.student, ...issues].filter(Boolean).join(': ');
    if (detail) return `${error.message} — ${detail}`;
  }
  return error.message;
}

async function run(actionFn: () => Promise<{ message: string }>, refresh?: () => void) {
  try {
    const result = await actionFn();
    toast.success(result.message);
    refresh?.();
  } catch (error) {
    toast.error(describeError(error));
  }
}

function FormFields({ children, onSubmit, submitLabel = 'Save', busy = false }: {
  children: ReactNode;
  onSubmit: () => void;
  submitLabel?: string;
  busy?: boolean;
}) {
  return (
    <form onSubmit={(event) => { event.preventDefault(); onSubmit(); }} className="space-y-4">
      {children}
      <div className="flex justify-end"><Button type="submit" loading={busy}>{submitLabel}</Button></div>
    </form>
  );
}

export function AdminDashboard() {
  const dashboard = useApiQuery<DataRecord>('admin-dashboard', '/admin/dashboard');
  const data = dashboard.data;
  return (
    <>
      <PageHeader eyebrow="Examination Admin" title="Administration Dashboard" description="Control the full examination lifecycle from registration to result publication." />
      <ErrorPanel error={dashboard.error} onRetry={() => void dashboard.refetch()} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Students" value={data?.total_students ?? '—'} icon={GraduationCap} />
        <StatCard label="Faculty" value={data?.total_faculty ?? '—'} icon={Users} tone="success" />
        <StatCard label="Open examinations" value={data?.active_examinations ?? '—'} icon={ClipboardCheck} tone="warning" />
        <StatCard label="Registrations" value={data?.total_registrations ?? '—'} icon={Award} />
      </div>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Marks submissions" value={data?.pending_marks_submissions ?? '—'} icon={ClipboardCheck} />
        <StatCard label="Correction requests" value={data?.pending_corrections ?? '—'} icon={FileText} tone="warning" />
        <StatCard label="Results to process" value={data?.results_awaiting_processing ?? '—'} icon={Activity} tone="primary" />
        <StatCard label="Recounting queue" value={data?.pending_recounting ?? '—'} icon={RefreshCw} tone="destructive" />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Upcoming examinations</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {(data?.upcoming_examinations as DataRecord[] | undefined)?.map((exam) => (
              <div key={String(exam.id)} className="flex items-center justify-between rounded-lg border border-border p-3">
                <div><p className="font-medium">{String(exam.name)}</p><p className="text-xs text-muted-foreground">{String(exam.exam_type)} · Deadline {formatDate(String(exam.registration_deadline))}</p></div>
                <StatusBadge value={String(exam.exam_type)} />
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Recent activity</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {(data?.recent_activity as DataRecord[] | undefined)?.map((item) => (
              <div key={String(item.id)} className="border-l-2 border-primary/40 pl-3">
                <p className="text-sm font-medium">{titleCase(String(item.action))}</p>
                <p className="text-xs text-muted-foreground">{String(item.entity_type)} · {formatDate(String(item.created_at), true)}</p>
              </div>
            ))}
            {!data?.recent_activity?.length && <p className="text-sm text-muted-foreground">No activity recorded yet.</p>}
          </CardContent>
        </Card>
      </div>
    </>
  );
}

export function AdminStudents() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ email: '', password: '', roll_number: '', full_name: '', academic_year: '2023-24', admission_year: '2023-24', current_semester: 1, section: '', department_id: '', branch_id: '' });
  const [busy, setBusy] = useState(false);
  const students = useApiEnvelope<PageType<DataRecord>>('admin-students', '/admin/students', { search: search || undefined, page, page_size: 20 });
  const years = useApiQuery<DataRecord[]>('admin-years', '/admin/academic-years');
  const branches = useApiQuery<DataRecord[]>('admin-branches', '/admin/branches');
  const departments = useApiQuery<DataRecord[]>('admin-departments', '/admin/departments');
  const refresh = () => void students.refetch();

  const create = async () => {
    setBusy(true);
    await run(() => api.post('/admin/students', { ...form, department_id: form.department_id || null, branch_id: form.branch_id || null }), refresh);
    setBusy(false);
    setOpen(false);
  };

  const columns: DataTableColumn<DataRecord>[] = [
    text('roll_number', 'Roll number'), text('full_name', 'Student'), text('email', 'Email'),
    text('department', 'Department'), text('branch', 'Branch'), text('current_semester', 'Semester'),
    status('enrollment_status'),
    action('deactivate', 'Deactivate', (row) => run(() => api.delete(`/admin/students/${String(row.id)}`), refresh)),
  ];

  return (
    <>
      <PageHeader eyebrow="Examination Admin" title="Student Records" description="Create and maintain student accounts. Student role and eligibility are determined server-side." actions={<Button onClick={() => setOpen(true)}>Add student</Button>} />
      <ErrorPanel error={students.error ?? years.error} onRetry={() => { refresh(); void years.refetch(); }} />
      <Card className="mb-5"><CardContent className="p-4"><Field label="Search students"><Input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Name or roll number" /></Field></CardContent></Card>
      <Card className="p-4">
        <DataTable columns={columns} data={students.data?.data.items ?? []} rowKey={(row) => String(row.id)} empty="No student records found." />
        {students.data?.data && <div className="mt-4"><Pagination page={students.data.data.page} pages={students.data.data.pages} total={students.data.data.total} onChange={setPage} /></div>}
      </Card>
      <Modal open={open} onClose={() => setOpen(false)} title="Create student account" size="lg">
        <FormFields onSubmit={create} submitLabel="Create student" busy={busy}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Full name"><Input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
            <Field label="Email"><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
            <Field label="Roll number"><Input value={form.roll_number} onChange={(e) => setForm({ ...form, roll_number: e.target.value })} /></Field>
            <Field label="Temporary password"><Input value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
            <Field label="Department"><Select value="" onChange={(e) => setForm({ ...form, department_id: e.target.value })}><option value="">Optional</option>{(departments.data ?? []).map((d) => <option key={String(d.id)} value={String(d.id)}>{String(d.department_name)}</option>)}</Select></Field>
            <Field label="Branch"><Select value="" onChange={(e) => setForm({ ...form, branch_id: e.target.value })}><option value="">Optional</option>{(branches.data ?? []).map((b) => <option key={String(b.id)} value={String(b.id)}>{String(b.branch_name)}</option>)}</Select></Field>
            <Field label="Current semester"><Input type="number" min={1} max={12} value={form.current_semester} onChange={(e) => setForm({ ...form, current_semester: Number(e.target.value) })} /></Field>
            <Field label="Section"><Input value={form.section} onChange={(e) => setForm({ ...form, section: e.target.value })} /></Field>
            <Field label="Academic year"><Select value={form.academic_year} onChange={(e) => setForm({ ...form, academic_year: e.target.value })}><option value="">Select year</option>{(years.data ?? []).map((y) => <option key={String(y.id)} value={String(y.academic_year_name)}>{String(y.academic_year_name)}</option>)}</Select></Field>
            <Field label="Admission year"><Select value={form.admission_year} onChange={(e) => setForm({ ...form, admission_year: e.target.value })}><option value="">Select year</option>{(years.data ?? []).map((y) => <option key={String(y.id)} value={String(y.academic_year_name)}>{String(y.academic_year_name)}</option>)}</Select></Field>
          </div>
        </FormFields>
      </Modal>
    </>
  );
}

export function AdminFaculty() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ email: '', password: '', faculty_id: '', full_name: '', designation: 'Faculty', department_id: '' });
  const [busy, setBusy] = useState(false);
  const faculty = useApiEnvelope<PageType<DataRecord>>('admin-faculty', '/admin/faculty', { search: search || undefined, page, page_size: 20 });
  const departments = useApiQuery<DataRecord[]>('admin-departments', '/admin/departments');
  const refresh = () => void faculty.refetch();

  const create = async () => {
    setBusy(true);
    await run(() => api.post('/admin/faculty', { ...form, department_id: form.department_id || null }), refresh);
    setBusy(false);
    setOpen(false);
  };
  const columns: DataTableColumn<DataRecord>[] = [
    text('faculty_id', 'Faculty ID'), text('full_name', 'Name'), text('email', 'Email'),
    text('department', 'Department'), text('designation', 'Designation'), status('account_status'),
    action('deactivate', 'Deactivate', (row) => run(() => api.delete(`/admin/faculty/${String(row.id)}`), refresh)),
  ];
  return (
    <>
      <PageHeader eyebrow="Examination Admin" title="Faculty Records" description="Faculty accounts and their assignment scope across subjects." actions={<Button onClick={() => setOpen(true)}>Add faculty</Button>} />
      <ErrorPanel error={faculty.error} onRetry={refresh} />
      <Card className="mb-5"><CardContent className="p-4"><Field label="Search faculty"><Input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Name or faculty ID" /></Field></CardContent></Card>
      <Card className="p-4">
        <DataTable columns={columns} data={faculty.data?.data.items ?? []} rowKey={(row) => String(row.id)} empty="No faculty records found." />
        {faculty.data?.data && <div className="mt-4"><Pagination page={faculty.data.data.page} pages={faculty.data.data.pages} total={faculty.data.data.total} onChange={setPage} /></div>}
      </Card>
      <Modal open={open} onClose={() => setOpen(false)} title="Create faculty account" size="lg">
        <FormFields onSubmit={create} submitLabel="Create faculty" busy={busy}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Full name"><Input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
            <Field label="Email"><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
            <Field label="Faculty ID"><Input value={form.faculty_id} onChange={(e) => setForm({ ...form, faculty_id: e.target.value })} /></Field>
            <Field label="Temporary password"><Input value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
            <Field label="Department"><Select value="" onChange={(e) => setForm({ ...form, department_id: e.target.value })}><option value="">Optional</option>{(departments.data ?? []).map((d) => <option key={String(d.id)} value={String(d.id)}>{String(d.department_name)}</option>)}</Select></Field>
            <Field label="Designation"><Input value={form.designation} onChange={(e) => setForm({ ...form, designation: e.target.value })} /></Field>
          </div>
        </FormFields>
      </Modal>
    </>
  );
}

const SUPPORTED_COURSES = [
  { course_code: 'CSE', course_name: 'Computer Science & Engineering' },
  { course_code: 'ECE', course_name: 'Electronics & Communication Engineering' },
  { course_code: 'EEE', course_name: 'Electrical & Electronics Engineering' },
  { course_code: 'MECH', course_name: 'Mechanical Engineering' },
  { course_code: 'CIVIL', course_name: 'Civil Engineering' },
  { course_code: 'AI&ML', course_name: 'Artificial Intelligence & Machine Learning' },
];

export function AdminAcademics() {
  const [tab, setTab] = useState('courses');
  const years = useApiQuery<DataRecord[]>('admin-years', '/admin/academic-years');
  const semesters = useApiQuery<DataRecord[]>('admin-semesters', '/admin/semesters');
  const regulations = useApiQuery<DataRecord[]>('admin-regulations', '/admin/regulations');
  const courses = useApiQuery<DataRecord[]>('admin-courses', '/admin/courses');
  const subjects = useApiQuery<DataRecord[]>('admin-subjects', '/admin/subjects');
  const [yearForm, setYearForm] = useState({ academic_year_name: '' });
  const [courseForm, setCourseForm] = useState({ course_code: 'CSE', duration_years: 4 });
  const [subjectForm, setSubjectForm] = useState({ subject_code: '', subject_name: '', credits: 3, internal_max_marks: 30, external_max_marks: 70, subject_type: 'THEORY', course_id: '', semester_id: '' });
  const [regulationForm, setRegulationForm] = useState({ regulation_name: '', effective_year: '2023' });
  const [busy, setBusy] = useState(false);

  const createYear = async () => {
    setBusy(true);
    await run(() => api.post('/admin/academic-years', yearForm), () => { void years.refetch(); setYearForm({ academic_year_name: '' }); });
    setBusy(false);
  };
  const createCourse = async () => {
    const preset = SUPPORTED_COURSES.find((item) => item.course_code === courseForm.course_code);
    setBusy(true);
    await run(() => api.post('/admin/courses', { ...courseForm, course_name: preset?.course_name ?? courseForm.course_code }), () => void courses.refetch());
    setBusy(false);
  };
  const createSubject = async () => {
    setBusy(true);
    await run(() => api.post('/admin/subjects', { ...subjectForm, course_id: subjectForm.course_id || null, semester_id: subjectForm.semester_id || null }), () => void subjects.refetch());
    setBusy(false);
  };
  const createRegulation = async () => {
    setBusy(true);
    await run(() => api.post('/admin/regulations', regulationForm), () => void regulations.refetch());
    setBusy(false);
  };

  const table = (rows: DataRecord[], columns: DataTableColumn<DataRecord>[]) => (
    <DataTable columns={columns} data={rows} rowKey={(row) => String(row.id)} empty="No records configured." compact />
  );

  return (
    <>
      <PageHeader eyebrow="Examination Admin" title="Academic Records" description="Manage academic years, the six supported courses, subjects and regulation labels. Grades and pass decisions are centralised in the backend." />
      <ErrorPanel error={years.error ?? courses.error ?? regulations.error ?? subjects.error ?? semesters.error} onRetry={() => { void years.refetch(); void courses.refetch(); void regulations.refetch(); void subjects.refetch(); void semesters.refetch(); }} />
      <Alert variant="info" title="Central grading is authoritative">
        Grade bands and pass/fail decisions are fixed by the server. Regulations here are labels only; no JSON grade rules or pass rules are accepted.
      </Alert>
      <div className="h-4" />
      <Tabs value={tab} onChange={setTab} items={[
        { value: 'courses', label: `Courses (${courses.data?.length ?? 0})`, content: (
          <div className="space-y-5">
            <Card><CardContent className="p-4">
              <h2 className="mb-3 text-sm font-semibold">Supported courses</h2>
              <div className="flex flex-wrap gap-2">
                {SUPPORTED_COURSES.map((preset) => {
                  const configured = (courses.data ?? []).some((course) => String(course.course_code).toUpperCase() === preset.course_code);
                  return <Badge key={preset.course_code} variant={configured ? 'success' : 'outline'}>{preset.course_code} — {configured ? 'configured' : 'missing'}</Badge>;
                })}
              </div>
            </CardContent></Card>
            <Card><CardContent className="p-4">
              <h2 className="mb-4 text-sm font-semibold">Add a course</h2>
              <FormFields onSubmit={createCourse} submitLabel="Add course" busy={busy}>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Course code"><Select value={courseForm.course_code} onChange={(e) => setCourseForm({ ...courseForm, course_code: e.target.value })}>{SUPPORTED_COURSES.map((preset) => <option key={preset.course_code} value={preset.course_code}>{preset.course_code} — {preset.course_name}</option>)}</Select></Field>
                  <Field label="Duration (years)"><Input type="number" min={1} max={6} value={courseForm.duration_years} onChange={(e) => setCourseForm({ ...courseForm, duration_years: Number(e.target.value) })} /></Field>
                </div>
              </FormFields>
            </CardContent></Card>
            {table(courses.data ?? [], [text('course_code', 'Code'), text('course_name', 'Course'), text('duration_years', 'Duration')])}
          </div>
        ) },
        { value: 'years', label: `Academic years (${years.data?.length ?? 0})`, content: (
          <div className="space-y-5">
            <Card><CardContent className="p-4">
              <h2 className="mb-4 text-sm font-semibold">Add academic year</h2>
              <FormFields onSubmit={createYear} submitLabel="Add academic year" busy={busy}>
                <Field label="Year" hint="Format YYYY-YY, starting from 2023-24"><Input value={yearForm.academic_year_name} onChange={(e) => setYearForm({ academic_year_name: e.target.value })} placeholder="2026-27" /></Field>
              </FormFields>
            </CardContent></Card>
            {table(years.data ?? [], [text('academic_year_name', 'Academic year'), status('status')])}
          </div>
        ) },
        { value: 'subjects', label: `Subjects (${subjects.data?.length ?? 0})`, content: (
          <div className="space-y-5">
            <Card><CardContent className="p-4">
              <h2 className="mb-4 text-sm font-semibold">Create subject</h2>
              <FormFields onSubmit={createSubject} submitLabel="Create subject" busy={busy}>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <Field label="Code"><Input value={subjectForm.subject_code} onChange={(e) => setSubjectForm({ ...subjectForm, subject_code: e.target.value })} /></Field>
                  <Field label="Name"><Input value={subjectForm.subject_name} onChange={(e) => setSubjectForm({ ...subjectForm, subject_name: e.target.value })} /></Field>
                  <Field label="Credits"><Input type="number" min={1} value={subjectForm.credits} onChange={(e) => setSubjectForm({ ...subjectForm, credits: Number(e.target.value) })} /></Field>
                  <Field label="Internal max (fixed)"><Input type="number" value={30} readOnly /></Field>
                  <Field label="External max"><Input type="number" min={1} value={subjectForm.external_max_marks} onChange={(e) => setSubjectForm({ ...subjectForm, external_max_marks: Number(e.target.value) })} /></Field>
                  <Field label="Type"><Select value={subjectForm.subject_type} onChange={(e) => setSubjectForm({ ...subjectForm, subject_type: e.target.value })}><option>THEORY</option><option>PRACTICAL</option></Select></Field>
                  <Field label="Course"><Select value={subjectForm.course_id} onChange={(e) => setSubjectForm({ ...subjectForm, course_id: e.target.value })}><option value="">Optional</option>{(courses.data ?? []).map((c) => <option key={String(c.id)} value={String(c.id)}>{String(c.course_code)}</option>)}</Select></Field>
                  <Field label="Semester"><Select value={subjectForm.semester_id} onChange={(e) => setSubjectForm({ ...subjectForm, semester_id: e.target.value })}><option value="">Optional</option>{(semesters.data ?? []).map((s) => <option key={String(s.id)} value={String(s.id)}>Sem {String(s.semester_number)}</option>)}</Select></Field>
                </div>
              </FormFields>
            </CardContent></Card>
            {table(subjects.data ?? [], [text('subject_code', 'Code'), text('subject_name', 'Subject'), text('credits', 'Credits'), text('internal_max_marks', 'Internal'), text('external_max_marks', 'External'), text('subject_type', 'Type')])}
          </div>
        ) },
        { value: 'regulations', label: `Regulations (${regulations.data?.length ?? 0})`, content: (
          <div className="space-y-5">
            <Card><CardContent className="p-4">
              <h2 className="mb-4 text-sm font-semibold">Create regulation label</h2>
              <FormFields onSubmit={createRegulation} submitLabel="Create regulation" busy={busy}>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Regulation name"><Input value={regulationForm.regulation_name} onChange={(e) => setRegulationForm({ ...regulationForm, regulation_name: e.target.value })} /></Field>
                  <Field label="Effective year"><Input value={regulationForm.effective_year} onChange={(e) => setRegulationForm({ ...regulationForm, effective_year: e.target.value })} /></Field>
                </div>
              </FormFields>
            </CardContent></Card>
            {table(regulations.data ?? [], [text('regulation_name', 'Regulation'), text('effective_year', 'Effective year')])}
          </div>
        ) },
      ]} />
    </>
  );
}

export function AdminAssignments() {
  const assignments = useApiQuery<DataRecord[]>('admin-assignments', '/admin/faculty-assignments');
  const faculty = useApiQuery<PageType<DataRecord>>('admin-faculty', '/admin/faculty', { page_size: 200 });
  const subjects = useApiQuery<DataRecord[]>('admin-subjects', '/admin/subjects');
  const [form, setForm] = useState({ faculty_id: '', subject_id: '', section: '' });
  const [busy, setBusy] = useState(false);
  const create = async () => {
    setBusy(true);
    await run(() => api.post('/admin/faculty-assignments', form), () => void assignments.refetch());
    setBusy(false);
  };
  const columns: DataTableColumn<DataRecord>[] = [
    {
      key: 'faculty_name', header: 'Faculty',
      render: (row) => (
        <div>
          <span className="font-medium">{String(row.faculty_name ?? '—')}</span>
          <span className="block text-xs text-muted-foreground">{String(row.faculty_code ?? '')}</span>
        </div>
      ),
    },
    text('subject_code', 'Code'), text('subject_name', 'Subject'),
    text('department', 'Department'), text('section', 'Section'), status('assignment_status'),
    action('remove', 'Remove', (row) => run(() => api.delete(`/admin/faculty-assignments/${String(row.id)}`), () => void assignments.refetch())),
  ];
  return (
    <>
      <PageHeader eyebrow="Examination Admin" title="Faculty Assignments" description="Assign subjects to faculty. All faculty portal actions are authorised against these records." />
      <ErrorPanel error={assignments.error ?? faculty.error ?? subjects.error} onRetry={() => { void assignments.refetch(); void faculty.refetch(); void subjects.refetch(); }} />
      <Card className="mb-5"><CardContent className="p-4">
        <FormFields onSubmit={create} submitLabel="Assign subject" busy={busy}>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Faculty"><Select value={form.faculty_id} onChange={(e) => setForm({ ...form, faculty_id: e.target.value })}><option value="">Select faculty</option>{(faculty.data?.items ?? []).map((f) => <option key={String(f.id)} value={String(f.id)}>{String(f.full_name)} ({String(f.faculty_id)})</option>)}</Select></Field>
            <Field label="Subject"><Select value={form.subject_id} onChange={(e) => setForm({ ...form, subject_id: e.target.value })}><option value="">Select subject</option>{(subjects.data ?? []).map((s) => <option key={String(s.id)} value={String(s.id)}>{String(s.subject_code)} — {String(s.subject_name)}</option>)}</Select></Field>
            <Field label="Section"><Input value={form.section} onChange={(e) => setForm({ ...form, section: e.target.value })} placeholder="e.g. A" /></Field>
          </div>
        </FormFields>
      </CardContent></Card>
      <DataTable columns={columns} data={assignments.data ?? []} rowKey={(row) => String(row.id)} empty="No faculty assignments found." />
    </>
  );
}

export function AdminExaminations() {
  const exams = useApiQuery<DataRecord[]>('admin-examinations', '/admin/examinations');
  const years = useApiQuery<DataRecord[]>('admin-years', '/admin/academic-years');
  const subjects = useApiQuery<DataRecord[]>('admin-subjects', '/admin/subjects');
  const [form, setForm] = useState({
    name: '', exam_type: 'REGULAR', academic_year_id: '',
    registration_start: '', registration_deadline: '', subject_ids: [] as string[],
  });
  const [busy, setBusy] = useState(false);
  const [subjectChoice, setSubjectChoice] = useState('');

  const create = async () => {
    setBusy(true);
    await run(() => api.post('/admin/examinations', { ...form, academic_year_id: form.academic_year_id || null, registration_start: new Date(form.registration_start).toISOString(), registration_deadline: new Date(form.registration_deadline).toISOString() }), () => void exams.refetch());
    setBusy(false);
  };
  const columns: DataTableColumn<DataRecord>[] = [
    text('name', 'Examination'), status('exam_type'), text('status', 'Lifecycle'),
    dateCol('registration_start', 'Registration opens'), dateCol('registration_deadline', 'Deadline'),
    { key: 'subjects', header: 'Subjects', render: (row) => `${(row.subject_ids as unknown[]).length ?? 0}` },
  ];
  return (
    <>
      <PageHeader eyebrow="Examination Admin" title="Examinations" description="Create examination windows and attach eligible subjects. Registration opens only within the configured window." />
      <ErrorPanel error={exams.error ?? subjects.error} onRetry={() => { void exams.refetch(); void subjects.refetch(); }} />
      <Card className="mb-5"><CardContent className="p-4">
        <FormFields onSubmit={create} submitLabel="Create examination" busy={busy}>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Field label="Name" className="sm:col-span-2"><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <Field label="Type"><Select value={form.exam_type} onChange={(e) => setForm({ ...form, exam_type: e.target.value })}><option>REGULAR</option><option>SUPPLEMENTARY</option></Select></Field>
            <Field label="Academic year"><Select value={form.academic_year_id} onChange={(e) => setForm({ ...form, academic_year_id: e.target.value })}><option value="">Optional</option>{(years.data ?? []).map((y) => <option key={String(y.id)} value={String(y.id)}>{String(y.academic_year_name)}</option>)}</Select></Field>
            <Field label="Registration opens"><Input type="datetime-local" value={form.registration_start} onChange={(e) => setForm({ ...form, registration_start: e.target.value })} /></Field>
            <Field label="Registration deadline"><Input type="datetime-local" value={form.registration_deadline} onChange={(e) => setForm({ ...form, registration_deadline: e.target.value })} /></Field>
            <Field label="Add subject">
              <div className="flex gap-2">
                <Select value={subjectChoice} onChange={(e) => setSubjectChoice(e.target.value)}><option value="">Select</option>{(subjects.data ?? []).map((s) => <option key={String(s.id)} value={String(s.id)}>{String(s.subject_code)}</option>)}</Select>
                <Button type="button" variant="outline" onClick={() => { if (subjectChoice && !form.subject_ids.includes(subjectChoice)) setForm({ ...form, subject_ids: [...form.subject_ids, subjectChoice] }); }}>Add</Button>
              </div>
            </Field>
            <Field label="Selected subjects" className="sm:col-span-2 lg:col-span-3">
              <div className="flex flex-wrap gap-2">{form.subject_ids.map((id) => <Badge key={id} variant="outline">{(subjects.data ?? []).find((s) => s.id === id)?.subject_code ?? id}</Badge>)}{!form.subject_ids.length && <span className="text-sm text-muted-foreground">None selected</span>}</div>
            </Field>
          </div>
        </FormFields>
      </CardContent></Card>
      <DataTable columns={columns} data={exams.data ?? []} rowKey={(row) => String(row.id)} empty="No examinations configured." />
    </>
  );
}

export function AdminRegistrations() {
  const [page, setPage] = useState(1);
  const [examId, setExamId] = useState('');
  const registrations = useApiEnvelope<PageType<DataRecord>>('admin-registrations', '/admin/registrations', { page, page_size: 20, examination_id: examId || undefined });
  const exams = useApiQuery<DataRecord[]>('admin-examinations', '/admin/examinations');
  const refresh = () => void registrations.refetch();
  const downloadReceipt = async (row: DataRecord) => {
    try {
      await api.download(`/admin/registrations/${String(row.id)}/receipt`, String(row.fee_receipt_filename ?? 'fee-receipt'));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not download receipt');
    }
  };
  const columns: DataTableColumn<DataRecord>[] = [
    text('roll_number', 'Roll number'), text('student_name', 'Student'), text('examination_name', 'Examination'),
    { key: 'subjects', header: 'Subjects', render: (row) => (row.subjects as DataRecord[]).map((s) => String(s.subject_code)).join(', ') },
    dateCol('submitted_at', 'Submitted'), status('status'),
    { key: 'receipt', header: 'Fee receipt', render: (row) => row.has_fee_receipt ? <Button variant="ghost" size="sm" onClick={() => void downloadReceipt(row)}><Download className="h-3.5 w-3.5" /> Receipt</Button> : <span className="text-xs text-destructive">Missing</span> },
    { key: 'confirm', header: '', render: (row) => <Button variant="outline" size="sm" onClick={() => run(() => api.patch(`/admin/registrations/${String(row.id)}`, undefined, { params: { status: 'CONFIRMED' } }), refresh)}>Confirm</Button> },
    { key: 'cancel', header: '', render: (row) => <Button variant="ghost" size="sm" onClick={() => run(() => api.patch(`/admin/registrations/${String(row.id)}`, undefined, { params: { status: 'CANCELLED' } }), refresh)}>Cancel</Button> },
  ];
  return (
    <>
      <PageHeader eyebrow="Examination Admin" title="Examination Registrations" description="Review and confirm student registrations. Eligibility was validated by the backend at submission time." />
      <ErrorPanel error={registrations.error} onRetry={refresh} />
      <Card className="mb-5"><CardContent className="p-4"><Field label="Filter by examination"><Select value={examId} onChange={(e) => { setExamId(e.target.value); setPage(1); }}><option value="">All examinations</option>{(exams.data ?? []).map((exam) => <option key={String(exam.id)} value={String(exam.id)}>{String(exam.name)}</option>)}</Select></Field></CardContent></Card>
      <Card className="p-4">
        <DataTable columns={columns} data={registrations.data?.data.items ?? []} rowKey={(row) => String(row.id)} empty="No registrations found." />
        {registrations.data?.data && <div className="mt-4"><Pagination page={registrations.data.data.page} pages={registrations.data.data.pages} total={registrations.data.data.total} onChange={setPage} /></div>}
      </Card>
    </>
  );
}

export function AdminSchedules() {
  const schedules = useApiQuery<DataRecord[]>('admin-schedules', '/admin/schedules');
  const timetable = useApiQuery<DataRecord[]>('admin-timetable', '/admin/timetables');
  const exams = useApiQuery<DataRecord[]>('admin-examinations', '/admin/examinations');
  const subjects = useApiQuery<DataRecord[]>('admin-subjects', '/admin/subjects');
  const [form, setForm] = useState({ examination_id: '', subject_id: '', exam_date: '', start_time: '09:30', end_time: '12:30', session: 'FORENOON', venue: '' });
  const [busy, setBusy] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const refresh = () => { void schedules.refetch(); void timetable.refetch(); };

  const create = async () => {
    setBusy(true);
    await run(() => api.post('/admin/schedules', form), refresh);
    setBusy(false);
  };
  const download = async () => {
    setDownloading(true);
    try { await api.download('/admin/timetables/download', 'examination-timetable-admin.pdf'); toast.success('Downloaded'); }
    catch (error) { toast.error(error instanceof ApiError ? error.message : 'Download failed'); }
    finally { setDownloading(false); }
  };
  const columns: DataTableColumn<DataRecord>[] = [
    text('examination_name', 'Examination'), text('subject_code', 'Code'), text('subject_name', 'Subject'),
    { key: 'date', header: 'Date', render: (row) => formatDate(String(row.exam_date)) },
    { key: 'time', header: 'Time', render: (row) => `${formatTime(String(row.start_time))} – ${formatTime(String(row.end_time))}` },
    text('venue', 'Venue'), status('publication_status'),
  ];
  return (
    <>
      <PageHeader eyebrow="Examination Admin" title="Schedules & Timetable" description="Create exam schedules, publish them, then download the official PDF." actions={<Button variant="outline" onClick={download} loading={downloading}><Download className="h-4 w-4" /> Download PDF</Button>} />
      <ErrorPanel error={schedules.error ?? timetable.error} onRetry={refresh} />
      <Card className="mb-5"><CardContent className="p-4">
        <FormFields onSubmit={create} submitLabel="Create schedule" busy={busy}>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Field label="Examination"><Select value={form.examination_id} onChange={(e) => setForm({ ...form, examination_id: e.target.value })}><option value="">Select</option>{(exams.data ?? []).map((e) => <option key={String(e.id)} value={String(e.id)}>{String(e.name)}</option>)}</Select></Field>
            <Field label="Subject"><Select value={form.subject_id} onChange={(e) => setForm({ ...form, subject_id: e.target.value })}><option value="">Select</option>{(subjects.data ?? []).map((s) => <option key={String(s.id)} value={String(s.id)}>{String(s.subject_code)} — {String(s.subject_name)}</option>)}</Select></Field>
            <Field label="Date"><Input type="date" value={form.exam_date} onChange={(e) => setForm({ ...form, exam_date: e.target.value })} /></Field>
            <Field label="Start"><Input type="time" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} /></Field>
            <Field label="End"><Input type="time" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} /></Field>
            <Field label="Venue"><Input value={form.venue} onChange={(e) => setForm({ ...form, venue: e.target.value })} /></Field>
          </div>
        </FormFields>
        <div className="mt-4 flex justify-end"><Button variant="secondary" onClick={() => run(() => api.post('/admin/timetables/publish'), refresh)}><Send className="h-4 w-4" /> Publish all schedules</Button></div>
      </CardContent></Card>
      <DataTable columns={columns} data={timetable.data ?? []} rowKey={(row) => String(row.id)} empty="No schedule entries found." />
    </>
  );
}

export function AdminHallTickets() {
  const tickets = useApiQuery<DataRecord[]>('admin-hall-tickets', '/admin/hall-tickets');
  const exams = useApiQuery<DataRecord[]>('admin-examinations', '/admin/examinations');
  const [examId, setExamId] = useState('');
  const [busy, setBusy] = useState(false);
  const refresh = () => void tickets.refetch();
  const columns: DataTableColumn<DataRecord>[] = [
    text('ticket_number', 'Ticket number'), text('roll_number', 'Roll number'), text('student_name', 'Student'),
    text('examination_name', 'Examination'), dateCol('issued_at', 'Issued'), status('is_valid', 'Validity'),
    action('regenerate', 'Regenerate', (row) => run(() => api.post(`/admin/hall-tickets/${String(row.id)}/regenerate`), refresh)),
  ];
  return (
    <>
      <PageHeader eyebrow="Examination Admin" title="Hall Tickets" description="Generate tickets for submitted registrations and invalidate older copies by regeneration." />
      <ErrorPanel error={tickets.error ?? exams.error} onRetry={refresh} />
      <Card className="mb-5"><CardContent className="p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <Field label="Examination" className="flex-1"><Select value={examId} onChange={(e) => setExamId(e.target.value)}><option value="">Select examination</option>{(exams.data ?? []).map((e) => <option key={String(e.id)} value={String(e.id)}>{String(e.name)}</option>)}</Select></Field>
          <Button disabled={!examId} loading={busy} onClick={async () => { setBusy(true); await run(() => api.post('/admin/hall-tickets/generate', undefined, { params: { examination_id: examId } }), refresh); setBusy(false); }}>Generate tickets</Button>
        </div>
      </CardContent></Card>
      <DataTable columns={columns} data={tickets.data ?? []} rowKey={(row) => String(row.id)} empty="No hall tickets generated yet." />
    </>
  );
}

export function AdminNotifications() {
  const notifications = useApiQuery<DataRecord[]>('admin-notifications', '/admin/notifications');
  const [form, setForm] = useState({ title: '', message: '', category: 'GENERAL', publish: true });
  const [busy, setBusy] = useState(false);
  const refresh = () => void notifications.refetch();
  const publish = async () => {
    setBusy(true);
    await run(() => api.post('/admin/notifications', form), refresh);
    setBusy(false);
  };
  return (
    <>
      <PageHeader eyebrow="Examination Admin" title="Notification Composer" description="Publish institutional announcements. Recipients are resolved by the backend from notification rules." />
      <ErrorPanel error={notifications.error} onRetry={refresh} />
      <Card className="mb-5"><CardContent className="p-4">
        <FormFields onSubmit={publish} submitLabel="Publish notification" busy={busy}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Title"><Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
            <Field label="Category"><Select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>{['GENERAL', 'RESULT', 'BACKLOG', 'RECOUNTING', 'TIMETABLE', 'HALL_TICKET', 'MARKS_SUBMISSION', 'EXAM_REGISTRATION'].map((c) => <option key={c}>{c}</option>)}</Select></Field>
            <Field label="Publish immediately"><Select value={String(form.publish)} onChange={(e) => setForm({ ...form, publish: e.target.value === 'true' })}><option value="true">Yes</option><option value="false">No (draft)</option></Select></Field>
            <Field label="Message" className="sm:col-span-2"><Textarea value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} /></Field>
          </div>
        </FormFields>
      </CardContent></Card>
      <DataTable columns={[text('title', 'Title'), text('message', 'Message'), text('category', 'Category'), dateCol('created_at', 'Created')]} data={notifications.data ?? []} rowKey={(row) => String(row.id)} empty="No notifications published yet." />
    </>
  );
}

export function AdminMarksVerification() {
  const submissions = useApiQuery<DataRecord[]>('admin-marks-verification', '/admin/marks-verification');
  const refresh = () => void submissions.refetch();
  const update = (row: DataRecord, actionName: string) => run(() => api.post(`/admin/marks-verification/${String(row.id)}`, undefined, { params: { action: actionName } }), refresh);
  const columns: DataTableColumn<DataRecord>[] = [
    text('subject_code', 'Code'), text('subject_name', 'Subject'),
    dateCol('submitted_at', 'Submitted'), status('status'), text('review_note', 'Review note'),
    { key: 'actions', header: 'Actions', render: (row) => <div className="flex flex-wrap gap-2"><Button size="sm" variant="outline" onClick={() => update(row, 'approve')}>Verify</Button><Button size="sm" variant="outline" onClick={() => update(row, 'return')}>Return</Button><Button size="sm" onClick={() => update(row, 'lock')}><LockKeyhole className="h-3.5 w-3.5" /> Lock</Button></div> },
  ];
  return (
    <>
      <PageHeader eyebrow="Examination Admin" title="Marks Verification" description="Faculty submissions must be verified or locked before result processing can include them." />
      <ErrorPanel error={submissions.error} onRetry={refresh} />
      <DataTable columns={columns} data={submissions.data ?? []} rowKey={(row) => String(row.id)} empty="No marks submissions awaiting review." />
    </>
  );
}

export function AdminMarksManagement() {
  const [tab, setTab] = useState('internal');
  const [studentFilter, setStudentFilter] = useState('');
  const [subjectFilter, setSubjectFilter] = useState('');
  const marks = useApiQuery<{ internal: DataRecord[]; external: DataRecord[] }>(
    'admin-marks-management',
    '/admin/marks-management',
    { student_id: studentFilter || undefined, subject_id: subjectFilter || undefined },
  );
  const [form, setForm] = useState({ student_id: '', subject_id: '', examination_id: '', marks_obtained: 0 });
  const exams = useApiQuery<DataRecord[]>('admin-examinations', '/admin/examinations');
  const [busy, setBusy] = useState(false);
  const [csvExamId, setCsvExamId] = useState('');
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<DataRecord | null>(null);
  const [importResult, setImportResult] = useState<DataRecord | null>(null);
  const [overwrite, setOverwrite] = useState(false);
  const [csvBusy, setCsvBusy] = useState(false);
  const refresh = () => void marks.refetch();

  const save = async () => {
    setBusy(true);
    await run(() => api.post('/admin/marks-management/external', [{ ...form, marks_obtained: Number(form.marks_obtained) }]), refresh);
    setBusy(false);
  };

  const previewCsv = async () => {
    if (!csvExamId || !csvFile) {
      toast.error('Select an examination and choose a CSV file');
      return;
    }
    const data = new FormData();
    data.append('examination_id', csvExamId);
    data.append('file', csvFile);
    setCsvBusy(true);
    try {
      const response = await api.post<DataRecord>('/admin/result-processing/import', data);
      setPreview(response.data);
      setImportResult(null);
      toast.success(response.message);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not validate CSV');
    } finally {
      setCsvBusy(false);
    }
  };

  const confirmImport = async () => {
    if (!preview) return;
    setCsvBusy(true);
    try {
      const response = await api.post<DataRecord>(
        `/admin/result-processing/import/${String(preview.import_id)}/confirm`,
        undefined,
        { params: { overwrite } },
      );
      setImportResult(response.data);
      toast.success(response.message);
      refresh();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not confirm import');
    } finally {
      setCsvBusy(false);
    }
  };

  const resetImport = () => {
    setPreview(null);
    setImportResult(null);
    setCsvFile(null);
    setOverwrite(false);
  };

  const previewRows = (preview?.rows ?? []) as DataRecord[];
  const previewSummary = (preview?.summary ?? {}) as DataRecord;

  return (
    <>
      <PageHeader eyebrow="Examination Admin" title="Marks Management" description="Inspect internal marks, enter or import external marks. Imports are staged for review and never publish results automatically." />
      <ErrorPanel error={marks.error ?? exams.error} onRetry={() => { refresh(); void exams.refetch(); }} />
      <Card className="mb-5"><CardContent className="p-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Filter by student ID"><Input value={studentFilter} onChange={(e) => setStudentFilter(e.target.value)} placeholder="Optional UUID" /></Field>
          <Field label="Filter by subject ID"><Input value={subjectFilter} onChange={(e) => setSubjectFilter(e.target.value)} placeholder="Optional UUID" /></Field>
        </div>
      </CardContent></Card>
      <Tabs value={tab} onChange={setTab} items={[
        { value: 'internal', label: `Internal (${marks.data?.internal.length ?? 0})`, content: <DataTable columns={[text('roll_number', 'Roll no.'), text('student_name', 'Student'), text('subject_code', 'Subject'), text('subject_name', 'Subject name'), text('total_marks', 'Total'), text('max_marks', 'Max'), status('status')]} data={marks.data?.internal ?? []} rowKey={(row) => String(row.id)} empty="No internal marks recorded." compact /> },
        { value: 'external', label: `External (${marks.data?.external.length ?? 0})`, content: (
          <div className="space-y-5">
            <Card><CardContent className="p-4"><FormFields onSubmit={save} submitLabel="Save external marks" busy={busy}>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <Field label="Student ID"><Input value={form.student_id} onChange={(e) => setForm({ ...form, student_id: e.target.value })} placeholder="UUID" /></Field>
                <Field label="Subject ID"><Input value={form.subject_id} onChange={(e) => setForm({ ...form, subject_id: e.target.value })} placeholder="UUID" /></Field>
                <Field label="Examination"><Select value={form.examination_id} onChange={(e) => setForm({ ...form, examination_id: e.target.value })}><option value="">Select</option>{(exams.data ?? []).map((e) => <option key={String(e.id)} value={String(e.id)}>{String(e.name)}</option>)}</Select></Field>
                <Field label="Marks obtained"><Input type="number" min={0} value={form.marks_obtained} onChange={(e) => setForm({ ...form, marks_obtained: Number(e.target.value) })} /></Field>
              </div>
            </FormFields></CardContent></Card>
            <DataTable columns={[text('roll_number', 'Roll no.'), text('student_name', 'Student'), text('subject_code', 'Code'), text('subject_name', 'Subject'), text('examination_name', 'Examination'), text('academic_year_name', 'Year'), text('marks_obtained', 'Marks'), text('max_marks', 'Max'), dateCol('entered_at', 'Entered')]} data={marks.data?.external ?? []} rowKey={(row) => String(row.id)} empty="No external marks recorded." compact />
          </div>
        ) },
        { value: 'import', label: 'CSV import', content: (
          <div className="space-y-5">
            <Alert variant="info" title="Two-phase import">
              Upload a UTF-8 CSV with columns <strong>rollno,subcode,marks</strong>. Enter external marks out of 70. The file is validated and staged in the database first. Nothing is written until you review the preview and confirm.
            </Alert>
            <Card><CardContent className="p-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Examination"><Select value={csvExamId} onChange={(e) => { setCsvExamId(e.target.value); resetImport(); }}><option value="">Select examination</option>{(exams.data ?? []).map((e) => <option key={String(e.id)} value={String(e.id)}>{String(e.name)}</option>)}</Select></Field>
                <Field label="CSV file"><Input type="file" accept=".csv,text/csv" onChange={(e) => { setCsvFile(e.target.files?.[0] ?? null); setPreview(null); setImportResult(null); }} /></Field>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button onClick={() => void previewCsv()} loading={csvBusy} disabled={!csvExamId || !csvFile}>Validate &amp; preview</Button>
                <Button variant="outline" onClick={resetImport} disabled={!csvFile && !preview}>Clear</Button>
              </div>
              <p className="mt-2 font-mono text-xs text-muted-foreground">rollno,subcode,marks<br />21CS001,CS301,52</p>
            </CardContent></Card>
            {preview && (
              <Card><CardContent className="space-y-4 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="font-semibold">{String(preview.filename)}</h2>
                    <p className="text-xs text-muted-foreground">{String(preview.examination_name)} · Total {String(previewSummary.total ?? 0)} · Valid {String(previewSummary.valid ?? 0)} · Invalid {String(previewSummary.invalid ?? 0)} · Existing {String(previewSummary.skipped ?? 0)}</p>
                  </div>
                  <Badge variant={importResult ? 'success' : 'warning'}>{importResult ? 'CONFIRMED' : 'PENDING CONFIRMATION'}</Badge>
                </div>
                <DataTable
                  columns={[
                    text('row', 'Row'), text('rollno', 'Roll no.'), text('subcode', 'Subject'), text('marks', 'Marks'),
                    text('student_name', 'Student'), text('subject_name', 'Subject name'), text('existing_marks', 'Existing'),
                    status('status'),
                    { key: 'errors', header: 'Validation', render: (row) => (row.errors as string[]).length ? <span className="text-xs text-destructive">{(row.errors as string[]).join('; ')}</span> : <span className="text-xs text-success">OK</span> },
                  ]}
                  data={previewRows}
                  rowKey={(row) => String(row.row)}
                  empty="No rows in preview."
                  compact
                />
                {!importResult && (
                  <div className="flex flex-wrap items-center justify-end gap-4">
                    <label className="flex items-center gap-2 text-sm">
                      <Checkbox checked={overwrite} onChange={(e) => setOverwrite(e.target.checked)} /> Overwrite existing marks
                    </label>
                    <Button onClick={() => void confirmImport()} loading={csvBusy}>Confirm import</Button>
                  </div>
                )}
                {importResult && (
                  <Alert variant="success" title="Import complete">
                    Applied {String(importResult.applied ?? 0)} · Skipped {String(importResult.skipped ?? 0)} · Failed {String((importResult.failed as unknown[] ?? []).length)}. Results were not published automatically.
                  </Alert>
                )}
              </CardContent></Card>
            )}
          </div>
        ) },
      ]} />
    </>
  );
}

export function AdminResults() {
  const navigate = useNavigate();
  const results = useApiQuery<DataRecord[]>('admin-results', '/admin/results');
  const exams = useApiQuery<DataRecord[]>('admin-examinations', '/admin/examinations');
  const [examId, setExamId] = useState('');
  const [busy, setBusy] = useState(false);
  const refresh = () => void results.refetch();

  const columns: DataTableColumn<DataRecord>[] = [
    text('roll_number', 'Roll number'), text('student_name', 'Student'), text('semester_number', 'Semester'),
    text('academic_year_name', 'Year'), text('sgpa', 'SGPA'), text('cgpa', 'CGPA'), text('subject_count', 'Subjects'),
    status('status'),
    { key: 'actions', header: 'Publication', render: (row) => {
      const state = String(row.status);
      return <div className="flex flex-wrap gap-2">
        {state === 'READY_FOR_REVIEW' && <Button size="sm" variant="outline" onClick={() => run(() => api.post(`/admin/result-publication/${String(row.id)}`, { action: 'approve' }), refresh)}><CheckCircle2 className="h-3.5 w-3.5" /> Approve</Button>}
        {state === 'APPROVED' && <Button size="sm" onClick={() => run(() => api.post(`/admin/result-publication/${String(row.id)}`, { action: 'publish' }), refresh)}><Send className="h-3.5 w-3.5" /> Publish</Button>}
        {state === 'PUBLISHED' && <Button size="sm" variant="outline" onClick={() => run(() => api.post(`/admin/result-publication/${String(row.id)}`, { action: 'unpublish' }), refresh)}>Unpublish</Button>}
      </div>;
    } },
  ];
  return (
    <>
      <PageHeader eyebrow="Examination Admin" title="Result Processing & Publication" description="Processing uses the central grading engine. Publication is a separate explicit approve → publish workflow." />
      <ErrorPanel error={results.error ?? exams.error} onRetry={refresh} />
      <Alert variant="info" title="External marks CSV" className="mb-5">
        Add a CSV containing <strong>rollno,subcode,marks</strong> with marks out of 70 before processing results.
        Each registered student also needs verified internal marks for every registered subject.
        <Button variant="link" size="sm" className="ml-2" onClick={() => navigate('/admin/marks-management')}>Open CSV import</Button>
      </Alert>
      <Card className="mb-5"><CardContent className="p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <Field label="Process examination results" className="flex-1"><Select value={examId} onChange={(e) => setExamId(e.target.value)}><option value="">Select examination</option>{(exams.data ?? []).map((e) => <option key={String(e.id)} value={String(e.id)}>{String(e.name)}</option>)}</Select></Field>
          <Button disabled={!examId} loading={busy} onClick={async () => { setBusy(true); await run(() => api.post('/admin/result-processing', { examination_id: examId }), refresh); setBusy(false); }}><PlayCircle className="h-4 w-4" /> Process results</Button>
        </div>
      </CardContent></Card>
      <DataTable columns={columns} data={results.data ?? []} rowKey={(row) => String(row.id)} empty="No semester results have been processed." />
    </>
  );
}

export function AdminPerformance() {
  const overview = useApiQuery<{ results: DataRecord[] }>('admin-performance', '/admin/sgpa-cgpa');
  return (
    <>
      <PageHeader eyebrow="Examination Admin" title="SGPA / CGPA Overview" description="Review server-calculated semester performance. Grading rules are fixed in the backend." />
      <ErrorPanel error={overview.error} onRetry={() => void overview.refetch()} />
      <Alert variant="info" title="Central grading">
        Grades are derived from the percentage of maximum marks: S &gt;90, A &gt;80, B ≥70, C &gt;60, D &gt;50, E ≥40, Fail &lt;40. A result at or above 40% passes.
      </Alert>
      <div className="h-4" />
      <Card className="p-4">
        <DataTable columns={[text('roll_number', 'Roll number'), text('semester', 'Semester'), text('sgpa', 'SGPA'), text('cgpa', 'CGPA'), status('status')]} data={overview.data?.results ?? []} rowKey={(row) => String(row.id)} empty="No calculated results." compact />
      </Card>
    </>
  );
}

export function AdminBacklogs() {
  const backlogs = useApiQuery<DataRecord[]>('admin-backlogs', '/admin/backlogs');
  const exams = useApiQuery<DataRecord[]>('admin-examinations', '/admin/examinations');
  const refresh = () => void backlogs.refetch();
  const columns: DataTableColumn<DataRecord>[] = [
    text('roll_number', 'Roll number'), text('student_name', 'Student'), text('subject_code', 'Subject'),
    text('semester_number', 'Semester'), text('attempts', 'Attempts'), text('credits', 'Credits'),
    { key: 'cleared', header: 'Status', render: (row) => <Badge variant={row.is_cleared ? 'success' : 'destructive'}>{row.is_cleared ? 'CLEARED' : 'ACTIVE'}</Badge> },
    { key: 'supplementary', header: 'Supplementary', render: (row) => <Select defaultValue={String(row.supplementary_exam_id ?? '')} onChange={(e) => run(() => api.patch(`/admin/backlogs/${String(row.id)}`, undefined, { params: { supplementary_exam_id: e.target.value || null } }), refresh)}><option value="">Not scheduled</option>{(exams.data ?? []).filter((e) => e.exam_type === 'SUPPLEMENTARY').map((e) => <option key={String(e.id)} value={String(e.id)}>{String(e.name)}</option>)}</Select> },
  ];
  return (
    <>
      <PageHeader eyebrow="Examination Admin" title="Backlog Management" description="Assign supplementary examinations to active backlogs. Students are notified separately." />
      <ErrorPanel error={backlogs.error ?? exams.error} onRetry={refresh} />
      <DataTable columns={columns} data={backlogs.data ?? []} rowKey={(row) => String(row.id)} empty="No backlogs recorded." />
    </>
  );
}

export function AdminRecounting() {
  const requests = useApiQuery<DataRecord[]>('admin-recounting', '/admin/recounting');
  const [active, setActive] = useState<DataRecord | null>(null);
  const [form, setForm] = useState({ action: 'processing', admin_response: '', revised_marks: '' });
  const [busy, setBusy] = useState(false);
  const refresh = () => void requests.refetch();
  const process = async () => {
    setBusy(true);
    await run(() => api.post(`/admin/recounting/${String(active?.id)}/process`, { action: form.action, admin_response: form.admin_response || null, revised_marks: form.revised_marks === '' ? null : Number(form.revised_marks) }), refresh);
    setBusy(false);
    setActive(null);
  };
  const columns: DataTableColumn<DataRecord>[] = [
    text('roll_number', 'Roll number'), text('student_name', 'Student'), text('subject_code', 'Subject'),
    text('original_marks', 'Original'), text('revised_marks', 'Revised'), dateCol('created_at', 'Submitted'),
    status('request_status'),
    { key: 'process', header: '', render: (row) => ['COMPLETED', 'REJECTED'].includes(String(row.request_status)) ? <span className="text-xs text-muted-foreground">Closed</span> : <Button variant="outline" size="sm" onClick={() => { setActive(row); setForm({ action: 'processing', admin_response: '', revised_marks: '' }); }}>Process</Button> },
  ];
  return (
    <>
      <PageHeader eyebrow="Examination Admin" title="Recounting Requests" description="Process requests and optionally revise marks. Revised totals reset the result to ready-for-review." />
      <ErrorPanel error={requests.error} onRetry={refresh} />
      <DataTable columns={columns} data={requests.data ?? []} rowKey={(row) => String(row.id)} empty="No recounting requests recorded." />
      <Modal open={Boolean(active)} onClose={() => setActive(null)} title="Process recounting request" description={active ? `${String(active.subject_code)} · ${String(active.roll_number)}` : undefined}>
        {active && <FormFields onSubmit={process} submitLabel="Save decision" busy={busy}>
          <Alert variant="info">{String(active.reason ?? 'No reason provided')}</Alert>
          <Field label="Decision"><Select value={form.action} onChange={(e) => setForm({ ...form, action: e.target.value })}><option value="pending_review">Pending review</option><option value="processing">Processing</option><option value="complete">Complete</option><option value="reject">Reject</option></Select></Field>
          <Field label="Revised total marks" hint="Leave blank if marks are unchanged"><Input type="number" min={0} value={form.revised_marks} onChange={(e) => setForm({ ...form, revised_marks: e.target.value })} /></Field>
          <Field label="Response"><Textarea value={form.admin_response} onChange={(e) => setForm({ ...form, admin_response: e.target.value })} /></Field>
        </FormFields>}
      </Modal>
    </>
  );
}

export function AdminPasswordReset() {
  const users = useApiQuery<PageType<DataRecord>>('admin-students', '/admin/students', { page_size: 200 });
  const faculty = useApiQuery<PageType<DataRecord>>('admin-faculty', '/admin/faculty', { page_size: 200 });
  const [userId, setUserId] = useState('');
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [token, setToken] = useState<DataRecord | null>(null);
  const allUsers = [...(users.data?.items ?? []), ...(faculty.data?.items ?? [])];

  const initiate = async () => {
    setBusy(true);
    try {
      const response = await api.post<DataRecord>('/admin/password-reset/initiate', { user_id: userId, reason: reason || null });
      setToken(response.data);
      toast.success(response.message);
    } catch (error) { toast.error(error instanceof ApiError ? error.message : 'Could not initiate reset'); }
    finally { setBusy(false); }
  };
  return (
    <>
      <PageHeader eyebrow="Examination Admin" title="Password Reset" description="Initiate a single-use, one-hour reset token for a student or faculty account." />
      <ErrorPanel error={users.error ?? faculty.error} onRetry={() => { void users.refetch(); void faculty.refetch(); }} />
      <Card className="mb-5"><CardContent className="p-4">
        <FormFields onSubmit={initiate} submitLabel="Generate reset token" busy={busy}>
          <Field label="Account"><Select value={userId} onChange={(e) => setUserId(e.target.value)}><option value="">Select student or faculty</option>{allUsers.map((u) => <option key={String(u.user_id)} value={String(u.user_id)}>{String(u.full_name)} · {String(u.email)}</option>)}</Select></Field>
          <Field label="Reason"><Textarea value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Optional audit note" /></Field>
        </FormFields>
      </CardContent></Card>
      {token && (
        <Card className="border-warning/30 bg-warning/5">
          <CardHeader><CardTitle className="flex items-center gap-2"><ShieldCheck className="h-5 w-5 text-warning" /> Reset token</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Alert variant="warning">{String(token.note)}</Alert>
            <p className="break-all font-mono text-xs">{String(token.reset_token ?? 'Not returned in production')}</p>
            <p className="text-muted-foreground">Expires: {formatDate(String(token.expires_at), true)}</p>
          </CardContent>
        </Card>
      )}
    </>
  );
}
