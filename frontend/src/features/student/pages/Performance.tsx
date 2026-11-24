import { Activity, TrendingUp } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { PageHeader } from '@/components/common/PageHeader';
import { StatCard } from '@/components/common/StatCard';
import { ErrorPanel } from '@/components/common/ErrorPanel';
import { Alert, Card, CardContent, CardHeader, CardTitle, LoadingState } from '@/components/ui';
import { useApiQuery } from '@/lib/hooks';
import type { PerformanceData } from '@/lib/types';

export function StudentPerformance() {
  const performance = useApiQuery<PerformanceData>('student-performance', '/students/me/sgpa-cgpa');

  if (performance.isLoading) return <LoadingState label="Calculating performance…" />;

  const data = performance.data ?? { semesters: [], current_cgpa: null };
  const chartData = data.semesters.map((item) => ({
    name: `Sem ${item.semester}`,
    sgpa: Number(item.sgpa ?? 0),
    cgpa: Number(item.cgpa ?? 0),
  }));
  const best = data.semesters.reduce<number>((max, item) => Math.max(max, Number(item.sgpa ?? 0)), 0);

  return (
    <>
      <PageHeader eyebrow="Student portal" title="Academic Performance" description="SGPA and CGPA trends calculated by the configured grading rules." />
      <ErrorPanel error={performance.error} onRetry={() => void performance.refetch()} />
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Current CGPA" value={data.current_cgpa ?? '—'} icon={TrendingUp} />
        <StatCard label="Best semester SGPA" value={best || '—'} icon={Activity} tone="success" />
        <StatCard label="Published semesters" value={data.semesters.length} icon={Activity} tone="warning" />
      </div>
      <Card className="mt-6">
        <CardHeader><CardTitle>Semester-wise SGPA / CGPA</CardTitle></CardHeader>
        <CardContent>
          {chartData.length ? (
            <div className="h-[320px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 8, right: 12, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0, 10]} tick={{ fontSize: 12 }} />
                  <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid hsl(var(--border))' }} />
                  <Line type="monotone" dataKey="sgpa" stroke="hsl(var(--primary))" strokeWidth={2.5} dot={{ r: 4 }} name="SGPA" />
                  <Line type="monotone" dataKey="cgpa" stroke="hsl(var(--success))" strokeWidth={2} dot={{ r: 3 }} name="CGPA" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : <Alert>No published results are available to chart yet.</Alert>}
        </CardContent>
      </Card>
    </>
  );
}
