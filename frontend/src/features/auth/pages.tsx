import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'react-hot-toast';
import { ArrowLeft, Eye, EyeOff, GraduationCap, ShieldCheck } from 'lucide-react';
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Field, Input } from '@/components/ui';
import { useAuth } from '@/providers/auth-context';
import { api, ApiError } from '@/lib/api';
import { homeForRole } from '@/lib/roles';
import type { AuthUser } from '@/lib/types';

const loginSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});
type LoginForm = z.infer<typeof loginSchema>;

const forgotSchema = z.object({ email: z.string().min(1, 'Email is required').email('Enter a valid email address') });
type ForgotForm = z.infer<typeof forgotSchema>;

const resetSchema = z
  .object({
    token: z.string().min(1, 'Reset token is required'),
    new_password: z.string().min(8, 'Use at least 8 characters'),
    confirm_password: z.string().min(1, 'Confirm your password'),
  })
  .refine((values) => values.new_password === values.confirm_password, {
    path: ['confirm_password'],
    message: 'Passwords do not match',
  });
type ResetForm = z.infer<typeof resetSchema>;

const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, 'Current password is required'),
    new_password: z.string().min(8, 'Use at least 8 characters')
      .regex(/[A-Z]/, 'Include an uppercase letter')
      .regex(/[a-z]/, 'Include a lowercase letter')
      .regex(/\d/, 'Include a digit'),
    confirm_password: z.string().min(1, 'Confirm your new password'),
  })
  .refine((values) => values.new_password === values.confirm_password, {
    path: ['confirm_password'],
    message: 'Passwords do not match',
  })
  .refine((values) => values.new_password !== values.current_password, {
    path: ['new_password'],
    message: 'Choose a password different from the current one',
  });
type ChangePasswordForm = z.infer<typeof changePasswordSchema>;

function AuthLayout({ children, subtitle }: { children: React.ReactNode; subtitle: string }) {
  return (
    <div className="relative grid min-h-screen place-items-center overflow-hidden bg-background p-4 sm:p-6">
      <div className="subtle-grid pointer-events-none absolute inset-0 opacity-60" />
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-primary/10 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-40 -right-24 h-96 w-96 rounded-full bg-accent/60 blur-3xl" />
      <div className="relative w-full max-w-md animate-fade-in">
        <div className="mb-7 flex flex-col items-center text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-lg">
            <GraduationCap className="h-6 w-6" aria-hidden="true" />
          </div>
          <h1 className="text-center text-lg font-bold leading-snug tracking-tight sm:text-xl">
            JNTUA College Of Engineering Pulivendula Smart Exam Result Management System
          </h1>
          <p className="mt-1.5 text-sm text-muted-foreground">{subtitle}</p>
        </div>
        {children}
      </div>
    </div>
  );
}

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  const onSubmit = async (values: LoginForm) => {
    try {
      const user = await login(values.email, values.password);
      toast.success(`Welcome, ${user.full_name}`);
      navigate(user.must_change_password ? '/change-password' : homeForRole(user.role), { replace: true });
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Unable to sign in right now';
      setError('root', { message });
      toast.error(message);
    }
  };

  return (
    <AuthLayout subtitle="Sign in to your role-based academic workspace">
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-lg">Sign in</CardTitle>
          <CardDescription>Use your institution-issued account. Your role is verified by the server.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            {errors.root && <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{errors.root.message}</p>}
            <Field label="Email address" error={errors.email?.message}>
              <Input type="email" autoComplete="username" placeholder="you@example.com" {...register('email')} />
            </Field>
            <Field label="Password" error={errors.password?.message}>
              <div className="relative">
                <Input
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className="pr-11"
                  {...register('password')}
                />
                <button
                  type="button"
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1.5 text-muted-foreground hover:text-foreground"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </Field>
            <div className="flex items-center justify-between">
              <Link to="/forgot-password" className="text-sm font-medium text-primary hover:underline">
                Forgot password?
              </Link>
            </div>
            <Button type="submit" className="w-full" loading={isSubmitting}>Sign in</Button>
          </form>
        </CardContent>
      </Card>
    </AuthLayout>
  );
}

export function ChangePasswordPage() {
  const { user, changePassword, logout } = useAuth();
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordForm>({ resolver: zodResolver(changePasswordSchema) });

  const onSubmit = async (values: ChangePasswordForm) => {
    try {
      await changePassword(values.current_password, values.new_password, values.confirm_password);
      toast.success('Password updated. You can now continue.');
      navigate(homeForRole(user?.role ?? 'STUDENT'), { replace: true });
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not change password');
    }
  };

  const signOut = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <AuthLayout subtitle="Mandatory first-login security step">
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle className="text-lg">Change temporary password</CardTitle>
          <CardDescription>
            Signed in as {user?.email}. Choose a new password before accessing the {user?.role === 'FACULTY' ? 'faculty' : user?.role === 'EXAM_ADMIN' ? 'administration' : 'student'} workspace.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <Field label="Current temporary password" error={errors.current_password?.message}>
              <Input type="password" autoComplete="current-password" {...register('current_password')} />
            </Field>
            <Field label="New password" hint="At least 8 characters with upper, lower and digit" error={errors.new_password?.message}>
              <Input type="password" autoComplete="new-password" {...register('new_password')} />
            </Field>
            <Field label="Confirm new password" error={errors.confirm_password?.message}>
              <Input type="password" autoComplete="new-password" {...register('confirm_password')} />
            </Field>
            <Button type="submit" className="w-full" loading={isSubmitting}>Update password and continue</Button>
          </form>
          <button type="button" onClick={signOut} className="mt-5 w-full text-center text-sm text-muted-foreground hover:text-foreground">
            Sign out instead
          </button>
        </CardContent>
      </Card>
    </AuthLayout>
  );
}

export function ForgotPasswordPage() {
  const [token, setToken] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotForm>({ resolver: zodResolver(forgotSchema) });

  const onSubmit = async (values: ForgotForm) => {
    try {
      const response = await api.post<{ reset_token?: string }>('/auth/forgot-password', values);
      setToken(response.data.reset_token ?? null);
      toast.success(response.message);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not request a reset');
    }
  };

  return (
    <AuthLayout subtitle="Request a password reset link">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Reset your password</CardTitle>
          <CardDescription>We never reveal whether an account exists. Reset links are delivered out-of-band.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <Field label="Email address" error={errors.email?.message}>
              <Input type="email" placeholder="you@example.com" {...register('email')} />
            </Field>
            <Button type="submit" className="w-full" loading={isSubmitting}>Request reset</Button>
          </form>
          {token && (
            <div className="mt-4 rounded-lg border border-warning/30 bg-warning/5 p-3 text-sm">
              <p className="font-semibold text-warning">Development reset token</p>
              <p className="mt-1 break-all font-mono text-xs">{token}</p>
              <Link className="mt-2 inline-block text-sm font-medium text-primary hover:underline" to={`/reset-password?token=${encodeURIComponent(token)}`}>
                Continue to reset password →
              </Link>
            </div>
          )}
          <Link to="/login" className="mt-5 flex items-center justify-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" /> Back to sign in
          </Link>
        </CardContent>
      </Card>
    </AuthLayout>
  );
}

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetForm>({
    resolver: zodResolver(resetSchema),
    defaultValues: { token: params.get('token') ?? '' },
  });

  const onSubmit = async (values: ResetForm) => {
    try {
      await api.post('/auth/reset-password', { token: values.token, new_password: values.new_password });
      toast.success('Password updated. Please sign in.');
      navigate('/login', { replace: true });
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not reset password');
    }
  };

  return (
    <AuthLayout subtitle="Choose a new password">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Set new password</CardTitle>
          <CardDescription>Reset tokens are single-use and expire after one hour.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <Field label="Reset token" error={errors.token?.message}>
              <Input className="font-mono text-xs" {...register('token')} />
            </Field>
            <Field label="New password" hint="At least 8 characters" error={errors.new_password?.message}>
              <Input type="password" autoComplete="new-password" {...register('new_password')} />
            </Field>
            <Field label="Confirm password" error={errors.confirm_password?.message}>
              <Input type="password" autoComplete="new-password" {...register('confirm_password')} />
            </Field>
            <Button type="submit" className="w-full" loading={isSubmitting}>Update password</Button>
          </form>
          <Link to="/login" className="mt-5 flex items-center justify-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" /> Back to sign in
          </Link>
        </CardContent>
      </Card>
    </AuthLayout>
  );
}

export function UnauthorizedPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="grid min-h-screen place-items-center p-6">
      <Card className="max-w-md text-center">
        <CardHeader>
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-warning/10 text-warning">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <CardTitle className="text-xl">Access restricted</CardTitle>
          <CardDescription>
            Your account ({user?.email}) does not have permission to view this portal. Switch to the dashboard for your role.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={() => navigate(homeForRole((user?.role ?? 'STUDENT') as AuthUser['role']))}>
            Go to my dashboard
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
