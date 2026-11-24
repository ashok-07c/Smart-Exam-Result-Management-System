import type { ReactNode } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from '@/providers/auth-context';
import { homeForRole } from '@/lib/roles';
import { GuestRoute, PasswordChangeRoute, ProtectedRoute } from '@/routes/ProtectedRoute';
import { ChangePasswordPage, ForgotPasswordPage, LoginPage, ResetPasswordPage, UnauthorizedPage } from '@/features/auth/pages';
import { StudentDashboard } from '@/features/student/pages/Dashboard';
import { StudentExaminations } from '@/features/student/pages/Examinations';
import { StudentTimetable } from '@/features/student/pages/Timetable';
import { StudentHallTickets } from '@/features/student/pages/HallTickets';
import { StudentInternalMarks } from '@/features/student/pages/InternalMarks';
import { StudentCorrections } from '@/features/student/pages/Corrections';
import { StudentResults } from '@/features/student/pages/Results';
import { StudentPerformance } from '@/features/student/pages/Performance';
import { StudentBacklogs } from '@/features/student/pages/Backlogs';
import { StudentRecounting } from '@/features/student/pages/Recounting';
import { StudentProfile } from '@/features/student/pages/Profile';
import { NotificationsPage } from '@/features/common/Notifications';
import {
  FacultyAssignments, FacultyClasses, FacultyCorrections, FacultyDashboard,
  FacultyMarksEntry, FacultyProfile, FacultySubmissions, FacultyTimetable,
} from '@/features/faculty/pages';
import {
  AdminAcademics, AdminAssignments, AdminBacklogs, AdminDashboard,
  AdminExaminations, AdminFaculty, AdminHallTickets, AdminMarksManagement,
  AdminMarksVerification, AdminNotifications, AdminPasswordReset, AdminPerformance,
  AdminRecounting, AdminRegistrations, AdminResults, AdminSchedules, AdminStudents,
} from '@/features/admin/pages';
import type { Role } from '@/lib/types';

const student = (element: ReactNode) => <ProtectedRoute roles={['STUDENT' as Role]}>{element}</ProtectedRoute>;
const faculty = (element: ReactNode) => <ProtectedRoute roles={['FACULTY' as Role]}>{element}</ProtectedRoute>;
const admin = (element: ReactNode) => <ProtectedRoute roles={['EXAM_ADMIN' as Role]}>{element}</ProtectedRoute>;

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route path="/login" element={<GuestRoute><LoginPage /></GuestRoute>} />
      <Route path="/change-password" element={<PasswordChangeRoute><ChangePasswordPage /></PasswordChangeRoute>} />
      <Route path="/forgot-password" element={<GuestRoute><ForgotPasswordPage /></GuestRoute>} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/unauthorized" element={<UnauthorizedPage />} />

      <Route path="/student/dashboard" element={student(<StudentDashboard />)} />
      <Route path="/student/examinations" element={student(<StudentExaminations />)} />
      <Route path="/student/timetable" element={student(<StudentTimetable />)} />
      <Route path="/student/hall-tickets" element={student(<StudentHallTickets />)} />
      <Route path="/student/marks" element={student(<StudentInternalMarks />)} />
      <Route path="/student/corrections" element={student(<StudentCorrections />)} />
      <Route path="/student/results" element={student(<StudentResults />)} />
      <Route path="/student/performance" element={student(<StudentPerformance />)} />
      <Route path="/student/backlogs" element={student(<StudentBacklogs />)} />
      <Route path="/student/recounting" element={student(<StudentRecounting />)} />
      <Route path="/student/notifications" element={student(<NotificationsPage portal="Student" />)} />
      <Route path="/student/profile" element={student(<StudentProfile />)} />

      <Route path="/faculty/dashboard" element={faculty(<FacultyDashboard />)} />
      <Route path="/faculty/assignments" element={faculty(<FacultyAssignments />)} />
      <Route path="/faculty/classes" element={faculty(<FacultyClasses />)} />
      <Route path="/faculty/marks" element={faculty(<FacultyMarksEntry />)} />
      <Route path="/faculty/submissions" element={faculty(<FacultySubmissions />)} />
      <Route path="/faculty/corrections" element={faculty(<FacultyCorrections />)} />
      <Route path="/faculty/timetable" element={faculty(<FacultyTimetable />)} />
      <Route path="/faculty/notifications" element={faculty(<NotificationsPage portal="Faculty" />)} />
      <Route path="/faculty/profile" element={faculty(<FacultyProfile />)} />

      <Route path="/admin/dashboard" element={admin(<AdminDashboard />)} />
      <Route path="/admin/students" element={admin(<AdminStudents />)} />
      <Route path="/admin/faculty" element={admin(<AdminFaculty />)} />
      <Route path="/admin/academics" element={admin(<AdminAcademics />)} />
      <Route path="/admin/assignments" element={admin(<AdminAssignments />)} />
      <Route path="/admin/examinations" element={admin(<AdminExaminations />)} />
      <Route path="/admin/registrations" element={admin(<AdminRegistrations />)} />
      <Route path="/admin/schedules" element={admin(<AdminSchedules />)} />
      <Route path="/admin/hall-tickets" element={admin(<AdminHallTickets />)} />
      <Route path="/admin/notifications" element={admin(<AdminNotifications />)} />
      <Route path="/admin/marks-verification" element={admin(<AdminMarksVerification />)} />
      <Route path="/admin/marks-management" element={admin(<AdminMarksManagement />)} />
      <Route path="/admin/results" element={admin(<AdminResults />)} />
      <Route path="/admin/performance" element={admin(<AdminPerformance />)} />
      <Route path="/admin/backlogs" element={admin(<AdminBacklogs />)} />
      <Route path="/admin/recounting" element={admin(<AdminRecounting />)} />
      <Route path="/admin/password-reset" element={admin(<AdminPasswordReset />)} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.must_change_password ? '/change-password' : homeForRole(user.role)} replace />;
}
