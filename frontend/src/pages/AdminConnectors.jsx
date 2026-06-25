import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { listConnectors } from "../services/api.js";
import { Modal } from "../components/Modal.jsx";
import { Sep } from "../components/ui.jsx";

export function AdminConnectors() {
  const { productId } = useParams();
  const [connectors, setConnectors] = useState([]);
  const [selected, setSelected] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    listConnectors()
      .then(setConnectors)
      .catch((e) => setErr(String(e.message || e)));
  }, []);

  return (
    <div className="page">
      <p className="muted" style={{ marginTop: 0 }}>
        <Link to={`/product/${productId}`}>← Portfolio</Link>
        {" · "}
        <Link to={`/product/${productId}/admin/bindings`}>Connector bindings</Link>
      </p>

      <div className="card card-strong">
        <h1 className="h1" style={{ marginBottom: "0.35rem" }}>Connector catalog</h1>
        <p className="muted">
          Every registered connector plugin that can back a sub-dimension. Click a row to see the full
          guide: when to use it, required env vars, parameters, and integration notes.
        </p>
        {err ? <p className="err">{err}</p> : null}
      </div>

      <div className="card" style={{ marginTop: "1rem" }}>
        <table className="sub-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Label</th>
              <th>Description</th>
              <th>Required env</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {connectors.map((c) => (
              <tr key={c.id}>
                <td className="mono" style={{ fontSize: "0.82rem" }}>{c.id}</td>
                <td><strong>{c.label}</strong></td>
                <td className="muted" style={{ fontSize: "0.86rem" }}>{c.description}</td>
                <td className="muted" style={{ fontSize: "0.82rem" }}>
                  {(c.required_env || []).join(", ") || "—"}
                </td>
                <td>
                  <button type="button" className="icon-btn" onClick={() => setSelected(c)}>Guide</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal open={Boolean(selected)} title={selected ? `${selected.label} (${selected.id})` : ""} onClose={() => setSelected(null)}>
        {selected ? (
          <div>
            <p className="muted">{selected.description}</p>
            <Sep />
            <div className="kv"><b>When to use</b><span>{selected.when_to_use || "—"}</span></div>
            <div className="kv" style={{ marginTop: "0.5rem" }}>
              <b>Required env</b>
              <span className="mono">{(selected.required_env || []).join(", ") || "none"}</span>
            </div>
            <div className="kv" style={{ marginTop: "0.5rem" }}>
              <b>Key parameters</b>
              <span className="mono">{(selected.required_params || []).join(", ") || "—"}</span>
            </div>
            <Sep />
            <p className="muted" style={{ margin: 0, fontSize: "0.86rem" }}>
              Full implementation: <span className="mono">backend/src/adapters/connectors/{selected.id.replace(/_/g, "_")}.py</span>.
              Use the <strong>Connector bindings</strong> page to wire this connector to a sub-dimension and hit
              <strong> Test connector</strong> to get a live preview with caveats.
            </p>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
