import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getEvidenceLog, listEvidenceSubdims } from "../services/api.js";
import { CaveatList } from "../components/CaveatList.jsx";
import { Modal } from "../components/Modal.jsx";

export function AdminEvidence() {
  const { productId } = useParams();
  const [subdims, setSubdims] = useState([]);
  const [selected, setSelected] = useState(null);
  const [log, setLog] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!productId) return;
    listEvidenceSubdims(productId)
      .then(setSubdims)
      .catch((e) => setErr(String(e.message || e)));
  }, [productId]);

  async function openLog(sid) {
    setSelected(sid);
    setLog([]);
    setErr("");
    try {
      const records = await getEvidenceLog(productId, sid, 20);
      setLog(records);
    } catch (e) {
      setErr(String(e.message || e));
    }
  }

  return (
    <div className="page">
      <p className="muted" style={{ marginTop: 0 }}>
        <Link to={`/product/${productId}`}>← Portfolio</Link>
        {" · "}
        <Link to={`/product/${productId}/admin/bindings`}>Bindings</Link>
      </p>

      <div className="card card-strong">
        <h1 className="h1" style={{ marginBottom: "0.35rem" }}>Evidence ledger</h1>
        <p className="muted">
          Every connector collect run is appended to a per-sub-dimension NDJSON log
          under <span className="mono">local/demo-data/evidence/</span> (gitignored).
          This ledger provides provenance — when was a score computed, from which connector,
          with what confidence and what caveats.
        </p>
        {err ? <p className="err">{err}</p> : null}
      </div>

      {subdims.length ? (
        <div className="card" style={{ marginTop: "1rem" }}>
          <table className="sub-table">
            <thead>
              <tr>
                <th>Sub-dimension ID</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {subdims.map((sid) => (
                <tr key={sid}>
                  <td className="mono">{sid}</td>
                  <td>
                    <button type="button" className="icon-btn" onClick={() => openLog(sid)}>
                      View log
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="card" style={{ marginTop: "1rem" }}>
          <p className="muted">
            No evidence records yet. Load the portfolio page to trigger connector collection runs,
            then return here.
          </p>
        </div>
      )}

      <Modal
        open={Boolean(selected)}
        wide
        title={selected ? `Evidence log: ${selected}` : ""}
        onClose={() => setSelected(null)}
      >
        {selected ? (
          <div>
            <p className="muted" style={{ marginTop: 0 }}>
              Last 20 collect runs — newest first. Each row is one call to the connector plugin.
            </p>
            {log.length ? (
              log.map((r, i) => (
                <div
                  key={i}
                  className="caveat"
                  style={{ marginBottom: "0.55rem" }}
                >
                  <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "0.35rem" }}>
                    <span className="mono" style={{ fontSize: "0.8rem" }}>{r.ts}</span>
                    <span className="chip">{r.connector_id}</span>
                    <span className="chip">score {r.score_0_10 ?? "n/a"}</span>
                    <span className="chip">{r.confidence}</span>
                  </div>
                  <div className="kv">
                    <b>Sources</b>
                    <span className="mono" style={{ fontSize: "0.82rem" }}>
                      {(r.evidence_sources || []).join(", ") || "—"}
                    </span>
                  </div>
                  <div className="kv" style={{ marginTop: "0.25rem" }}>
                    <b>Notes</b>
                    <span className="mono" style={{ fontSize: "0.82rem" }}>{r.connector_notes || "—"}</span>
                  </div>
                  <CaveatList items={r.caveats || []} />
                </div>
              ))
            ) : (
              <p className="muted">No records yet for this sub-dimension.</p>
            )}
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
