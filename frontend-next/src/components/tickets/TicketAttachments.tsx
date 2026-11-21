'use client';

import { useRef, useState } from 'react';
import { FileText, Loader2, LockKeyhole, Paperclip, UploadCloud } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { EmptyState } from '@/components/common/EmptyState';
import {
  ATTACHMENT_EXTENSIONS,
  ATTACHMENT_MAX_BYTES,
  type AttachmentCreateInput,
  type AttachmentResponse,
} from '@/lib/api/types';
import { formatDateTime } from '@/lib/utils';

interface TicketAttachmentsProps {
  attachments: AttachmentResponse[];
  canUpload: boolean;
  canWriteInternal: boolean;
  busy: boolean;
  onUpload: (input: AttachmentCreateInput) => Promise<void>;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function TicketAttachments({
  attachments,
  canUpload,
  canWriteInternal,
  busy,
  onUpload,
}: TicketAttachmentsProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [messageBody, setMessageBody] = useState('');
  const [isInternal, setIsInternal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedFile) return;
    setError('');

    const extension = selectedFile.name.split('.').pop()?.toLowerCase() ?? '';
    if (!ATTACHMENT_EXTENSIONS.some((allowed) => allowed === extension)) {
      setError('Choose a PDF, TXT or Markdown file.');
      return;
    }
    if (selectedFile.size === 0) {
      setError('Choose a file that is not empty.');
      return;
    }
    if (selectedFile.size > ATTACHMENT_MAX_BYTES) {
      setError('That file is larger than 5 MiB. Choose a smaller file.');
      return;
    }

    setUploading(true);
    try {
      await onUpload({
        file: selectedFile,
        message_body: messageBody.trim(),
        is_internal: canWriteInternal && isInternal,
      });
      setSelectedFile(null);
      setMessageBody('');
      setIsInternal(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to upload this attachment.');
    } finally {
      setUploading(false);
    }
  }

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-4 sm:px-6">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-50 text-teal-700 ring-1 ring-teal-100">
            <Paperclip className="h-4 w-4" aria-hidden="true" />
          </span>
          <div>
            <h2 className="text-sm font-semibold text-navy-900">Attachments</h2>
            <p className="text-xs text-slate-500">{attachments.length} {attachments.length === 1 ? 'file' : 'files'}</p>
          </div>
        </div>
      </div>

      <div className="p-5 sm:p-6">
        {attachments.length === 0 ? (
          <EmptyState
            title="No attachments yet"
            message="Files shared on this ticket will appear here with their size and upload date."
            icon={<Paperclip className="h-5 w-5" aria-hidden="true" />}
          />
        ) : (
          <ul className="space-y-3">
            {attachments.map((attachment) => (
              <li
                key={attachment.id}
                className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-3.5"
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
                  <FileText className="h-4 w-4" aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="break-all text-sm font-medium text-navy-900">{attachment.file_name}</p>
                  <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-slate-500">
                    <span>{formatSize(attachment.size_bytes)}</span>
                    <span aria-hidden="true">·</span>
                    <span>{attachment.content_type}</span>
                    <span aria-hidden="true">·</span>
                    <time dateTime={attachment.created_at}>{formatDateTime(attachment.created_at)}</time>
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}

        {canUpload ? (
          <form onSubmit={handleSubmit} className="mt-6 space-y-3 border-t border-slate-100 pt-6">
            <label htmlFor="attachment-file" className="field-label">Attach a file</label>
            <input
              id="attachment-file"
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
              onChange={(event) => {
                setSelectedFile(event.target.files?.[0] ?? null);
                setError('');
              }}
              className="field-input h-auto min-h-11 py-2.5"
              aria-describedby="attachment-file-help"
            />
            <p id="attachment-file-help" className="text-xs text-slate-500">
              {selectedFile
                ? `Selected: ${selectedFile.name}`
                : 'PDF, TXT or Markdown files up to 5 MiB.'}
            </p>

            <label htmlFor="attachment-message" className="field-label">Message <span className="font-normal text-slate-500">(optional)</span></label>
            <Input
              id="attachment-message"
              value={messageBody}
              onChange={(event) => setMessageBody(event.target.value)}
              maxLength={10000}
              placeholder="Add context for this file…"
            />

            {canWriteInternal ? (
              <label className="flex cursor-pointer items-center gap-2.5 rounded-lg border border-slate-200 bg-slate-50/60 px-3 py-2.5 text-sm text-slate-700">
                <input
                  id="attachment-internal"
                  type="checkbox"
                  checked={isInternal}
                  onChange={(event) => setIsInternal(event.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-teal-700 focus:ring-teal-500"
                />
                <LockKeyhole className="h-4 w-4 text-amber-600" aria-hidden="true" />
                Internal attachment — visible to staff only
              </label>
            ) : null}

            {error ? <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</p> : null}

            <div className="flex justify-end">
              <Button type="submit" variant="teal" disabled={busy || uploading || !selectedFile}>
                {uploading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <UploadCloud className="h-4 w-4" aria-hidden="true" />}
                {uploading ? 'Uploading…' : 'Upload file'}
              </Button>
            </div>
          </form>
        ) : (
          <p className="mt-6 flex items-center gap-2 rounded-xl bg-slate-100 px-4 py-3 text-sm text-slate-600">
            <LockKeyhole className="h-4 w-4" aria-hidden="true" /> This ticket is closed. New attachments are disabled.
          </p>
        )}
      </div>
    </Card>
  );
}
