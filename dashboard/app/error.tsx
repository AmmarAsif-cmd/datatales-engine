"use client"; // Error boundaries must be Client Components

/** Any page error renders this instead of crashing the Worker (Cloudflare error 1101). */
export default function PageError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  return (
    <div className="panel">
      <h1>Something went wrong</h1>
      <p>This page could not be loaded. The details are in the Worker logs.</p>
      {error.digest && (
        <p className="small muted">
          Reference: <code>{error.digest}</code>
        </p>
      )}
      <button type="button" onClick={() => retry()}>
        Try again
      </button>
    </div>
  );
}
