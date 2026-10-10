import type { VerifyReport as Report } from "@/lib/types";

const CLAIM_LABEL: Record<string, string> = {
  ok: "ok",
  mismatch: "number not from its keys",
  sentence_not_found: "sentence not in text",
  unknown_keys: "unknown key",
};

export default function VerifyReport({ report }: { report: Report | null }) {
  if (!report) return <p className="muted">Not verified yet. Paste a narration reply.</p>;
  const badClaims = report.claims.filter((c) => c.status !== "ok");
  return (
    <div>
      <p className="row">
        <span className={`badge ${report.status === "passed" ? "ok" : "bad"}`}>
          {report.status.toUpperCase()}
        </span>
        <span className="small muted">
          {report.checked} numbers checked · {report.claims.length} claims ({badClaims.length}{" "}
          failing) · data years {report.data_years.join("–")}
        </span>
      </p>

      {!report.claims_checked && (
        <p className="msg bad">No claims were supplied, so claim-level checks did not run.</p>
      )}

      {report.unmatched.length > 0 && (
        <>
          <h3>Numbers not found anywhere in the data</h3>
          <ul>
            {report.unmatched.map((u, i) => (
              <li key={i}>
                <code>{u.text}</code> in <b>{u.field}</b>
              </li>
            ))}
          </ul>
        </>
      )}

      {report.years_out_of_range.length > 0 && (
        <>
          <h3>Years outside the data period</h3>
          <ul>
            {report.years_out_of_range.map((y, i) => (
              <li key={i}>
                <code>{y.text}</code> in <b>{y.field}</b> (data covers {y.allowed.join("–")})
              </li>
            ))}
          </ul>
        </>
      )}

      {report.uncovered.length > 0 && (
        <>
          <h3>Numbers outside any claim</h3>
          <table>
            <thead>
              <tr>
                <th>Number</th>
                <th>Field</th>
                <th>Sentence</th>
              </tr>
            </thead>
            <tbody>
              {report.uncovered.map((u, i) => (
                <tr key={i} className="claim-bad">
                  <td>
                    <code>{u.text}</code>
                  </td>
                  <td>{u.field}</td>
                  <td>{u.sentence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {report.claims.length > 0 && (
        <>
          <h3>Claims</h3>
          <table>
            <thead>
              <tr>
                <th style={{ width: "9rem" }}>Status</th>
                <th>Sentence</th>
                <th>Numbers → keys</th>
              </tr>
            </thead>
            <tbody>
              {report.claims.map((c, i) => (
                <tr key={i} className={c.status === "ok" ? undefined : "claim-bad"}>
                  <td>
                    <span className={`badge ${c.status === "ok" ? "ok" : "bad"}`}>
                      {CLAIM_LABEL[c.status] ?? c.status}
                    </span>
                    {c.fields.length > 0 && (
                      <div className="small muted">{c.fields.join(", ")}</div>
                    )}
                  </td>
                  <td className="sentence">{c.sentence}</td>
                  <td>
                    {c.numbers.map((n, j) => (
                      <span key={j} className={`num-chip ${n.key ? "" : "missing"}`}>
                        {n.text} → {n.key ?? "no matching key"}
                      </span>
                    ))}
                    {c.unknown_keys && (
                      <div className="small">
                        Unknown: <code>{c.unknown_keys.join(", ")}</code>
                      </div>
                    )}
                    {c.status === "mismatch" && c.key_values && (
                      <div className="small muted">
                        Keys given:{" "}
                        {Object.entries(c.key_values)
                          .map(([k, v]) => `${k} = ${v}`)
                          .join("; ")}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
