"use client"; // Error boundaries must be Client Components

/** Errors in the root layout itself: a minimal, self-contained page (no global CSS here). */
export default function GlobalError({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  return (
    <html lang="en-GB">
      <body style={{ fontFamily: "system-ui, sans-serif", padding: "1.5rem", maxWidth: "40rem" }}>
        <title>DataTales review: error</title>
        <h1>Something went wrong</h1>
        <p>The dashboard could not start this page. The details are in the Worker logs.</p>
        {error.digest && (
          <p>
            Reference: <code>{error.digest}</code>
          </p>
        )}
        <button type="button" onClick={() => retry()}>
          Try again
        </button>
      </body>
    </html>
  );
}
