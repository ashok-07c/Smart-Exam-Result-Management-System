import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'react-hot-toast';
import { ShieldCheck } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { ErrorPanel } from '@/components/common/ErrorPanel';
import { Alert, Button, Card, CardContent, CardHeader, CardTitle, Field, Input } from '@/components/ui';
import { api, ApiError } from '@/lib/api';
import { useApiQuery } from '@/lib/hooks';
import type { StudentProfile } from '@/lib/types';
import { useAuth } from '@/providers/auth-context';

const schema = z.object({
  full_name: z.string().min(2, 'Enter your full name'),
  section: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export function StudentProfile() {
  const { refreshUser } = useAuth();
  const profile = useApiQuery<StudentProfile>('student-profile', '/students/me');
  const {
    register, handleSubmit, reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (profile.data) {
      reset({
        full_name: profile.data.full_name,
        section: profile.data.section ?? '',
      });
    }
  }, [profile.data, reset]);

  const submit = async (values: FormValues) => {
    try {
      const response = await api.patch('/students/me/profile', values);
      toast.success(response.message);
      void profile.refetch();
      await refreshUser();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : 'Could not update profile');
    }
  };

  return (
    <>
      <PageHeader eyebrow="Student portal" title="My Profile" description="Your enrollment details are maintained by the Examination Admin." />
      <ErrorPanel error={profile.error} onRetry={() => void profile.refetch()} />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Personal & enrollment details</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(submit)} className="grid gap-4 sm:grid-cols-2">
              <Field label="Full name" error={errors.full_name?.message}>
                <Input {...register('full_name')} />
              </Field>
              <Field label="Roll number">
                <Input value={profile.data?.roll_number ?? ''} disabled />
              </Field>
              <Field label="Email address">
                <Input value={profile.data?.email ?? ''} disabled />
              </Field>
              <Field label="Department">
                <Input value={profile.data?.department ?? '—'} disabled />
              </Field>
              <Field label="Branch">
                <Input value={profile.data?.branch ?? '—'} disabled />
              </Field>
              <Field label="Section" error={errors.section?.message}>
                <Input {...register('section')} placeholder="e.g. A" />
              </Field>
              <Field label="Current semester">
                <Input value={`Semester ${profile.data?.current_semester ?? '—'}`} disabled />
              </Field>
              <Field label="Academic year">
                <Input value={profile.data?.academic_year ?? '—'} disabled />
              </Field>
              <div className="sm:col-span-2">
                <Button type="submit" loading={isSubmitting}>Save changes</Button>
              </div>
            </form>
          </CardContent>
        </Card>
        <Card className="h-fit">
          <CardHeader><CardTitle>Account security</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-start gap-3 rounded-lg border border-border p-3">
              <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-success" />
              <div>
                <p className="font-medium">Password protected</p>
                <p className="text-xs text-muted-foreground">Passwords are hashed with bcrypt and never returned by the API.</p>
              </div>
            </div>
            <Alert variant="info">
              Contact the Examination Admin if you need a password reset. Reset tokens are single-use and expire after one hour.
            </Alert>
            <div>
              <p className="text-xs text-muted-foreground">Enrollment status</p>
              <p className="font-medium">{profile.data?.enrollment_status ?? '—'}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Admission year</p>
              <p className="font-medium">{profile.data?.admission_year ?? '—'}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
