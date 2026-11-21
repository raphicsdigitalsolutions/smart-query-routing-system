'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  BarChart3,
  Download,
  Inbox,
  Loader2,
  RefreshCw,
  TrendingUp,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { PageHeader } from '@/components/common/PageHeader';
import { Skeleton, StatSkeleton } from '@/components/common/Skeleton';
import { StatCard } from '@/components/common/StatCard';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { analyticsApi, downloadReport } from '@/lib/api/endpoints';
import { getApiErrorMessage } from '@/lib/api/errors';
import type { AnalyticsOverview, ReportFormat } from '@/lib/api/types';
import { useSession } from '@/hooks/useSession';
import { prettyLabel } from '@/lib/utils';

interface ChartDatum {
  name: string;
  value: number;
}

interface MonthlyDatum {
  month: string;
  created: number;
  resolved: number;
}

const CHART_COLORS = ['#0D9488', '#102A43', '#3DBBAE', '#D97706', '#64748B', '#0B7A72', '#1D4ED8', '#BE123C'];

const TOOLTIP_STYLE = {
  borderRadius: 12,
  border: '1px solid #E2E8F0',
  boxShadow: '0 12px 30px -12px rgba(16,42,67,0.25)',
  fontSize: 12,
};

function readNumber(value: unknown): number {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function toChartData(value: unknown): ChartDatum[] {
  if (Array.isArray(value)) {
    return value
      .map((entry) => {
        if (entry === null || typeof entry !== 'object') return null;
        const record = entry as Record<string, unknown>;
        const rawName =
          record.name ?? record.label ?? record.status ?? record.priority ?? record.department_name ?? record.department ?? record.key ?? 'Other';
        const rawValue = record.value ?? record.count ?? record.total ?? record.tickets ?? 0;
        return { name: String(rawName), value: readNumber(rawValue) };
      })
      .filter((entry): entry is ChartDatum => entry !== null);
  }
  if (value && typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>).map(([name, count]) => ({
      name,
      value: readNumber(count),
    }));
  }
  return [];
}

function toMonthlyData(value: unknown): MonthlyDatum[] {
  if (Array.isArray(value)) {
    return value
      .map((entry) => {
        if (entry === null || typeof entry !== 'object') return null;
        const record = entry as Record<string, unknown>;
        const month = String(record.month ?? record.label ?? record.name ?? '');
        if (!month) return null;
        return {
          month,
          created: readNumber(record.created ?? record.value ?? record.total ?? 0),
          resolved: readNumber(record.resolved ?? 0),
        };
      })
      .filter((entry): entry is MonthlyDatum => entry !== null);
  }
  if (value && typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>).map(([month, count]) => ({
      month,
      created: readNumber(count),
      resolved: 0,
    }));
  }
  return [];
}

function ChartShell({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return (
    <Card className="min-w-0 overflow-hidden p-5 sm:p-6">
      <h3 className="text-sm font-semibold text-navy-900">{title}</h3>
      <p className="mt-0.5 text-xs text-slate-500">{description}</p>
      <div className="mt-4 h-[260px] w-full min-w-0">{children}</div>
    </Card>
  );
}

export default function AnalyticsPage() {
  const { user } = useSession();
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloading, setDownloading] = useState<ReportFormat | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setOverview(await analyticsApi.overview());
    } catch (cause) {
      setError(getApiErrorMessage(cause, 'Unable to load analytics.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleDownload(format: ReportFormat) {
    setDownloading(format);
    try {
      const blob = await downloadReport(format);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `smartquery-tickets.${format}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      toast.success(`${format.toUpperCase()} report downloaded.`);
    } catch (cause) {
      toast.error(getApiErrorMessage(cause, 'Unable to download the report.'));
    } finally {
      setDownloading(null);
    }
  }

  const statusData = toChartData(overview?.by_status);
  const priorityData = toChartData(overview?.by_priority);
  const departmentData = toChartData(overview?.by_department);
  const monthlyData = toMonthlyData(overview?.monthly);
  const hasAnyChart = statusData.length + priorityData.length + departmentData.length + monthlyData.length > 0;
  const metric = (value: number | null | undefined) => (value === null || value === undefined ? '—' : value);

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Workspace tools"
        title="Analytics"
        description={`Ticket insights scoped to your role${user ? ` (${prettyLabel(user.role)})` : ''}. All figures come from the live backend.`}
        icon={<BarChart3 className="h-6 w-6" aria-hidden="true" />}
        actions={
          <>
            <Button variant="outline" onClick={() => void handleDownload('pdf')} disabled={downloading !== null}>
              {downloading === 'pdf' ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Download className="h-4 w-4" aria-hidden="true" />}
              PDF report
            </Button>
            <Button variant="outline" onClick={() => void handleDownload('xlsx')} disabled={downloading !== null}>
              {downloading === 'xlsx' ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Download className="h-4 w-4" aria-hidden="true" />}
              Excel report
            </Button>
            <Button variant="ghost" size="icon" onClick={() => void load()} aria-label="Refresh analytics" disabled={loading}>
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
            </Button>
          </>
        }
      />

      {error ? <ErrorState title="Analytics unavailable" message={error} onRetry={() => void load()} /> : null}
      {loading ? <StatSkeleton count={4} /> : null}

      {!loading && !error && overview ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Total tickets" value={metric(overview.total_tickets)} hint="Visible to your role" icon={<Inbox className="h-5 w-5" aria-hidden="true" />} tone="navy" />
            <StatCard label="Open tickets" value={metric(overview.open_tickets)} hint="Awaiting resolution" icon={<Activity className="h-5 w-5" aria-hidden="true" />} tone="teal" />
            <StatCard label="Resolved" value={metric(overview.resolved_tickets)} hint="Closed or resolved" icon={<TrendingUp className="h-5 w-5" aria-hidden="true" />} tone="teal" />
            <StatCard label="Escalated" value={metric(overview.escalated_tickets)} hint="Requires attention" icon={<AlertTriangle className="h-5 w-5" aria-hidden="true" />} tone="rose" />
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Unassigned" value={metric(overview.unassigned_tickets)} icon={<ArrowUpRight className="h-5 w-5" aria-hidden="true" />} tone="amber" />
            <StatCard label="Avg. resolution" value={overview.avg_resolution_hours === null || overview.avg_resolution_hours === undefined ? '—' : `${overview.avg_resolution_hours.toFixed(1)}h`} icon={<TrendingUp className="h-5 w-5" aria-hidden="true" />} tone="navy" />
            <StatCard label="First response" value={overview.avg_first_response_hours === null || overview.avg_first_response_hours === undefined ? '—' : `${overview.avg_first_response_hours.toFixed(1)}h`} icon={<Activity className="h-5 w-5" aria-hidden="true" />} tone="teal" />
            <StatCard label="Reporting scope" value={overview.role ? prettyLabel(overview.role) : prettyLabel(user?.role ?? 'all')} icon={<BarChart3 className="h-5 w-5" aria-hidden="true" />} tone="navy" />
          </div>

          {!hasAnyChart ? (
            <EmptyState
              title="No chart data yet"
              message="Charts will appear once tickets have been recorded. KPI values above reflect the current backend response."
              icon={<BarChart3 className="h-5 w-5" aria-hidden="true" />}
            />
          ) : (
            <div className="grid gap-5 xl:grid-cols-2">
              <ChartShell title="Tickets by status" description="Current distribution across the ticket lifecycle.">
                {statusData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={statusData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius="72%" label={false}>
                        {statusData.map((entry, index) => (
                          <Cell key={`${entry.name}-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={TOOLTIP_STYLE} />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : <EmptyState title="No status data" message="No status breakdown was returned for your role." />}
              </ChartShell>

              <ChartShell title="Tickets by priority" description="How urgent the reported tickets are.">
                {priorityData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={priorityData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E6EBF1" vertical={false} />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                      <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: '#F1F5F9' }} />
                      <Bar dataKey="value" name="Tickets" fill="#0D9488" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : <EmptyState title="No priority data" message="No priority breakdown was returned for your role." />}
              </ChartShell>

              <ChartShell title="Tickets by department" description="Department-level workload across visible tickets.">
                {departmentData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={departmentData} layout="vertical" margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E6EBF1" horizontal={false} />
                      <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                      <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 10 }} />
                      <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: '#F1F5F9' }} />
                      <Bar dataKey="value" name="Tickets" fill="#102A43" radius={[0, 6, 6, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : <EmptyState title="No department data" message="No department breakdown was returned for your role." />}
              </ChartShell>

              <ChartShell title="Monthly activity" description="Tickets created and resolved over time.">
                {monthlyData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={monthlyData} margin={{ top: 8, right: 12, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E6EBF1" vertical={false} />
                      <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                      <Tooltip contentStyle={TOOLTIP_STYLE} />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      <Line type="monotone" dataKey="created" name="Created" stroke="#0D9488" strokeWidth={2} dot={{ r: 2 }} />
                      <Line type="monotone" dataKey="resolved" name="Resolved" stroke="#102A43" strokeWidth={2} dot={{ r: 2 }} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : <EmptyState title="No monthly data" message="No monthly breakdown was returned for your role." />}
              </ChartShell>
            </div>
          )}

          <Card className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="text-sm font-semibold text-navy-900">Export detailed tickets</h3>
              <p className="mt-1 text-xs leading-relaxed text-slate-500">
                Reports use the same role scope as this dashboard and are generated by the backend.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="teal" size="sm" onClick={() => void handleDownload('pdf')} disabled={downloading !== null}>
                <Download className="h-4 w-4" aria-hidden="true" /> Export PDF
              </Button>
              <Button variant="outline" size="sm" onClick={() => void handleDownload('xlsx')} disabled={downloading !== null}>
                <Download className="h-4 w-4" aria-hidden="true" /> Export Excel
              </Button>
            </div>
          </Card>
        </>
      ) : null}

      {!loading && !error && !overview ? (
        <EmptyState title="No analytics available" message="The backend did not return an overview for this role." />
      ) : null}

      {loading ? (
        <div className="grid gap-5 xl:grid-cols-2">
          <Skeleton className="h-80" />
          <Skeleton className="h-80" />
        </div>
      ) : null}
    </div>
  );
}
