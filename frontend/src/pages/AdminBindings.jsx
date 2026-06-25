import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  deleteBinding,
  getProductScore,
  listBindings,
  listConnectors,
  putBinding,
  testConnector,
} from "../services/api.js";
import { CaveatList } from "../components/CaveatList.jsx";
import { Modal } from "../components/Modal.jsx";
import { Sep } from "../components/ui.jsx";

const CONNECTOR_HELP = {
  static: "Set parameters.score_0_10 (float 0–10), evidence_sources (array), confidence (high/medium/low).",
  placeholder: "Explicit no-op — score will be null with an actionable caveat.",
  loki_logql: "Set parameters.base_url (or env LOKI_BASE_URL) + query_body (LogQL). Optional: bearer_token, fallback_score_0_10.",
  prometheus_promql: "Set parameters.base_url (or PROMETHEUS_URL) + query_body (PromQL) + score_mode (raw|ratio|inverse_ratio|threshold). Optional: threshold, fallback_score_0_10.",
  postgres_sql: "Set DATABASE_URL env + query_body (SELECT returning one numeric). Optional: fallback_score_0_10.",
  sonarqube_rest: "Set parameters.base_url (or SONARQUBE_URL) + token + project_key. Optional: fallback_score_0_10.",
  snyk_rest: "Set parameters.token (or SNYK_TOKEN) + org_id (or SNYK_ORG_ID). Optional: project_id, fallback_score_0_10.",
  trivy_json: "Set parameters.report_url (HTTP/S to JSON report) OR report_path (absolute server path). Optional: fallback_score_0_10.",
  github_rest: "Set parameters.token (or GITHUB_TOKEN). Optional: api_base (for GHE), fallback_score_0_10.",
};

function ConnectorGuide({ connectorId, allConnectors }) {
  const meta = allConnectors.find((c) => c.id === connectorId);
  const help = CONNECTOR_HELP[connectorId] || "See docs/API.md for this connector.";
  if (!meta) return <p className="muted">{help}</p>;
  return (
    <div>
      <p className="muted" style={{ marginTop: 0 }}>
        <strong>{meta.label}</strong> — {meta.description}
      </p>
      <p className="muted">{meta.when_to_use}</p>
      {meta.required_env?.length ? (
        <div className="kv" style={{ marginBottom: "0.35rem" }}>
          <b>Required env</b>
          <span className="mono">{meta.required_env.join(", ")}</span>
        </div>
      ) : null}
      {meta.required_params?.length ? (
        <div className="kv">
          <b>Key params</b>
          <span className="mono">{meta.required_params.join(", ")}</span>
        </div>
      ) : null}
    </div>
  );
}

export function AdminBindings() {
  const { productId } = useParams();
  const [bindings, setBindings] = useState({});
  const [rows, setRows] = useState([]);
  const [allConnectors, setAllConnectors] = useState([]);
  const [selected, setSelected] = useState(null);
  const [editor, setEditor] = useState("");
  const [testResult, setTestResult] = useState(null);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!productId) return;
    setErr("");
    Promise.all([
      getProductScore(productId),
      listBindings(productId),
      listConnectors(),
    ])
      .then(([snap, b, connectors]) => {
        setBindings(b || {});
        setAllConnectors(connectors || []);
        const flat = [];
        for (const d of snap.dimensions || []) {
          for (const s of d.subdimensions || []) flat.push({ dimension: d, sub: s });
        }
        setRows(flat);
      })
      .catch((e) => setErr(String(e.message || e)));
  }, [productId]);

  function openEditor(row) {
    setSelected(row);
    const existing = bindings[row.sub.id];
    const seed = existing || {
      connector_id: "static",
      dialect: "sql",
      query_body: "",
      parameters: {
        score_0_10: row.sub.score_0_10 ?? 5.0,
        evidence_sources: row.sub.evidence_sources || [],
        confidence: "medium",
      },
      schedule_cron: "0 */6 * * *",
      filters: {},
    };
    setEditor(JSON.stringify(seed, null, 2));
    setTestResult(null);
    setMsg("");
    setErr("");
  }

  async function save() {
    if (!selected) return;
    setErr(""); setMsg("");
    try {
      const body = JSON.parse(editor);
      await putBinding(productId, selected.sub.id, body);
      setMsg("Saved.");
      setBindings(await listBindings(productId));
    } catch (e) { setErr(String(e.message || e)); }
  }

  async function runTest() {
    setErr(""); setTestResult(null);
    try {
      const body = JSON.parse(editor);
      setTestResult(await testConnector(body));
    } catch (e) { setErr(String(e.message || e)); }
  }

  async function removeRow() {
    if (!selected) return;
    setErr(""); setMsg("");
    try {
      await deleteBinding(productId, selected.sub.id);
      setMsg("Removed.");
      setBindings(await listBindings(productId));
      setSelected(null);
    } catch (e) { setErr(String(e.message || e)); }
  }

  const selectedConnectorId = (() => {
    try { return JSON.parse(editor)?.connector_id || ""; } catch { return ""; }
  })();

  return (
    <div className="page">
      <p className="muted" style={{ marginTop: 0 }}>
        <Link to={`/product/${productId}`}>← Portfolio</Link>
        {" · "}
        <Link to={`/product/${productId}/admin/connectors`}>Connector catalog</Link>
      </p>

      <div className="card card-strong">
        <h1 className="h1" style={{ marginBottom: "0.35rem" }}>Connector bindings</h1>
        <p className="muted">
          Wire each sub-dimension to a data source. Changes persist to{" "}
          <span className="mono">local/demo-data/bindings.json</span> (gitignored).
          Registered connectors: <span className="mono">{allConnectors.map((c) => c.id).join(", ")}</span>.
        </p>
        {err ? <p className="err">{err}</p> : null}
        {msg ? <p className="muted">{msg}</p> : null}
      </div>

      <div className="card" style={{ marginTop: "1rem" }}>
        <table className="sub-table">
          <thead>
            <tr>
              <th>Dimension</th>
              <th>Sub-dimension</th>
              <th>Connector</th>
              <th>Score</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const b = bindings[r.sub.id];
              return (
                <tr key={r.sub.id}>
                  <td className="muted">{r.dimension.title}</td>
                  <td>
                    <strong>{r.sub.title}</strong>
                    <div className="mono" style={{ color: "var(--muted)", marginTop: "0.15rem", fontSize: "0.78rem" }}>
                      {r.sub.id}
                    </div>
                  </td>
                  <td className="mono" style={{ fontSize: "0.82rem" }}>{b?.connector_id || "—"}</td>
                  <td style={{ fontWeight: 800 }}>{r.sub.score_0_10 ?? "—"}</td>
                  <td>
                    <button type="button" className="icon-btn" onClick={() => openEditor(r)}>Edit</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <Modal
        open={Boolean(selected)}
        wide
        title={selected ? `Binding: ${selected.sub.id}` : ""}
        onClose={() => setSelected(null)}
      >
        {selected ? (
          <div>
            {selectedConnectorId && (
              <div className="caveat" style={{ marginBottom: "0.75rem" }}>
                <div className="caveat-title">Connector guide — {selectedConnectorId}</div>
                <ConnectorGuide connectorId={selectedConnectorId} allConnectors={allConnectors} />
              </div>
            )}
            <textarea
              className="textarea mono"
              value={editor}
              onChange={(e) => setEditor(e.target.value)}
            />
            {err ? <p className="err">{err}</p> : null}
            {msg ? <p className="muted">{msg}</p> : null}
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "0.65rem" }}>
              <button type="button" className="btn btn-small" onClick={save}>Save binding</button>
              <button type="button" className="btn btn-ghost btn-small" onClick={runTest}>Test connector</button>
              <button type="button" className="btn btn-ghost btn-small" onClick={removeRow}>Remove</button>
            </div>
            {testResult ? (
              <div style={{ marginTop: "0.85rem" }}>
                <Sep />
                <div className="h2" style={{ marginBottom: "0.35rem" }}>
                  Test result — {testResult.ok ? "✓ ok" : "⚠ issues"}
                </div>
                <div className="kv"><b>Score preview</b><span style={{ fontWeight: 800 }}>{testResult.preview?.score_0_10 ?? "—"}</span></div>
                <div className="kv" style={{ marginTop: "0.35rem" }}>
                  <b>Confidence</b><span className="mono">{testResult.preview?.confidence}</span>
                </div>
                <div className="kv" style={{ marginTop: "0.35rem" }}>
                  <b>Sources</b>
                  <span className="mono">{(testResult.preview?.evidence_sources || []).join(", ") || "—"}</span>
                </div>
                <div style={{ marginTop: "0.65rem" }}>
                  <CaveatList items={testResult.caveats || []} />
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
