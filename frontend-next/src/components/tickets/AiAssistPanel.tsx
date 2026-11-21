'use client';

import { useEffect, useRef, useState, type ReactNode } from 'react';
import Link from 'next/link';
import {
  AlertTriangle,
  BookOpen,
  Bot,
  CheckCircle2,
  FileText,
  GitBranch,
  Loader2,
  LockKeyhole,
  RefreshCw,
  Sparkles,
  XCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { LoadingInline } from '@/components/common/LoadingScreen';
import { ErrorState } from '@/components/common/ErrorState';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { aiApi } from '@/lib/api/endpoints';
import { ApiError, getApiErrorMessage } from '@/lib/api/errors';
import { AI_MISSING_KEY_CODE, PRETTY_LABELS } from '@/lib/api/types';
import type { AiAnalysisResponse, TicketResponse } from '@/lib/api/types';
import { cn, formatDateTime } from '@/lib/utils';

type BusyAction = 'analyze' | 'regenerate' | 'approve' | null;

interface AiAssistPanelProps {
  ticket: TicketResponse;
  canUseAi: boolean;
  onApproved?: () => void | Promise<void>;
}

function Section({
  icon,
  title,
  aside,
  children,
}: {
  icon: ReactNode;
  title: string;
  aside?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-navy-900">
          <span className="text-teal-700" aria-hidden="true">{icon}</span>
          {title}
        </h3>
        {aside}
      </div>
      <div className="pt-4">{children}</div>
    </section>
  );
}

function Meta({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 break-words text-sm font-medium text-navy-900">{children}</dd>
    </div>
  );
}

function Confidence({ value }: { value: number }) {
  const percent = Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-200" aria-hidden="true">
        <div className="h-full rounded-full bg-teal-500" style={{ width: `${percent}%` }} />
      </div>
      <span className="text-xs font-semibold tabular-nums text-slate-600">{percent}%</span>
    </div>
  );
}

export function AiAssistPanel({ ticket, canUseAi, onApproved }: AiAssistPanelProps) {
  const [analysis, setAnalysis] = useState<AiAnalysisResponse | null>(null);
  const [loadingExisting, setLoadingExisting] = useState(true);
  const [busyAction, setBusyAction] = useState<BusyAction>(null);
  const [error, setError] = useState('');
  const [missingKey, setMissingKey] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);

  function isMissingKeyError(cause: unknown): boolean {
    return cause instanceof ApiError && cause.code === AI_MISSING_KEY_CODE;
  }

  useEffect(() => {
    if (!canUseAi) return;
    const controller = new AbortController();
    controllerRef.current = controller;
    setLoadingExisting(true);

    aiApi
      .getAnalysis(ticket.id, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setAnalysis(result);
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return;
        if (cause instanceof ApiError && cause.status === 404) {
          setAnalysis(null);
          setError('');
          return;
        }
        if (isMissingKeyError(cause)) {
          setMissingKey(true);
          setError('');
          return;
        }
        setError(getApiErrorMessage(cause, 'Unable to load the existing AI analysis.'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingExisting(false);
      });

    return () => {
      controller.abort();
      if (controllerRef.current === controller) controllerRef.current = null;
    };
  }, [canUseAi, ticket.id]);

  async function runAnalysis(kind: 'analyze' | 'regenerate') {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setBusyAction(kind);
    setError('');

    try {
      const result =
        kind === 'analyze'
          ? await aiApi.analyze(ticket.id, controller.signal)
          : await aiApi.regenerateDraft(ticket.id, controller.signal);
      if (controller.signal.aborted) return;
      setAnalysis(result);
      toast.success(kind === 'analyze' ? 'Query analyzed.' : 'Draft regenerated.');
    } catch (cause: unknown) {
      if (controller.signal.aborted || (cause instanceof Error && cause.name === 'AbortError')) return;
      if (isMissingKeyError(cause)) {
        setMissingKey(true);
        setError('');
        toast.error('Add your personal AI key in Settings to use AI assistance.');
        return;
      }
      const message = getApiErrorMessage(cause, 'AI analysis failed.');
      setError(message);
      toast.error(message);
    } finally {
      if (!controller.signal.aborted) setBusyAction(null);
    }
  }

  async function approveDraft() {
    setBusyAction('approve');
    setError('');
    try {
      const result = await aiApi.approveDraft(ticket.id);
      setAnalysis((current) =>
        current
          ? {
              ...current,
              approved_message_id: result.message.id,
              approved_at: new Date().toISOString(),
            }
          : current,
      );
      toast.success(
        result.already_approved ? 'This draft was already approved.' : 'AI draft approved and posted publicly.',
      );
      await onApproved?.();
    } catch (cause: unknown) {
      if (isMissingKeyError(cause)) {
        setMissingKey(true);
        setError('');
        return;
      }
      const message = getApiErrorMessage(cause, 'Unable to approve this draft.');
      setError(message);
      toast.error(message);
    } finally {
      setBusyAction(null);
    }
  }

  if (!canUseAi) return null;

  const busy = busyAction !== null;
  const approved = Boolean(analysis?.approved_message_id);
  const classification = analysis?.classification;
  const department = analysis?.department_recommendation;
  const staff = analysis?.staff_recommendation;
  const draft = analysis?.draft;
  const validationPassed = analysis?.validation?.passed ?? false;
  const closed = ticket.status === 'closed';
  const keyMissing = missingKey || analysis?.error?.code === AI_MISSING_KEY_CODE;

  return (
    <Card className="overflow-hidden" aria-label="AI assistance">
      <div className="border-b border-slate-100 bg-gradient-to-r from-teal-50/80 to-white px-5 py-4 sm:px-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white shadow-sm">
              <Bot className="h-5 w-5" aria-hidden="true" />
            </span>
            <div>
              <h2 className="text-base font-semibold tracking-tight text-navy-900">AI assistance</h2>
              <p className="mt-0.5 max-w-xl text-xs leading-relaxed text-slate-600">
                Staff-only recommendations grounded in approved knowledge. Nothing is assigned or published automatically.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="teal"
              size="sm"
              disabled={busy || closed || keyMissing}
              onClick={() => void runAnalysis('analyze')}
            >
              {busyAction === 'analyze' ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Sparkles className="h-4 w-4" aria-hidden="true" />}
              {busyAction === 'analyze' ? 'Analyzing…' : 'Analyze query'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={busy || !analysis || closed || keyMissing}
              onClick={() => void runAnalysis('regenerate')}
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              {busyAction === 'regenerate' ? 'Regenerating…' : 'Regenerate draft'}
            </Button>
            <Button
              variant="primary"
              size="sm"
              disabled={busy || !draft || approved || closed || keyMissing || analysis?.validation?.passed === false}
              onClick={() => void approveDraft()}
            >
              {busyAction === 'approve' ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <CheckCircle2 className="h-4 w-4" aria-hidden="true" />}
              {busyAction === 'approve'
                ? 'Approving…'
                : approved
                  ? 'Approved and posted'
                  : 'Approve & post reply'}
            </Button>
          </div>
        </div>

        <div className="mt-4 flex items-start gap-2.5 rounded-lg border border-amber-200 bg-amber-50 px-3.5 py-2.5 text-xs text-amber-900">
          <LockKeyhole className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" aria-hidden="true" />
          <p>
            <span className="font-semibold">Human approval required.</span> AI drafts are not public and are never shown to students
            until an authorized staff member approves and posts them.
          </p>
        </div>
      </div>

      <div className="space-y-4 p-5 sm:p-6">
        {keyMissing ? (
          <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-4">
            <p className="flex items-start gap-2 text-sm font-semibold text-amber-900">
              <LockKeyhole className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" aria-hidden="true" />
              Add your personal AI key
            </p>
            <p className="mt-1.5 text-xs leading-relaxed text-amber-800">
              AI assistance needs your own API key. No shared or administrator key is used. Add or validate a key in Settings, then return here to run the analysis.
            </p>
            <Button asChild variant="outline" size="sm" className="mt-3 border-amber-300 bg-white text-amber-900 hover:bg-amber-50">
              <Link href="/settings">Open Settings</Link>
            </Button>
          </div>
        ) : null}
        {error ? <ErrorState compact title="AI request failed" message={error} /> : null}
        {analysis?.error ? (
          <ErrorState compact title="AI run failed" message={analysis.error.message} />
        ) : null}

        {loadingExisting && !analysis ? (
          <LoadingInline label="Checking for a saved analysis…" />
        ) : null}

        {!loadingExisting && !analysis ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/60 px-6 py-10 text-center">
            <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-white text-teal-700 shadow-sm ring-1 ring-slate-200">
              <Sparkles className="h-5 w-5" aria-hidden="true" />
            </span>
            <p className="mt-3 text-sm font-semibold text-navy-900">No analysis yet</p>
            <p className="mx-auto mt-1 max-w-md text-xs leading-relaxed text-slate-500">
              Run an analysis to see classification, routing suggestions, approved sources and a draft reply. All output stays private until you approve it.
            </p>
            <Button variant="teal" size="sm" className="mt-4" disabled={busy || closed || keyMissing} onClick={() => void runAnalysis('analyze')}>
              <Sparkles className="h-4 w-4" aria-hidden="true" /> Analyze this query
            </Button>
          </div>
        ) : null}

        {analysis && !loadingExisting ? (
          <>
            <div className="flex flex-wrap items-center gap-2 text-[11px]">
              <span className="rounded-full bg-slate-100 px-2.5 py-1 font-semibold text-slate-700">
                Version {analysis.version} · {formatDateTime(analysis.created_at)}
              </span>
              <span className="rounded-full bg-amber-50 px-2.5 py-1 font-semibold text-amber-800 ring-1 ring-amber-200/70">
                Recommendations are not confirmed assignments
              </span>
              {analysis.validation ? (
                <span
                  className={cn(
                    'inline-flex items-center gap-1 rounded-full px-2.5 py-1 font-semibold ring-1',
                    validationPassed
                      ? 'bg-teal-50 text-teal-800 ring-teal-200/70'
                      : 'bg-rose-50 text-rose-700 ring-rose-200/70',
                  )}
                >
                  {validationPassed ? <CheckCircle2 className="h-3 w-3" aria-hidden="true" /> : <XCircle className="h-3 w-3" aria-hidden="true" />}
                  {validationPassed ? 'Validation passed' : 'Needs staff review'}
                </span>
              ) : null}
              {approved ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-teal-600 px-2.5 py-1 font-semibold text-white">
                  <CheckCircle2 className="h-3 w-3" aria-hidden="true" /> Draft approved
                </span>
              ) : null}
            </div>

            {classification ? (
              <Section
                icon={<FileText className="h-4 w-4" aria-hidden="true" />}
                title="Classification"
                aside={<Confidence value={classification.confidence} />}
              >
                <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <Meta label="Intent">{classification.intent}</Meta>
                  <Meta label="Category">{classification.category}</Meta>
                  <Meta label="Detected urgency"><span className="capitalize">{classification.urgency}</span></Meta>
                  <Meta label="Language"><span className="uppercase">{classification.language}</span></Meta>
                </dl>
                <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-slate-100 pt-3 text-xs">
                  <span className="text-slate-500">
                    Suggested priority:{' '}
                    <span className="font-semibold text-navy-900">
                      {analysis.priority_recommendation
                        ? PRETTY_LABELS[analysis.priority_recommendation] ?? analysis.priority_recommendation
                        : 'unavailable'}
                    </span>
                  </span>
                  {classification.entities.length > 0 ? (
                    <span className="text-slate-500">
                      Entities: <span className="font-medium text-navy-800">{classification.entities.join(', ')}</span>
                    </span>
                  ) : null}
                  {classification.rationale ? (
                    <span className="w-full text-slate-500">{classification.rationale}</span>
                  ) : null}
                </div>
              </Section>
            ) : null}

            <div className="grid gap-4 lg:grid-cols-2">
              <Section
                icon={<GitBranch className="h-4 w-4" aria-hidden="true" />}
                title="Routing recommendation"
              >
                <p className="text-sm font-semibold text-navy-900">
                  {department?.department_name ?? 'No department recommendation'}
                </p>
                <p className="mt-1 text-xs leading-relaxed text-slate-600">
                  {department?.reason ?? 'No explanation available.'}
                </p>
                {department ? (
                  <div className="mt-3"><Confidence value={department.confidence} /></div>
                ) : null}
                <dl className="mt-4 space-y-1.5 border-t border-slate-100 pt-3 text-xs">
                  <div className="flex justify-between gap-3">
                    <dt className="text-slate-500">Confirmed assignment</dt>
                    <dd className="text-right font-medium text-navy-900">{ticket.assignee_name ?? 'Unassigned'}</dd>
                  </div>
                  {staff ? (
                    <div className="flex justify-between gap-3">
                      <dt className="text-slate-500">Suggested staff</dt>
                      <dd className="text-right font-medium text-navy-900">{staff.staff_name} <span className="font-normal text-slate-500">(not assigned)</span></dd>
                    </div>
                  ) : null}
                </dl>
              </Section>

              <Section
                icon={<BookOpen className="h-4 w-4" aria-hidden="true" />}
                title="Approved knowledge sources"
                aside={
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-600">
                    {analysis.knowledge_sources.length}
                  </span>
                }
              >
                {analysis.knowledge_sources.length > 0 ? (
                  <ul className="space-y-3">
                    {analysis.knowledge_sources.map((source) => (
                      <li key={source.source_id} className="rounded-lg border border-slate-200 bg-slate-50/50 p-3">
                        <p className="flex flex-wrap items-center gap-2 text-xs font-semibold text-navy-900">
                          {source.title}
                          <span className="rounded bg-white px-1.5 py-0.5 font-mono text-[10px] text-teal-700 ring-1 ring-slate-200">{source.source_id}</span>
                        </p>
                        <p className="mt-1 text-xs leading-relaxed text-slate-600">{source.excerpt}</p>
                        <div className="mt-2 flex items-center gap-2">
                          <span className="text-[10px] text-slate-500">Relevance</span>
                          <Confidence value={source.relevance_score} />
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="rounded-lg border border-amber-200 bg-amber-50/70 p-3">
                    <p className="flex items-start gap-2 text-xs leading-relaxed text-amber-900">
                      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-700" aria-hidden="true" />
                      No approved knowledge source matched this query. The draft abstains rather than inventing policy.
                    </p>
                  </div>
                )}
                {analysis.abstention_reason ? (
                  <p className="mt-3 text-xs italic text-amber-800">{analysis.abstention_reason}</p>
                ) : null}
              </Section>
            </div>

            {analysis.validation && !analysis.validation.passed ? (
              <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
                <p className="flex items-center gap-2 text-sm font-semibold text-rose-900">
                  <XCircle className="h-4 w-4" aria-hidden="true" /> Validation issues
                </p>
                <p className="mt-1 text-xs text-rose-700">This draft cannot be approved until the issues are resolved.</p>
                <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-rose-800">
                  {analysis.validation.issues.map((issue) => (
                    <li key={issue}>{issue}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {draft ? (
              <Section
                icon={<FileText className="h-4 w-4" aria-hidden="true" />}
                title="AI response draft"
                aside={
                  <span className={cn(
                    'rounded-full px-2.5 py-1 text-[11px] font-semibold ring-1',
                    approved
                      ? 'bg-teal-600 text-white ring-teal-600'
                      : 'bg-white text-teal-800 ring-teal-200',
                  )}>
                    {approved ? 'Approved & posted' : 'Not public until approved'}
                  </span>
                }
              >
                <div className="rounded-xl border border-teal-200 bg-teal-50/60 p-4">
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">{draft.body}</p>
                </div>
                <dl className="mt-4 grid gap-3 border-t border-slate-100 pt-3 text-[11px] sm:grid-cols-3">
                  <Meta label="Language"><span className="uppercase">{draft.language}</span></Meta>
                  <Meta label="Confidence"><Confidence value={draft.confidence} /></Meta>
                  <Meta label="Cited sources">
                    {draft.source_ids.length > 0 ? draft.source_ids.join(', ') : 'none'}
                  </Meta>
                </dl>
                {draft.needs_staff_review ? (
                  <p className="mt-3 flex items-center gap-1.5 text-xs text-amber-800">
                    <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" /> Staff review recommended before posting.
                  </p>
                ) : null}
              </Section>
            ) : null}
          </>
        ) : null}
      </div>
    </Card>
  );
}
