export default function LoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="flex flex-col items-center gap-4">
        <div
          className="h-10 w-10 animate-spin rounded-full border-4 border-navy-100 border-t-teal-600"
          role="status"
          aria-label="Loading"
        />
        <p className="text-sm font-medium text-navy-700">Loading workspace…</p>
      </div>
    </div>
  );
}
