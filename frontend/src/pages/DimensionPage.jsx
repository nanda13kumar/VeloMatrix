import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { explainSubdimension, getProductScore } from "../services/api.js";
import { CaveatList } from "../components/CaveatList.jsx";
import { Modal } from "../components/Modal.jsx";
import { bandClass, Chip, Sep } from "../components/ui.jsx";

function SubDetailModal({ sub, onClose }) {
  return (
    <Modal open={Boolean(sub)} title={sub?.title || ""} onClose={onClose}>
      {sub ? (
        <div>
          <p className="muted">{sub.description}</p>
          <Sep />
          <div className="kv"><b>Why it matters</b><span>{sub.importance_rationale || "—"}</span></div>
          <div className="kv" style={{ marginTop: "0.5rem" }}>
            <b>Weight rationale</b><span>{sub.weight_rationale || "—"}</span>
          </div>
          <div className="kv" style={{ marginTop: "0.5rem" }}>
            <b>Guide</b><span>{sub.guide_overview || "—"}</span>
          </div>
          <div style={{ marginTop: "0.65rem" }}>
            <div className="muted" style={{ fontWeight: 800, marginBottom: "0.25rem" }}>Signals to look for</div>
            <div className="chips">
              {(sub.guide_signals || []).map((x) => <span key={x} className="chip">{x}</span>)}
              {!(sub.guide_signals || []).length ? <span className="muted">—</span> : null}
            </div>
          </div>
          <Sep />
          <div className="kv">
            <b>Non-negotiable</b>
            <span>{sub.non_negotiable ? "Yes — treat gaps as hard risk." : "No — optimise with context."}</span>
          </div>
          <div className="kv" style={{ marginTop: "0.5rem" }}>
            <b>Trade-offs</b><span>{sub.tradeoff_summary || "—"}</span>
          </div>
          <div className="kv" style={{ marginTop: "0.5rem" }}>
            <b>Evidence sources</b>
            <span className="mono">{(sub.evidence_sources || []).join(", ") || "—"}</span>
          </div>
          <div className="kv" style={{ marginTop: "0.5rem" }}>
            <b>Confidence</b><span className="mono">{sub.confidence}</span>
          </div>
          <div className="kv" style={{ marginTop: "0.5rem" }}>
            <b>Last updated</b>
            <span className="muted">{sub.last_evidence_at ? new Date(sub.last_evidence_at).toLocaleString() : "—"}</span>
          </div>
        </div>
      ) : null}
    </Modal>
  );
}

export function DimensionPage() {
  const { productId, dimensionId } = useParams();
  const [score, setScore] = useState(null);
  const [modal, setModal] = useState(null);
  const [aiBySub, setAiBySub] = useState({});
  const [error, setError] = useState("");

  useEffect(() => {
    if (!productId) return;
    getProductScore(productId).then(setScore).catch((e) => setError(String(e.message || e)));
  }, [productId]);

  const dim = useMemo(
    () => score?.dimensions?.find((d) => d.id === dimensionId),
    [score, dimensionId]
  );

  async function askGenAi(sub) {
    const sid = sub.id;
    setAiBySub((m) => ({ ...m, [sid]: "…thinking…" }));
    try {
      const res = await explainSubdimension(productId, {
        subdimension_id: sid,
        question: "Explain trade-offs, non-negotiables, and the top improvement for an engineering lead.",
        context: {
          dimension_title: dim?.title,
          sub_title: sub.title,
          guide_overview: sub.guide_overview,
          importance: sub.importance_rationale,
          weight_rationale: sub.weight_rationale,
          tradeoff: sub.tradeoff_summary,
          non_negotiable: sub.non_negotiable,
          evidence_sources: sub.evidence_sources,
          score_0_10: sub.score_0_10,
        },
      });
      setAiBySub((m) => ({ ...m, [sid]: res.answer || JSON.stringify(res) }));
    } catch (e) {
      setAiBySub((m) => ({ ...m, [sid]: String(e.message || e) }));
    }
  }

  if (!dim) {
    return (
      <div className="page">
        <div className="card">
          <p className="muted">Loading or dimension not found…</p>
          {error ? <p className="err">{error}</p> : null}
          <Link to={`/product/${productId}`}>← Portfolio</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <p className="muted" style={{ marginTop: 0 }}>
        <Link to={`/product/${productId}`}>← Portfolio</Link>
      </p>

      <div className="card card-strong" style={{ marginBottom: "1rem" }}>
        <div className="dim-top">
          <div>
            <h1 className="h1" style={{ marginBottom: "0.35rem" }}>{dim.title}</h1>
            <p className="muted" style={{ margin: 0 }}>{dim.description}</p>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
            <span className={bandClass(dim.band)}>{dim.band}</span>
            <Chip>numeric {dim.numeric_0_10 ?? "—"}/10</Chip>
            <Chip>weight {dim.weight}</Chip>
          </div>
        </div>
        {dim.dimension_importance
          ? <p className="muted">{dim.dimension_importance}</p>
          : null}
        <CaveatList items={dim.caveats || []} />
      </div>

      <div className="card">
        <h2 className="h2" style={{ marginBottom: "0.5rem" }}>Sub-dimensions — evidence & weights</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Each row is a measurable facet scored by a connector plugin. Hit{" "}
          <strong>Details</strong> for the full rationale (importance, weight justification, signals, trade-offs).
          Hit <strong>Ask GenAI</strong> for a contextual explanation tailored to this sub-dimension.
        </p>

        {dim.subdimensions?.length ? (
          <table className="sub-table">
            <thead>
              <tr>
                <th>Sub-dimension</th>
                <th>Score /10</th>
                <th>Weight</th>
                <th>Weighted contribution</th>
                <th>Sources</th>
                <th>Next check</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {dim.subdimensions.map((s) => (
                <tr key={s.id}>
                  <td>
                    <div>
                      <strong>{s.title}</strong>
                      {s.non_negotiable
                        ? <span className="pill warn" style={{ marginLeft: "0.4rem" }}>Non-negotiable</span>
                        : null}
                      <div className="muted" style={{ fontSize: "0.82rem", marginTop: "0.2rem" }}>
                        {s.tradeoff_summary}
                      </div>
                      <CaveatList items={s.caveats || []} />
                      {aiBySub[s.id] ? (
                        <div className="caveat" style={{ marginTop: "0.5rem" }}>
                          <div className="caveat-title">GenAI insight (stub)</div>
                          <div className="muted" style={{ color: "var(--text-soft)", whiteSpace: "pre-wrap" }}>
                            {aiBySub[s.id]}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </td>
                  <td style={{ fontWeight: 800 }}>{s.score_0_10 ?? "—"}</td>
                  <td>{s.weight}</td>
                  <td className="muted">{s.weighted_contribution != null ? s.weighted_contribution.toFixed(3) : "—"}</td>
                  <td className="muted" style={{ fontSize: "0.82rem" }}>
                    {(s.evidence_sources || []).join(", ") || "—"}
                  </td>
                  <td className="muted" style={{ fontSize: "0.82rem" }}>
                    {s.next_check_at ? new Date(s.next_check_at).toLocaleString() : "—"}
                  </td>
                  <td>
                    <div className="row-actions">
                      <button type="button" className="icon-btn" onClick={() => setModal(s)}>
                        Details
                      </button>
                      <button type="button" className="btn btn-small" onClick={() => askGenAi(s)}>
                        Ask GenAI
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">No sub-dimensions configured in the catalog for this dimension.</p>
        )}
      </div>

      <SubDetailModal sub={modal} onClose={() => setModal(null)} />
    </div>
  );
}
