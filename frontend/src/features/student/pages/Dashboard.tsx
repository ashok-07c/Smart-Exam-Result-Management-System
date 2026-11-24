import { Link } from 'react-router-dom';
import { Award, Bell, CalendarDays, ClipboardList, Ticket, TrendingUp } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { StatCard } from '@/components/common/StatCard';
import { ErrorPanel } from '@/components/common/ErrorPanel';
import { Alert, Badge, Button, Card, CardContent, CardHeader, CardTitle, LoadingState, StatusBadge } from '@/components/ui';
import { useApiQuery } from '@/lib/hooks';
import type { Examination, HallTicket, NotificationItem, PerformanceData, SemesterResult, StudentProfile } from '@/lib/types';
import { formatDate, titleCase } from '@/lib/utils';
import { useAuth } from '@/providers/auth-context';

export function StudentDashboard() {
  const { user } = useAuth();
  const profile = useApiQuery<StudentProfile>('student-profile', '/students/me');
  const exams = useApiQuery<Examination[]>('student-exams', '/students/me/examinations');
  const results = useApiQuery<SemesterResult[]>('student-results', '/students/me/results');
  const performance = useApiQuery<PerformanceData>('student-performance', '/students/me/sgpa-cgpa');
  const tickets = useApiQuery<HallTicket[]>('student-tickets', '/students/me/hall-tickets');
  const notices = useApiQuery<{ items: NotificationItem[]; total: number }>('student-notices', '/students/me/notifications', { page_size: 5 });
  const error = profile.error ?? exams.error ?? results.error ?? performance.error ?? notices.error;

  if (profile.isLoading || exams.isLoading || results.isLoading) return <LoadingState label="Loading your dashboard…" />;

  const openExams = (exams.data ?? []).filter((exam) => exam.eligible && !exam.registered);
  const latestResult = results.data?.[results.data.length - 1];
  const unread = (notices.data?.items ?? []).filter((notice) => !notice.read).length;

  return (
    <>
      <PageHeader
        eyebrow="Student portal"
        title={`Welcome back, ${user?.full_name?.split(' ')[0] ?? 'student'}`}
        description="Track registrations, timetables, marks and published results from one place."
        actions={<Badge variant="outline">{profile.data?.roll_number ?? user?.roll_number}</Badge>}
      />
      <ErrorPanel error={error} onRetry={() => { void profile.refetch(); void exams.refetch(); void results.refetch(); }} />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Open registrations" value={openExams.length} icon={ClipboardList} hint="Eligible examinations" />
        <StatCard label="Hall tickets" value={tickets.data?.length ?? 0} icon={Ticket} tone="success" hint="Valid documents" />
        <StatCard label="Published results" value={results.data?.length ?? 0} icon={Award} tone="warning" hint="Semesters available" />
        <StatCard label="Current CGPA" value={performance.data?.current_cgpa ?? '—'} icon={TrendingUp} hint="From published results" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <CardTitle>Registration opportunities</CardTitle>
            <Link to="/student/examinations" className="text-sm font-medium text-primary hover:underline">View all</Link>
          </CardHeader>
          <CardContent className="space-y-3">
            {openExams.length === 0 ? (
              <Alert variant="info">No examination registrations are currently open for your profile.</Alert>
            ) : openExams.slice(0, 3).map((exam) => (
              <div key={exam.id} className="flex flex-col gap-3 rounded-lg border border-border p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-medium">{exam.name}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Deadline {formatDate(exam.registration_deadline)} · {exam.subject_count ?? '—'} subjects
                  </p>
                </div>
                <StatusBadge value={exam.exam_type} />
              </div>
            ))}
            <Link to="/student/timetable">
              <Button variant="outline" size="sm" className="mt-1"><CalendarDays className="h-4 w-4" /> View timetable</Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <CardTitle>Recent activity</CardTitle>
            <Link to="/student/notifications" className="text-sm font-medium text-primary hover:underline">Inbox</Link>
          </CardHeader>
          <CardContent className="space-y-3">
            {unread > 0 && <p className="text-xs font-medium text-warning">{unread} unread notification{unread === 1 ? '' : 's'}</p>}
            {(notices.data?.items ?? []).slice(0, 4).map((notice) => (
              <div key={notice.id} className="border-l-2 border-primary/40 pl-3">
                <p className="text-sm font-medium">{notice.title}</p>
                <p className="text-xs text-muted-foreground">{formatDate(notice.created_at, true)} · {titleCase(notice.category)}</p>
              </div>
            ))}
            {!notices.data?.items?.length && <p className="text-sm text-muted-foreground">No notifications yet.</p>}
            <Link to="/student/results"><Button variant="ghost" size="sm"><Bell className="h-4 w-4" /> My results</Button></Link>
          </CardContent>
        </Card>
      </div>

      {latestResult && (
        <Card className="mt-6">
          <CardHeader><CardTitle>Latest published result</CardTitle></CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-4">
            <div><p className="text-xs text-muted-foreground">Semester</p><p className="text-lg font-semibold">Sem {latestResult.semester_number}</p></div>
            <div><p className="text-xs text-muted-foreground">SGPA</p><p className="text-lg font-semibold">{latestResult.sgpa ?? '—'}</p></div>
            <div><p className="text-xs text-muted-foreground">CGPA</p><p className="text-lg font-semibold">{latestResult.cgpa ?? '—'}</p></div>
            <div><p className="text-xs text-muted-foreground">Credits earned</p><p className="text-lg font-semibold">{latestResult.earned_credits}/{latestResult.total_credits}</p></div>
          </CardContent>
        </Card>
      )}
    </>
  );
}
