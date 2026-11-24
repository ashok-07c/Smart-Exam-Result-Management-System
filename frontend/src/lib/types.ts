export type Role = 'STUDENT' | 'FACULTY' | 'EXAM_ADMIN';
export type ID = string;
export type DataRecord = Record<string, any>;

export interface ApiErrorItem {
  field?: string;
  message?: string;
}

export interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
  errors?: ApiErrorItem[];
  code?: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface AuthUser {
  id: ID;
  email: string;
  full_name: string;
  role: Role;
  account_status: string;
  student_id?: ID | null;
  faculty_id?: ID | null;
  roll_number?: string | null;
  department?: string | null;
  branch?: string | null;
  semester?: number | null;
  academic_year?: string | null;
  must_change_password?: boolean;
}

export interface LoginData {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export interface StudentProfile {
  id: ID;
  user_id: ID;
  roll_number: string;
  full_name: string;
  email: string;
  department?: string | null;
  branch?: string | null;
  current_semester: number;
  academic_year: string;
  admission_year: string;
  enrollment_status: string;
  section?: string | null;
}

export interface Examination {
  id: ID;
  name: string;
  exam_type: 'REGULAR' | 'SUPPLEMENTARY';
  registration_start: string;
  registration_deadline: string;
  status: string;
  subject_count?: number;
  eligible?: boolean;
  eligibility_reason?: string;
  registered?: boolean;
  registration_id?: ID | null;
}

export interface EligibleSubject {
  subject_id: ID;
  subject_code: string;
  subject_name: string;
  credits: number;
  internal_max_marks: number;
  external_max_marks: number;
  already_registered?: boolean;
}

export interface Registration {
  id: ID;
  examination_id: ID;
  examination_name: string;
  exam_type: string;
  status: string;
  submitted_at?: string | null;
  fee_receipt_filename?: string | null;
  fee_receipt_uploaded_at?: string | null;
  has_fee_receipt?: boolean;
  subjects: Array<{ subject_id: ID; subject_code: string; subject_name: string; credits: number }>;
}

export interface ScheduleItem {
  id: ID;
  examination_name?: string;
  exam_type?: string;
  subject_code: string;
  subject_name: string;
  exam_date: string;
  start_time: string;
  end_time: string;
  session?: string | null;
  venue?: string | null;
  publication_status?: string;
}

export interface HallTicket {
  id: ID;
  ticket_number: string;
  examination_id?: ID;
  examination_name?: string;
  exam_type?: string;
  issued_at?: string | null;
  is_valid?: boolean;
}

export interface InternalMark {
  id: ID;
  student_id: ID;
  subject_id: ID;
  examination_id?: ID | null;
  subject_code: string;
  subject_name: string;
  component_marks: Record<string, number>;
  mid1_marks: number;
  mid2_marks: number;
  assignments_marks: number;
  total_marks: number;
  max_marks: number;
  status: string;
  submitted_at?: string | null;
  student_name?: string;
  roll_number?: string;
}

export interface SubjectResult {
  id: ID;
  subject_id: ID;
  subject_code: string;
  subject_name: string;
  credits: number;
  internal_marks: number;
  external_marks: number;
  total_marks: number;
  max_marks: number;
  grade: string;
  grade_point: number;
  result_status: 'PASS' | 'FAIL' | 'BACKLOG';
}

export interface SemesterResult {
  id: ID;
  examination_id?: ID | null;
  examination_name?: string | null;
  semester_number: number;
  academic_year_name: string;
  sgpa: number | null;
  cgpa: number | null;
  total_credits: number;
  earned_credits: number;
  status: string;
  published_at?: string | null;
  subject_results: SubjectResult[];
  student_id?: ID;
  roll_number?: string;
  student_name?: string;
}

export interface PerformanceData {
  semesters: Array<{ semester: number; academic_year: string; sgpa: number | null; cgpa: number | null; status: string }>;
  current_cgpa: number | null;
}

export interface Backlog {
  id: ID;
  subject_id: ID;
  subject_code: string;
  subject_name: string;
  credits: number;
  semester_number: number;
  academic_year_name: string;
  attempts: number;
  is_cleared: boolean;
  supplementary_exam_id?: ID | null;
}

export interface RecountingRequest {
  id: ID;
  examination_id?: ID;
  examination_name?: string;
  subject_id: ID;
  subject_code: string;
  subject_name: string;
  original_marks: number;
  reason?: string | null;
  request_status: string;
  admin_response?: string | null;
  revised_marks?: number | null;
  created_at: string;
}

export interface CorrectionRequest {
  id: ID;
  subject_id: ID;
  subject_code: string;
  subject_name: string;
  reported_marks: number;
  suggested_marks?: number | null;
  explanation: string;
  request_status: string;
  faculty_response?: string | null;
  created_at: string;
  student_id?: ID;
  student_name?: string;
  roll_number?: string;
}

export interface NotificationItem {
  id: ID;
  notification_id?: ID;
  title: string;
  message: string;
  category: string;
  created_at: string;
  published_at?: string | null;
  read: boolean;
  read_at?: string | null;
}

export interface FacultyAssignment {
  id: ID;
  subject_id: ID;
  examination_id?: ID | null;
  subject_code: string;
  subject_name: string;
  credits?: number;
  section?: string | null;
  internal_max_marks?: number;
  external_max_marks?: number;
  assessment_configuration?: { components?: Array<{ name: string; max_marks: number }> };
  assignment_status?: string;
  subject?: DataRecord;
}

export interface FacultyStudent {
  id: ID;
  roll_number: string;
  full_name: string;
  email: string;
  branch?: string | null;
  semester: number;
  section?: string | null;
}

export interface AdminStudent {
  id: ID;
  user_id: ID;
  roll_number: string;
  full_name: string;
  email: string;
  department?: string | null;
  branch?: string | null;
  current_semester: number;
  academic_year: string;
  enrollment_status: string;
  section?: string | null;
}

export interface AdminFaculty {
  id: ID;
  user_id: ID;
  faculty_id: string;
  full_name: string;
  email: string;
  department?: string | null;
  designation: string;
  account_status: string;
}

export interface Subject {
  id: ID;
  subject_code: string;
  subject_name: string;
  course_id?: ID | null;
  semester_id?: ID | null;
  credits: number;
  internal_max_marks: number;
  external_max_marks: number;
  subject_type: string;
  assessment_configuration: DataRecord;
}

export interface AuditLog {
  id: ID;
  user_id?: ID | null;
  user_role?: string | null;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  created_at: string;
}
