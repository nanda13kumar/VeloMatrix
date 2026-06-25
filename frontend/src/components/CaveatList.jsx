export function caveatClass(c) {
  if (c.severity === "error") return "caveat caveat-sev-error";
  if (c.severity === "warn") return "caveat caveat-sev-warn";
  return "caveat";
}

export function CaveatList({ items }) {
  if (!items?.length) return null;
  return (
    <div>
      {items.map((c) => (
        <div key={`${c.code}-${c.message}`} className={caveatClass(c)}>
          <div className="caveat-title">{c.title || c.code}</div>
          <div className="muted" style={{ color: "var(--text-soft)" }}>
            {c.message}
          </div>
          {(c.remediation || (c.references || []).length > 0) && (
            <div className="caveat-meta">
              {c.remediation ? (
                <div className="kv">
                  <b>Remediation</b>
                  <span>{c.remediation}</span>
                </div>
              ) : null}
              {(c.references || []).length ? (
                <div className="kv">
                  <b>Refs</b>
                  <span className="mono">{(c.references || []).join(", ")}</span>
                </div>
              ) : null}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
