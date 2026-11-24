import { useState, type ReactNode } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import {
  Activity, Award, Bell, BookOpen, CalendarDays, ClipboardCheck, ClipboardList,
  FileBarChart2, FileText, GraduationCap, LayoutDashboard, LogOut, Menu,
  Repeat2, ScrollText, Settings2, Ticket, UserCog, Users, X,
} from 'lucide-react';
import { useAuth } from '@/providers/auth-context';
import { API_MODE } from '@/lib/api';
import { useApiQuery } from '@/lib/hooks';
import { initials, titleCase } from '@/lib/utils';
import { Badge, Button } from '@/components/ui';
import { cn } from '@/lib/utils';

interface NavItem {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const studentNav: NavGroup[] = [
  {
    label: 'Overview',
    items: [
      { to: '/student/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/student/examinations', label: 'Examinations', icon: ClipboardList },
      { to: '/student/timetable', label: 'Timetable', icon: CalendarDays },
      { to: '/student/hall-tickets', label: 'Hall Tickets', icon: Ticket },
    ],
  },
  {
    label: 'Academics',
    items: [
      { to: '/student/marks', label: 'Internal Marks', icon: ClipboardCheck },
      { to: '/student/corrections', label: 'Marks Corrections', icon: FileText },
      { to: '/student/results', label: 'Results', icon: Award },
      { to: '/student/performance', label: 'SGPA / CGPA', icon: Activity },
      { to: '/student/backlogs', label: 'Backlogs', icon: Repeat2 },
      { to: '/student/recounting', label: 'Recounting', icon: ScrollText },
    ],
  },
  {
    label: 'Account',
    items: [
      { to: '/student/notifications', label: 'Notifications', icon: Bell },
      { to: '/student/profile', label: 'Profile', icon: Settings2 },
    ],
  },
];

const facultyNav: NavGroup[] = [
  {
    label: 'Workspace',
    items: [
      { to: '/faculty/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/faculty/assignments', label: 'My Assignments', icon: BookOpen },
      { to: '/faculty/classes', label: 'Classes & Students', icon: Users },
      { to: '/faculty/marks', label: 'Marks Entry', icon: ClipboardCheck },
      { to: '/faculty/submissions', label: 'Submissions', icon: FileBarChart2 },
      { to: '/faculty/corrections', label: 'Correction Requests', icon: FileText },
    ],
  },
  {
    label: 'Academic',
    items: [
      { to: '/faculty/timetable', label: 'Exam Timetable', icon: CalendarDays },
      { to: '/faculty/notifications', label: 'Notifications', icon: Bell },
      { to: '/faculty/profile', label: 'Profile', icon: Settings2 },
    ],
  },
];

const adminNav: NavGroup[] = [
  {
    label: 'Administration',
    items: [
      { to: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/admin/students', label: 'Students', icon: GraduationCap },
      { to: '/admin/faculty', label: 'Faculty', icon: UserCog },
      { to: '/admin/academics', label: 'Academic Records', icon: BookOpen },
      { to: '/admin/assignments', label: 'Faculty Assignments', icon: Users },
    ],
  },
  {
    label: 'Examinations',
    items: [
      { to: '/admin/examinations', label: 'Examinations', icon: ClipboardList },
      { to: '/admin/registrations', label: 'Registrations', icon: ClipboardCheck },
      { to: '/admin/schedules', label: 'Schedules & Timetable', icon: CalendarDays },
      { to: '/admin/hall-tickets', label: 'Hall Tickets', icon: Ticket },
      { to: '/admin/notifications', label: 'Notifications', icon: Bell },
    ],
  },
  {
    label: 'Results & Operations',
    items: [
      { to: '/admin/marks-verification', label: 'Marks Verification', icon: ClipboardCheck },
      { to: '/admin/marks-management', label: 'Marks Management', icon: FileText },
      { to: '/admin/results', label: 'Result Processing', icon: Award },
      { to: '/admin/performance', label: 'SGPA / CGPA Overview', icon: Activity },
      { to: '/admin/backlogs', label: 'Backlogs', icon: Repeat2 },
      { to: '/admin/recounting', label: 'Recounting', icon: ScrollText },
      { to: '/admin/password-reset', label: 'Password Reset', icon: Settings2 },
    ],
  },
];

const navForRole = (role: string): NavGroup[] => {
  if (role === 'EXAM_ADMIN') return adminNav;
  if (role === 'FACULTY') return facultyNav;
  return studentNav;
};

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const groups = navForRole(user?.role ?? 'STUDENT');
  const current = groups.flatMap((group) => group.items).find((item) => item.to === location.pathname);
  const unread = useApiQuery<{ count: number }>('notification-unread-count', '/notifications/unread-count');
  const unreadCount = unread.data?.count ?? 0;
  const notificationPath = user?.role === 'FACULTY' ? '/faculty/notifications' : user?.role === 'EXAM_ADMIN' ? '/admin/notifications' : '/student/notifications';

  const handleLogout = async () => {
    await logout();
    toast.success('You have been signed out');
    navigate('/login', { replace: true });
  };

  return (
    <div className="min-h-screen bg-background">
      {mobileOpen && (
        <button
          className="fixed inset-0 z-30 bg-slate-950/50 lg:hidden"
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-[272px] flex-col border-r border-border bg-card transition-transform duration-200 lg:translate-x-0',
          mobileOpen ? 'translate-x-0' : '-translate-x-full',
        )}
        aria-label="Main navigation"
      >
        <div className="flex h-16 items-center gap-3 border-b border-border px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <GraduationCap className="h-5 w-5" aria-hidden="true" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-bold leading-tight tracking-tight">JNTUA College Of Engineering Pulivendula Smart Exam Result Management System</p>
          </div>
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobileOpen(false)} aria-label="Close navigation">
            <X className="h-4 w-4" />
          </Button>
        </div>

        <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-5 scrollbar-thin">
          {groups.map((group) => (
            <div key={group.label}>
              <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
                {group.label}
              </p>
              <ul className="space-y-1">
                {group.items.map((item) => (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      onClick={() => setMobileOpen(false)}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors',
                          isActive
                            ? 'bg-primary/10 text-primary'
                            : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                        )
                      }
                    >
                      <item.icon className="h-[18px] w-[18px] shrink-0" aria-hidden="true" />
                      <span className="truncate">{item.label}</span>
                      {item.to.endsWith('/notifications') && unreadCount > 0 && (
                        <Badge className="ml-auto" variant="destructive">{unreadCount}</Badge>
                      )}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        <div className="border-t border-border p-4">
          <div className="flex items-center gap-3 rounded-lg bg-muted/60 p-2.5">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-bold text-primary">
              {initials(user?.full_name)}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{user?.full_name}</p>
              <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
            </div>
          </div>
          <p className="mt-3 px-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Signed in as {titleCase(user?.role)}
          </p>
        </div>
      </aside>

      <div className="lg:pl-[272px]">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-border bg-card/90 px-4 backdrop-blur sm:px-6">
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
            <Menu className="h-5 w-5" />
          </Button>
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              {titleCase(user?.role)} portal
            </p>
            <h2 className="truncate text-sm font-semibold sm:text-base">{current?.label ?? 'Overview'}</h2>
          </div>
          {API_MODE === 'mock' && <Badge variant="warning" className="hidden sm:inline-flex">DEMO DATA</Badge>}
          <NavLink
            to={notificationPath}
            className="relative inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label={`Notifications${unreadCount ? `, ${unreadCount} unread` : ''}`}
          >
            <Bell className="h-[18px] w-[18px]" />
            {unreadCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </NavLink>
          <div className="relative">
            <Button variant="outline" size="sm" onClick={() => setUserOpen((value) => !value)} aria-expanded={userOpen}>
              <span className="hidden max-w-[180px] truncate sm:inline">{user?.full_name ?? 'Account'}</span>
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/15 text-[10px] font-bold text-primary sm:hidden">
                {initials(user?.full_name)}
              </span>
            </Button>
            {userOpen && (
              <div className="absolute right-0 top-11 z-30 w-56 rounded-lg border border-border bg-card p-2 shadow-lg">
                <NavLink
                  to={user?.role === 'EXAM_ADMIN' ? '/admin/password-reset' : `${user?.role === 'FACULTY' ? '/faculty' : '/student'}/profile`}
                  onClick={() => setUserOpen(false)}
                  className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-muted"
                >
                  <Settings2 className="h-4 w-4" /> Account settings
                </NavLink>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-destructive hover:bg-destructive/10"
                >
                  <LogOut className="h-4 w-4" /> Sign out
                </button>
              </div>
            )}
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1400px] animate-fade-in p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
