'use client';

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: 'sans-serif', padding: 32 }}>
        <h1>Application error</h1>
        <p>{error.message}</p>
        <button type="button" onClick={reset}>Try again</button>
      </body>
    </html>
  );
}
