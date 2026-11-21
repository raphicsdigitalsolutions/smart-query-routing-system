'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  BookOpenCheck,
  CheckCircle2,
  FileText,
  History,
  Loader2,
  Trash2,
  UploadCloud,
} from 'lucide-react';
import { toast } from 'sonner';
import { RoleGuard } from '@/components/auth/RoleGuard';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { PageHeader } from '@/components/common/PageHeader';
import { TableSkeleton } from '@/components/common/Skeleton';
import { StatusPill } from '@/components/common/StatusPill';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textArea';
import { departmentsApi, knowledgeApi } from '@/lib/api/endpoints';
import { getApiErrorMessage } from '@/lib/api/errors';
import type {
  DepartmentResponse,
  KnowledgeDocument,
  KnowledgeSourceType,
  KnowledgeVersion,
} from '@/lib/api/types';
import { formatDateTime } from '@/lib/utils';

const SOURCE_TYPES: KnowledgeSourceType[] = ['text', 'txt', 'md', 'pdf'];

function KnowledgeWorkspace() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [departments, setDepartments] = useState<DepartmentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [approvalFilter, setApprovalFilter] = useState<'all' | 'approved' | 'pending'>('all');
  const [activeFilter, setActiveFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [busyId, setBusyId] = useState<number | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyDoc, setHistoryDoc] = useState<KnowledgeDocument | null>(null);
  const [versions, setVersions] = useState<KnowledgeVersion[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const [form, setForm] = useState({
    title: '',
    source_type: 'text' as KnowledgeSourceType,
    source_key: '',
    content: '',
    department_id: '',
  });
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const result = await knowledgeApi.list();
      setDocuments(result.items);
    } catch (cause) {
      setError(getApiErrorMessage(cause, 'Unable to load knowledge documents.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    departmentsApi
      .list()
      .then((result) => setDepartments(result.items ?? []))
      .catch(() => setDepartments([]));
  }, [load]);

  function handleFileChange(selected: File | null) {
    setFile(selected);
    setUploadError('');
    if (!selected) return;
    const extension = selected.name.split('.').pop()?.toLowerCase();
    if (extension === 'pdf' || extension === 'txt' || extension === 'md') {
      setForm((current) => ({ ...current, source_type: extension as KnowledgeSourceType }));
    }
    if (!form.title.trim()) {
      setForm((current) => ({ ...current, title: selected.name.replace(/\.[^.]+$/, '') }));
    }
  }

  async function handleUpload(event: React.FormEvent) {
    event.preventDefault();
    setUploading(true);
    setUploadError('');
    try {
      await knowledgeApi.create({
        title: form.title.trim(),
        source_type: form.source_type,
        source_key: form.source_key.trim() || undefined,
        content: form.content,
        department_id: form.department_id ? Number(form.department_id) : null,
        file,
      });
      toast.success('Knowledge document submitted for review.');
      setForm({ title: '', source_type: 'text', source_key: '', content: '', department_id: '' });
      setFile(null);
      const input = document.getElementById('knowledge-file') as HTMLInputElement | null;
      if (input) input.value = '';
      await load();
    } catch (cause) {
      setUploadError(getApiErrorMessage(cause, 'Unable to upload the document.'));
    } finally {
      setUploading(false);
    }
  }

  async function updateDocument(doc: KnowledgeDocument, payload: { is_approved?: boolean; is_active?: boolean }, message: string) {
    setBusyId(doc.id);
    try {
      await knowledgeApi.update(doc.id, payload);
      toast.success(message);
      await load();
    } catch (cause) {
      toast.error(getApiErrorMessage(cause, 'Unable to update this document.'));
    } finally {
      setBusyId(null);
    }
  }

  async function openHistory(doc: KnowledgeDocument) {
    setHistoryDoc(doc);
    setHistoryOpen(true);
    setHistoryLoading(true);
    setHistoryError('');
    try {
      setVersions(await knowledgeApi.versions(doc.id));
    } catch (cause) {
      setHistoryError(getApiErrorMessage(cause, 'Unable to load version history.'));
    } finally {
      setHistoryLoading(false);
    }
  }

  async function handleDelete() {
    if (deleteId === null) return;
    setBusyId(deleteId);
    try {
      await knowledgeApi.remove(deleteId);
      toast.success('Knowledge document deleted.');
      setDeleteId(null);
      await load();
    } catch (cause) {
      toast.error(getApiErrorMessage(cause, 'Unable to delete this document.'));
    } finally {
      setBusyId(null);
    }
  }

  const visible = documents.filter((doc) => {
    const approvalMatch =
      approvalFilter === 'all' ||
      (approvalFilter === 'approved' ? doc.is_approved : !doc.is_approved);
    const activeMatch =
      activeFilter === 'all' || (activeFilter === 'active' ? doc.is_active : !doc.is_active);
    return approvalMatch && activeMatch;
  });

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Workspace tools"
        title="Knowledge library"
        description="Upload, approve and maintain the approved sources used for grounded AI answers."
        icon={<BookOpenCheck className="h-6 w-6" aria-hidden="true" />}
      />

      <Card className="overflow-hidden">
        <div className="border-b border-slate-100 p-5 sm:p-6">
          <p className="eyebrow text-teal-700">New source</p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight text-navy-900">Upload a document</h2>
          <p className="mt-1 text-sm leading-relaxed text-slate-500">
            Paste text directly or upload a PDF, TXT or Markdown file. New sources start unapproved.
          </p>
        </div>
        <form onSubmit={handleUpload} className="grid gap-5 p-5 sm:p-6 lg:grid-cols-2">
          <div className="space-y-5">
            <div>
              <label htmlFor="knowledge-title" className="field-label">Title</label>
              <input
                id="knowledge-title"
                required
                maxLength={255}
                value={form.title}
                onChange={(event) => setForm({ ...form, title: event.target.value })}
                placeholder="e.g. Scholarship eligibility policy"
                className="field-input"
              />
            </div>
            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <label htmlFor="knowledge-type" className="field-label">Source type</label>
                <select
                  id="knowledge-type"
                  value={form.source_type}
                  onChange={(event) => setForm({ ...form, source_type: event.target.value as KnowledgeSourceType })}
                  className="field-input"
                >
                  {SOURCE_TYPES.map((type) => <option key={type} value={type}>{type.toUpperCase()}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="knowledge-department" className="field-label">Department <span className="font-normal text-slate-500">(optional)</span></label>
                <select
                  id="knowledge-department"
                  value={form.department_id}
                  onChange={(event) => setForm({ ...form, department_id: event.target.value })}
                  className="field-input"
                >
                  <option value="">All departments</option>
                  {departments.map((department) => (
                    <option key={department.id} value={String(department.id)}>{department.name}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label htmlFor="knowledge-source-key" className="field-label">Source key <span className="font-normal text-slate-500">(optional)</span></label>
              <input
                id="knowledge-source-key"
                maxLength={255}
                value={form.source_key}
                onChange={(event) => setForm({ ...form, source_key: event.target.value })}
                placeholder="Stable identifier for new versions"
                className="field-input"
              />
            </div>
          </div>

          <div className="space-y-5">
            <div>
              <label htmlFor="knowledge-content" className="field-label">Text content</label>
              <Textarea
                id="knowledge-content"
                value={form.content}
                onChange={(event) => setForm({ ...form, content: event.target.value })}
                rows={7}
                placeholder="Paste the approved policy or reference text here…"
              />
            </div>
            <div>
              <label htmlFor="knowledge-file" className="field-label">Or choose a file</label>
              <input
                id="knowledge-file"
                type="file"
                accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
                onChange={(event) => handleFileChange(event.target.files?.[0] ?? null)}
                className="field-input h-auto min-h-11 py-2.5"
                aria-describedby="knowledge-file-help"
              />
              <p id="knowledge-file-help" className="mt-1.5 text-xs text-slate-500">
                {file ? `Selected: ${file.name}` : 'PDF, TXT and Markdown files are supported.'}
              </p>
            </div>
            {uploadError ? <ErrorState compact title="Upload failed" message={uploadError} /> : null}
            <div className="flex justify-end">
              <Button type="submit" variant="teal" disabled={uploading || !form.title.trim() || (!form.content.trim() && !file)}>
                {uploading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <UploadCloud className="h-4 w-4" aria-hidden="true" />}
                {uploading ? 'Uploading…' : 'Upload source'}
              </Button>
            </div>
          </div>
        </form>
      </Card>

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-4 border-b border-slate-100 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
          <div>
            <h2 className="text-base font-semibold text-navy-900">Document library</h2>
            <p className="mt-0.5 text-xs text-slate-500">Only approved and active sources are used by AI retrieval.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <div>
              <label htmlFor="approval-filter" className="sr-only">Filter by approval</label>
              <select
                id="approval-filter"
                value={approvalFilter}
                onChange={(event) => setApprovalFilter(event.target.value as typeof approvalFilter)}
                className="field-input h-10"
              >
                <option value="all">All approval states</option>
                <option value="approved">Approved</option>
                <option value="pending">Pending approval</option>
              </select>
            </div>
            <div>
              <label htmlFor="active-filter" className="sr-only">Filter by active state</label>
              <select
                id="active-filter"
                value={activeFilter}
                onChange={(event) => setActiveFilter(event.target.value as typeof activeFilter)}
                className="field-input h-10"
              >
                <option value="all">All statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Deactivated</option>
              </select>
            </div>
          </div>
        </div>

        <div className="p-5 sm:p-6">
          {error ? <ErrorState title="Unable to load knowledge" message={error} onRetry={() => void load()} /> : null}
          {loading ? <TableSkeleton rows={5} columns={6} /> : null}
          {!loading && !error && visible.length === 0 ? (
            <EmptyState
              title={documents.length === 0 ? 'No knowledge sources yet' : 'No documents match these filters'}
              message={documents.length === 0 ? 'Upload a policy, guide or reference document to begin building the approved knowledge base.' : 'Try changing the approval or status filters.'}
              icon={<FileText className="h-5 w-5" aria-hidden="true" />}
            />
          ) : null}
          {!loading && !error && visible.length > 0 ? (
            <div className="overflow-x-auto rounded-xl border border-slate-200">
              <table className="w-full min-w-[720px] text-left text-sm" aria-label="Knowledge documents">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                    <th scope="col" className="px-4 py-3">Title</th>
                    <th scope="col" className="px-4 py-3">Version</th>
                    <th scope="col" className="px-4 py-3">Approval</th>
                    <th scope="col" className="px-4 py-3">Status</th>
                    <th scope="col" className="px-4 py-3">Added</th>
                    <th scope="col" className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {visible.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-50/70">
                      <td className="max-w-xs px-4 py-3">
                        <p className="truncate font-semibold text-navy-900">{doc.title}</p>
                        <p className="truncate text-xs text-slate-500">{doc.file_name ?? `${doc.source_type} source`}</p>
                      </td>
                      <td className="px-4 py-3 tabular-nums text-slate-700">v{doc.version}</td>
                      <td className="px-4 py-3">
                        <StatusPill
                          status={doc.is_approved ? 'completed' : 'planned'}
                          label={doc.is_approved ? 'Approved' : 'Pending'}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <StatusPill status={doc.is_active ? 'healthy' : 'closed'} label={doc.is_active ? 'Active' : 'Inactive'} />
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500">{formatDateTime(doc.created_at)}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap justify-end gap-1.5">
                          {!doc.is_approved ? (
                            <Button variant="soft" size="sm" disabled={busyId === doc.id} onClick={() => void updateDocument(doc, { is_approved: true }, 'Document approved.')}>
                              <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" /> Approve
                            </Button>
                          ) : null}
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={busyId === doc.id}
                            onClick={() => void updateDocument(doc, { is_active: !doc.is_active }, doc.is_active ? 'Document deactivated.' : 'Document reactivated.')}
                          >
                            {doc.is_active ? 'Deactivate' : 'Activate'}
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => void openHistory(doc)} aria-label={`Version history for ${doc.title}`}>
                            <History className="h-3.5 w-3.5" aria-hidden="true" /> History
                          </Button>
                          <Button variant="ghost" size="sm" className="text-rose-600 hover:bg-rose-50" onClick={() => setDeleteId(doc.id)} aria-label={`Delete ${doc.title}`}>
                            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      </Card>

      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Version history</DialogTitle>
            <DialogDescription>{historyDoc?.title} · newer versions are listed first.</DialogDescription>
          </DialogHeader>
          {historyLoading ? <div className="space-y-3"><TableSkeleton rows={3} columns={3} /></div> : null}
          {historyError ? <ErrorState compact title="History unavailable" message={historyError} /> : null}
          {!historyLoading && !historyError && versions.length === 0 ? (
            <EmptyState title="No earlier versions" message="Version records will appear when a source key is updated." />
          ) : null}
          {!historyLoading && versions.length > 0 ? (
            <ul className="space-y-2">
              {versions.map((version) => (
                <li key={version.id} className="rounded-lg border border-slate-200 bg-slate-50/60 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-navy-900">Version {version.version}</p>
                    <p className="text-xs text-slate-500">{formatDateTime(version.created_at)}</p>
                  </div>
                  <p className="mt-1 text-xs text-slate-600">{version.title ?? historyDoc?.title}</p>
                </li>
              ))}
            </ul>
          ) : null}
        </DialogContent>
      </Dialog>

      <Dialog open={deleteId !== null} onOpenChange={(open) => { if (!open) setDeleteId(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this document?</DialogTitle>
            <DialogDescription>The source will no longer be available for AI retrieval. This cannot be undone.</DialogDescription>
          </DialogHeader>
          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button variant="outline" onClick={() => setDeleteId(null)}>Cancel</Button>
            <Button variant="danger" disabled={busyId !== null} onClick={() => void handleDelete()}>
              {busyId !== null ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Trash2 className="h-4 w-4" aria-hidden="true" />}
              Delete document
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function KnowledgePage() {
  return <RoleGuard roles={['hod', 'admin']}><KnowledgeWorkspace /></RoleGuard>;
}
