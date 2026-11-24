import type { ApiEnvelope } from './types';

/**
 * Explicit local demonstration adapter. It is used only when
 * VITE_API_MODE=mock. Live request failures never fall back to this module.
 */
const DEMO = {
  admin: { id: '10000000-0000-4000-8000-000000000001', email: 'admin@example.com', password: 'Admin@123' },
  faculty: { id: '20000000-0000-4000-8000-000000000002', email: 'faculty@example.com', password: 'Faculty@123' },
  student: { id: '30000000-0000-4000-8000-000000000003', email: 'student@example.com', password: 'Student@123' },
  student2: { id: '30000000-0000-4000-8000-000000000004', email: 'student2@example.com', password: 'Student@123' },
  tempstudent: { id: '30000000-0000-4000-8000-000000000005', email: 'tempstudent@example.com', password: 'Temp@123' },
};

const today = new Date();
const iso = (offsetDays: number) => new Date(today.getTime() + offsetDays * 86_400_000).toISOString();
const date = (offsetDays: number) => iso(offsetDays).slice(0, 10);
let tempPasswordChanged = false;
let csvImportPreview: Record<string, any> | null = null;

const academicYears = ['2023-24', '2024-25', '2025-26'].map((academic_year_name, index) => ({
  id: `50000000-0000-4000-8000-00000000000${index + 1}`,
  academic_year_name,
  status: 'ACTIVE',
}));

const courses = [
  { code: 'CSE', name: 'Computer Science & Engineering' },
  { code: 'ECE', name: 'Electronics & Communication Engineering' },
  { code: 'EEE', name: 'Electrical & Electronics Engineering' },
  { code: 'MECH', name: 'Mechanical Engineering' },
  { code: 'CIVIL', name: 'Civil Engineering' },
  { code: 'AI&ML', name: 'Artificial Intelligence & Machine Learning' },
].map((course, index) => ({
  id: `70000000-0000-4000-8000-00000000000${index + 1}`,
  course_code: course.code,
  course_name: course.name,
  duration_years: 4,
}));

const fixedComponents = { components: [
  { name: 'MID-1', max_marks: 25 },
  { name: 'MID-2', max_marks: 25 },
  { name: 'Assignments', max_marks: 5 },
] };

const exams = [
  {
    id: '40000000-0000-4000-8000-000000000001',
    name: 'Regular Semester III - 2025-26',
    exam_type: 'REGULAR',
    registration_start: iso(-10),
    registration_deadline: iso(20),
    status: 'OPEN',
    subject_count: 3,
    eligible: true,
    eligibility_reason: 'Eligible',
    registered: true,
    registration_id: 'b0000000-0000-4000-8000-000000000001',
    academic_year_id: academicYears[2].id,
    semester_id: '50000000-0000-4000-8000-000000000103',
  },
  {
    id: '40000000-0000-4000-8000-000000000002',
    name: 'Supplementary Semester I - 2025-26',
    exam_type: 'SUPPLEMENTARY',
    registration_start: iso(-30),
    registration_deadline: iso(-2),
    status: 'CLOSED',
    subject_count: 2,
    eligible: false,
    eligibility_reason: 'Registration deadline has passed',
    registered: false,
    registration_id: null,
  },
];

const subjects = [
  { code: 'CS301', name: 'Data Structures', credits: 4 },
  { code: 'CS302', name: 'Operating Systems', credits: 3 },
  { code: 'CS303', name: 'Database Management Systems', credits: 3 },
].map((subject, index) => ({
  id: `60000000-0000-4000-8000-00000000000${index + 1}`,
  subject_code: subject.code,
  subject_name: subject.name,
  course_id: courses[0].id,
  semester_id: exams[0].semester_id,
  credits: subject.credits,
  internal_max_marks: 30,
  external_max_marks: 70,
  subject_type: 'THEORY',
  assessment_configuration: fixedComponents,
}));

const studentProfile = {
  id: '80000000-0000-4000-8000-000000000001', user_id: DEMO.student.id, roll_number: '21CS001',
  full_name: 'Arjun Kumar', email: DEMO.student.email, department: 'Computer Science & Engineering',
  branch: 'Computer Science & Engineering', current_semester: 3, academic_year: '2025-26',
  admission_year: '2023-24', enrollment_status: 'ACTIVE', section: 'A',
};

const facultyProfile = {
  id: '90000000-0000-4000-8000-000000000001', user_id: DEMO.faculty.id,
  faculty_id: 'FAC001', full_name: 'Dr. Anita Sharma', email: DEMO.faculty.email,
  department: 'Computer Science & Engineering', designation: 'Associate Professor',
  account_status: 'ACTIVE', assigned_subjects: subjects.map((s) => ({
    id: s.id, subject_code: s.subject_code, subject_name: s.subject_name, section: 'A',
  })),
};

const assignments = subjects.map((subject, index) => ({
  id: `a0000000-0000-4000-8000-00000000000${index + 1}`,
  faculty_id: facultyProfile.id, subject_id: subject.id, subject_code: subject.subject_code,
  subject_name: subject.subject_name, credits: subject.credits, section: 'A',
  internal_max_marks: subject.internal_max_marks, external_max_marks: subject.external_max_marks,
  assessment_configuration: fixedComponents,
  assignment_status: 'ACTIVE',
}));

const facultyStudents = [
  { id: studentProfile.id, roll_number: '21CS001', full_name: 'Arjun Kumar', email: DEMO.student.email, branch: 'CSE', semester: 3, section: 'A' },
  { id: '80000000-0000-4000-8000-000000000002', roll_number: '21CS002', full_name: 'Priya Singh', email: DEMO.student2.email, branch: 'CSE', semester: 3, section: 'A' },
];

const registrations = [{
  id: 'b0000000-0000-4000-8000-000000000001', examination_id: exams[0].id,
  examination_name: exams[0].name, exam_type: 'REGULAR', student_id: studentProfile.id,
  status: 'CONFIRMED', submitted_at: iso(-2),
  fee_receipt_filename: 'SBI-Collect-Receipt-21CS001.pdf',
  fee_receipt_uploaded_at: iso(-2),
  has_fee_receipt: true,
  subjects: subjects.map((s) => ({ subject_id: s.id, subject_code: s.subject_code, subject_name: s.subject_name, credits: s.credits })),
}];

const timetable = subjects.map((subject, index) => ({
  id: `c0000000-0000-4000-8000-00000000000${index + 1}`, examination_id: exams[0].id,
  examination_name: exams[0].name, exam_type: 'REGULAR', subject_id: subject.id,
  subject_code: subject.subject_code, subject_name: subject.subject_name,
  exam_date: date(30 + index * 2), start_time: '09:30', end_time: '12:30',
  session: 'FORENOON', venue: `Room A-${101 + index}`, publication_status: 'PUBLISHED',
}));

const hallTickets = [{
  id: 'd0000000-0000-4000-8000-000000000001', ticket_number: 'HT-REG-DEMO001',
  examination_id: exams[0].id, examination_name: exams[0].name, exam_type: 'REGULAR',
  issued_at: iso(-1), is_valid: true,
}];

const internalMarks = subjects.map((subject, index) => ({
  id: `e0000000-0000-4000-8000-00000000000${index + 1}`, student_id: studentProfile.id,
  student_name: studentProfile.full_name, roll_number: studentProfile.roll_number,
  subject_id: subject.id, subject_code: subject.subject_code, subject_name: subject.subject_name,
  examination_id: exams[0].id,
  component_marks: { 'MID-1': 20, 'MID-2': 24, Assignments: 4 },
  mid1_marks: 20, mid2_marks: 24, assignments_marks: 4,
  total_marks: 27.2, max_marks: 30, status: 'VERIFIED', submitted_at: iso(-4),
}));

const externalMarks = subjects.map((subject, index) => ({
  id: `e1000000-0000-4000-8000-00000000000${index + 1}`,
  student_id: studentProfile.id,
  student_name: studentProfile.full_name,
  roll_number: studentProfile.roll_number,
  subject_id: subject.id,
  subject_code: subject.subject_code,
  subject_name: subject.subject_name,
  examination_id: exams[0].id,
  examination_name: exams[0].name,
  academic_year_name: '2025-26',
  marks_obtained: index === 1 ? 45 : 52,
  max_marks: 70,
  entered_at: iso(-3),
}));

const gradeFor = (percentage: number) => {
  if (percentage > 90) return { grade: 'S', grade_point: 10 };
  if (percentage > 80) return { grade: 'A', grade_point: 9 };
  if (percentage >= 70) return { grade: 'B', grade_point: 8 };
  if (percentage > 60) return { grade: 'C', grade_point: 7 };
  if (percentage > 50) return { grade: 'D', grade_point: 6 };
  if (percentage >= 40) return { grade: 'E', grade_point: 5 };
  return { grade: 'Fail', grade_point: 0 };
};

const subjectResults = subjects.map((subject, index) => {
  const external = index === 1 ? 45 : 52;
  const total = 27.2 + external;
  const band = gradeFor(total);
  return {
    id: `f0000000-0000-4000-8000-00000000000${index + 1}`, subject_id: subject.id,
    subject_code: subject.subject_code, subject_name: subject.subject_name, credits: subject.credits,
    internal_marks: 27.2, external_marks: external, total_marks: total,
    max_marks: 100, grade: band.grade, grade_point: band.grade_point,
    result_status: total >= 40 ? 'PASS' : 'FAIL',
  };
});

const results = [{
  id: 'g0000000-0000-4000-8000-000000000001', student_id: studentProfile.id,
  examination_id: exams[0].id, examination_name: exams[0].name,
  roll_number: studentProfile.roll_number, student_name: studentProfile.full_name,
  semester_number: 3, academic_year_name: '2025-26', sgpa: 7.42, cgpa: 7.42,
  total_credits: 10, earned_credits: 10, status: 'PUBLISHED', published_at: iso(-3),
  subject_results: subjectResults,
}];

const performance = {
  semesters: [
    { semester: 1, academic_year: '2023-24', sgpa: 6.8, cgpa: 6.8, status: 'PUBLISHED' },
    { semester: 2, academic_year: '2024-25', sgpa: 7.1, cgpa: 6.95, status: 'PUBLISHED' },
    { semester: 3, academic_year: '2025-26', sgpa: 7.42, cgpa: 7.11, status: 'PUBLISHED' },
  ],
  current_cgpa: 7.11,
};

const backlogs = [{
  id: 'h0000000-0000-4000-8000-000000000001', subject_id: subjects[1].id,
  subject_code: 'CS302', subject_name: 'Operating Systems', credits: 3,
  semester_number: 3, academic_year_name: '2025-26', attempts: 1,
  is_cleared: false, supplementary_exam_id: null,
}];

const recounting = [{
  id: 'i0000000-0000-4000-8000-000000000001', student_id: studentProfile.id,
  examination_id: exams[0].id, examination_name: exams[0].name, subject_id: subjects[0].id,
  subject_code: 'CS301', subject_name: 'Data Structures', original_marks: 79.2,
  reason: 'Please recheck the external marks total.', request_status: 'COMPLETED',
  admin_response: 'Recount verified. No change required.', revised_marks: 79.2, created_at: iso(-2),
}];

const corrections = [{
  id: 'j0000000-0000-4000-8000-000000000001', student_id: studentProfile.id,
  student_name: studentProfile.full_name, roll_number: studentProfile.roll_number,
  subject_id: subjects[0].id, subject_code: 'CS301', subject_name: 'Data Structures',
  reported_marks: 27.2, suggested_marks: 28.2,
  explanation: 'The assignments total appears to be one mark short.',
  request_status: 'RESOLVED', faculty_response: 'Verified and corrected.', created_at: iso(-5),
}];

const notifications = [
  { id: 'k0000000-0000-4000-8000-000000000001', title: 'Semester III result published', message: 'Your Semester III result is now available.', category: 'RESULT', created_at: iso(-3), read: false },
  { id: 'k0000000-0000-4000-8000-000000000002', title: 'Internal marks submitted', message: 'Marks for CS301 were submitted for verification.', category: 'MARKS_SUBMISSION', created_at: iso(-5), read: true },
  { id: 'k0000000-0000-4000-8000-000000000003', title: 'Examination registration open', message: 'Register for Regular Semester III before the deadline.', category: 'EXAM_REGISTRATION', created_at: iso(-10), read: true },
];

const adminStudents = [
  studentProfile,
  { ...studentProfile, id: '80000000-0000-4000-8000-000000000002', user_id: DEMO.student2.id, roll_number: '21CS002', full_name: 'Priya Singh', email: DEMO.student2.email },
  { ...studentProfile, id: '80000000-0000-4000-8000-000000000003', user_id: DEMO.tempstudent.id, roll_number: '21CS003', full_name: 'Temporary Student', email: DEMO.tempstudent.email },
];

const adminFaculty = [facultyProfile];

const regulations = [{
  id: '70000000-0000-4000-8000-000000000009',
  regulation_name: 'DEMO-2023',
  effective_year: '2023',
}];

const dashboard = {
  total_students: adminStudents.length, total_faculty: 1, active_examinations: 1, total_registrations: registrations.length,
  pending_marks_submissions: 0, pending_marks_verification: 0, pending_corrections: 0,
  results_awaiting_processing: 0, pending_recounting: 0,
  upcoming_examinations: exams.slice(0, 2).map((e) => ({ id: e.id, name: e.name, exam_type: e.exam_type, registration_deadline: e.registration_deadline })),
  recent_activity: [
    { id: '1', action: 'RESULT_PUBLISH', entity_type: 'SemesterResult', created_at: iso(-3) },
    { id: '2', action: 'EXAM_REGISTRATION_SUBMITTED', entity_type: 'ExaminationRegistration', created_at: iso(-4) },
  ],
};

const page = <T,>(items: T[], params: Record<string, any> = {}) => {
  const current = Number(params.page ?? 1);
  const size = Number(params.page_size ?? 20);
  return {
    items: items.slice((current - 1) * size, current * size),
    total: items.length,
    page: current,
    page_size: size,
    pages: Math.max(1, Math.ceil(items.length / size)),
  };
};

const envelope = <T,>(data: T, message = 'OK'): ApiEnvelope<T> => ({ success: true, message, data });

const field = (body: any, key: string): any => {
  if (body instanceof FormData) return body.get(key);
  return body?.[key];
};

function userForToken(token?: string | null) {
  if (token?.includes('admin')) return 'admin';
  if (token?.includes('faculty')) return 'faculty';
  if (token?.includes('tempstudent')) return 'tempstudent';
  return 'student';
}

function authUser(role: string) {
  if (role === 'admin') return {
    id: DEMO.admin.id, email: DEMO.admin.email, full_name: 'Examination Administrator',
    role: 'EXAM_ADMIN', account_status: 'ACTIVE', student_id: null, faculty_id: null,
    must_change_password: false,
  };
  if (role === 'faculty') return {
    id: DEMO.faculty.id, email: DEMO.faculty.email, full_name: facultyProfile.full_name,
    role: 'FACULTY', account_status: 'ACTIVE', faculty_id: facultyProfile.id,
    department: facultyProfile.department, must_change_password: false,
  };
  if (role === 'tempstudent') return {
    id: DEMO.tempstudent.id, email: DEMO.tempstudent.email, full_name: 'Temporary Student',
    role: 'STUDENT', account_status: 'ACTIVE', student_id: adminStudents[2].id,
    roll_number: '21CS003', department: 'Computer Science & Engineering',
    branch: 'Computer Science & Engineering', semester: 3, academic_year: '2025-26',
    must_change_password: !tempPasswordChanged,
  };
  return {
    id: DEMO.student.id, email: DEMO.student.email, full_name: studentProfile.full_name,
    role: 'STUDENT', account_status: 'ACTIVE', student_id: studentProfile.id,
    roll_number: studentProfile.roll_number, department: studentProfile.department,
    branch: studentProfile.branch, semester: 3, academic_year: '2025-26',
    must_change_password: false,
  };
}

export function mockRequest<T>(
  method: string,
  path: string,
  body: any,
  params: Record<string, any> = {},
  token?: string | null,
): ApiEnvelope<T> {
  const p = path.replace(/^\/+/, '');
  const role = userForToken(token);
  const created = { id: crypto.randomUUID() };

  if (p === 'auth/login') {
    const account = Object.values(DEMO).find((item) => item.email === String(field(body, 'email') ?? '').toLowerCase());
    if (!account || account.password !== field(body, 'password')) {
      return { success: false, message: 'Invalid email or password', data: null as T, code: 'unauthorized' };
    }
    const key = Object.keys(DEMO).find((k) => DEMO[k as keyof typeof DEMO] === account) ?? 'student';
    return envelope({ access_token: `mock.${key}.token`, token_type: 'bearer', expires_in: 1800, user: authUser(key) } as T, 'Login successful');
  }
  if (p === 'auth/change-password') {
    tempPasswordChanged = true;
    return envelope({} as T, 'Password changed successfully');
  }
  if (p === 'auth/refresh') return envelope({ access_token: `mock.${role}.token`, token_type: 'bearer', expires_in: 1800, user: authUser(role) } as T, 'Token refreshed');
  if (p === 'auth/me') return envelope(authUser(role) as T, 'Current user');
  if (p === 'auth/logout' || p === 'auth/forgot-password' || p === 'auth/reset-password') return envelope({} as T, 'Operation completed');

  if (p === 'students/me') return envelope(studentProfile as T, 'Student profile');
  if (p === 'students/me/examinations') return envelope(exams as T, 'Eligible examinations');
  if (p.startsWith('students/me/examinations/') && p.endsWith('/subjects')) {
    return envelope(subjects.map((s) => ({ ...s, subject_id: s.id, already_registered: false })) as T, 'Eligible subjects');
  }
  if (p === 'students/me/registrations') {
    if (method === 'POST') {
      return envelope({ ...created, has_fee_receipt: true, fee_receipt_filename: String(field(body, 'fee_receipt')?.name ?? 'SBI-Collect-Receipt.pdf') } as T, 'Registration submitted with SBI Collect fee receipt');
    }
    return envelope(registrations as T, 'Registration history');
  }
  if (p.startsWith('students/me/registrations/') && p.endsWith('/receipt')) return envelope({ filename: registrations[0].fee_receipt_filename } as T, 'Fee receipt');
  if (p === 'students/me/timetable') return envelope(timetable as T, 'Published timetable');
  if (p === 'students/me/hall-tickets') return envelope(hallTickets as T, 'Hall tickets');
  if (p.startsWith('students/me/hall-tickets/')) return envelope({ ...hallTickets[0], institution_name: 'JNTUA College Of Engineering Pulivendula', student_name: studentProfile.full_name, roll_number: studentProfile.roll_number, subjects: timetable } as T, 'Hall ticket preview');
  if (p === 'students/me/internal-marks') return envelope(internalMarks as T, 'Internal marks');
  if (p === 'students/me/results') return envelope(results as T, 'Published results');
  if (p.startsWith('students/me/results/')) return envelope(results[0] as T, 'Result detail');
  if (p === 'students/me/sgpa-cgpa') return envelope(performance as T, 'Academic performance');
  if (p === 'students/me/backlogs') return envelope(backlogs as T, 'Backlogs');
  if (p === 'students/me/recounting-requests') return method === 'POST' ? envelope(created as T, 'Recounting request submitted') : envelope(recounting as T, 'Recounting requests');
  if (p === 'students/me/mark-correction-requests') return method === 'POST' ? envelope(created as T, 'Marks correction request submitted') : envelope(corrections as T, 'Correction requests');
  if (p === 'students/me/profile') return envelope(studentProfile as T, 'Profile updated');

  if (p === 'faculty/me') return envelope(facultyProfile as T, 'Faculty profile');
  if (p === 'faculty/me/assignments') return envelope(assignments as T, 'Assigned subjects');
  if (p === 'faculty/me/classes') return envelope([{ section: 'A', student_count: facultyStudents.length, subject_ids: subjects.map((s) => s.id) }] as T, 'Assigned classes');
  if (p === 'faculty/me/students') return envelope(page(facultyStudents, params) as T, 'Assigned students');
  if (p === 'faculty/me/internal-marks') return method === 'POST' ? envelope({ saved: 1, formula: 'best_mid*0.8 + other_mid*0.2 + assignments' } as T, 'Marks saved') : envelope(internalMarks as T, 'Internal marks');
  if (p === 'faculty/me/marks-submissions') return method === 'POST' ? envelope({ id: crypto.randomUUID() } as T, 'Marks submitted') : envelope([{ id: 'l0000000-0000-4000-8000-000000000001', subject_code: 'CS301', subject_name: 'Data Structures', status: 'SUBMITTED', submitted_at: iso(-1) }] as T, 'Marks submissions');
  if (p === 'faculty/me/correction-requests') return envelope(corrections as T, 'Correction requests');
  if (p.startsWith('faculty/me/correction-requests/')) return envelope({ ...created, status: 'RESOLVED' } as T, 'Request updated');
  if (p === 'faculty/me/timetable') return envelope(timetable as T, 'Published timetable');

  if (p === 'notifications/unread-count') return envelope({ count: notifications.filter((n) => !n.read).length } as T, 'Unread notification count');
  if (p === 'notifications/mark-all-read' || /^notifications\/[^/]+\/read$/.test(p)) return envelope({} as T, 'Notifications updated');
  if (p === 'notifications' || p.endsWith('/notifications')) return envelope(page(notifications, params) as T, 'Notifications');

  if (p === 'admin/dashboard') return envelope(dashboard as T, 'Examination administration dashboard');
  if (p === 'admin/students') return method === 'POST' ? envelope(created as T, 'Student created') : envelope(page(adminStudents, params) as T, 'Students');
  if (p === 'admin/faculty') return method === 'POST' ? envelope(created as T, 'Faculty member created') : envelope(page(adminFaculty, params) as T, 'Faculty');
  if (p.startsWith('admin/students/') || p.startsWith('admin/faculty/')) return envelope({} as T, 'Updated');
  if (p === 'admin/academic-years') return method === 'POST' ? envelope(created as T, 'Academic year created') : envelope(academicYears as T, 'Academic years');
  if (p === 'admin/semesters') return envelope([{ id: exams[0].semester_id, semester_number: 3 }] as T, 'Semesters');
  if (p === 'admin/regulations') return method === 'POST' ? envelope(created as T, 'Regulation created') : envelope(regulations as T, 'Regulations');
  if (p === 'admin/courses') return method === 'POST' ? envelope(created as T, 'Course created') : envelope(courses as T, 'Courses');
  if (p === 'admin/subjects') return method === 'POST' ? envelope(created as T, 'Subject created') : envelope(subjects as T, 'Subjects');
  if (p.startsWith('admin/subjects/')) return envelope({} as T, 'Subject updated');
  if (p === 'admin/faculty-assignments') return method === 'POST' ? envelope(created as T, 'Faculty assigned') : envelope(assignments as T, 'Faculty assignments');
  if (p.startsWith('admin/faculty-assignments/')) return envelope({} as T, 'Assignment updated');
  if (p === 'admin/examinations') return method === 'POST' ? envelope(created as T, 'Examination created') : envelope(exams as T, 'Examinations');
  if (p.startsWith('admin/examinations/')) return envelope(exams[0] as T, 'Examination');
  if (p === 'admin/registrations') return envelope(page(registrations, params) as T, 'Registrations');
  if (p.startsWith('admin/registrations/') && p.endsWith('/receipt')) return envelope({ filename: registrations[0].fee_receipt_filename } as T, 'Fee receipt');
  if (p.startsWith('admin/registrations/')) return envelope({} as T, 'Registration updated');
  if (p === 'admin/schedules' || p === 'admin/timetables') return envelope(timetable as T, 'Timetable');
  if (p === 'admin/timetables/publish') return envelope({ published: timetable.length } as T, 'Timetable published');
  if (p === 'admin/hall-tickets') return envelope(hallTickets as T, 'Hall tickets');
  if (p.startsWith('admin/hall-tickets/')) return envelope({ ticket_number: 'HT-REG-DEMO001' } as T, 'Hall ticket regenerated');
  if (p === 'admin/marks-verification') return envelope([{ id: 'm0000000-0000-4000-8000-000000000001', subject_code: 'CS301', subject_name: 'Data Structures', status: 'SUBMITTED', submitted_at: iso(-1), mark_count: 2 }] as T, 'Marks verification');
  if (p.startsWith('admin/marks-verification/')) return envelope({ status: 'VERIFIED' } as T, 'Marks submission updated');
  if (p === 'admin/marks-management') return envelope({ internal: internalMarks, external: externalMarks } as T, 'Marks management');
  if (p === 'admin/marks-management/external') return envelope({ saved: 1 } as T, 'External marks saved');
  if (p === 'admin/result-processing/import') {
    const rows = [
      { row: 2, rollno: '21CS001', subcode: 'CS301', marks: 52, student_id: studentProfile.id, subject_id: subjects[0].id, student_name: studentProfile.full_name, subject_name: subjects[0].subject_name, max_marks: 70, status: 'valid', errors: [], existing_marks: null },
      { row: 3, rollno: '21CS002', subcode: 'CS302', marks: 45, student_id: '80000000-0000-4000-8000-000000000002', subject_id: subjects[1].id, student_name: 'Priya Singh', subject_name: subjects[1].subject_name, max_marks: 70, status: 'valid', errors: [], existing_marks: null },
      { row: 4, rollno: '99CS999', subcode: 'CS303', marks: 52, student_id: null, subject_id: subjects[2].id, student_name: null, subject_name: subjects[2].subject_name, max_marks: 70, status: 'invalid', errors: ["roll number '99CS999' does not exist"], existing_marks: null },
    ];
    const summary = { total: 3, valid: 2, invalid: 1, skipped: 0 };
    csvImportPreview = {
      import_id: crypto.randomUUID(),
      examination_id: exams[0].id,
      examination_name: exams[0].name,
      filename: String(field(body, 'file')?.name ?? 'external-marks.csv'),
      rows,
      summary,
    };
    return envelope(csvImportPreview as T, 'CSV validated — review the preview before confirming');
  }
  if (p.startsWith('admin/result-processing/import/') && p.endsWith('/confirm')) {
    const applied = csvImportPreview?.summary?.valid ?? 0;
    return envelope({ import_id: csvImportPreview?.import_id, applied, skipped: 0, failed: [], summary: { ...csvImportPreview?.summary, applied, skipped: 0, failed: 0 } } as T, 'External marks imported. Results are not published automatically.');
  }
  if (p === 'admin/result-processing') return envelope({ processed: 1, result_ids: [results[0].id], errors: [] } as T, 'Results processed using central grading');
  if (p === 'admin/results') return envelope(results as T, 'Semester results');
  if (p.startsWith('admin/result-publication/')) return envelope({ status: 'PUBLISHED' } as T, 'Result publication updated');
  if (p === 'admin/sgpa-cgpa') return envelope({ results: results.map((r) => ({ id: r.id, student_id: r.student_id, roll_number: r.roll_number, semester: r.semester_number, sgpa: r.sgpa, cgpa: r.cgpa, status: r.status })) } as T, 'SGPA / CGPA overview');
  if (p === 'admin/backlogs') return envelope(backlogs as T, 'Backlogs');
  if (p.startsWith('admin/backlogs/')) return envelope({} as T, 'Backlog updated');
  if (p === 'admin/recounting') return envelope(recounting as T, 'Recounting requests');
  if (p.startsWith('admin/recounting/')) return envelope({ status: 'COMPLETED' } as T, 'Recounting request updated');
  if (p === 'admin/notifications') return method === 'POST' ? envelope(created as T, 'Notification published') : envelope(notifications as T, 'Notifications');
  if (p === 'admin/password-reset/initiate') return envelope({ reset_token: 'mock-reset-token', expires_at: iso(0), user_id: DEMO.student.id, note: 'Local demo only' } as T, 'Password reset initiated');

  return envelope({} as T, `Mock response for ${method} ${p}`);
}

export function mockDownload(): Blob {
  return new Blob(['%PDF-1.4\n% Mock document — not a valid PDF\n'], { type: 'application/pdf' });
}
