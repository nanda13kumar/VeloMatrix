import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getHealth, getProductScore } from "../services/api.js";
import { CaveatList } from "../components/CaveatList.jsx";
import { bandClass, Chip } from "../components/ui.jsx";

export function Overview() {
  const { productId } = useParams();
  const [score, setScore] = useState(null);
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => { getHealth().then(setHealth).catch(() => {}); }, []);

  useEffect(() => {
    if (!productId) return;
    setError("");
    getProductScore(productId).then(setScore).catch((e) => setError(String(e.message || e)));
  }, [productId]);

  const fillDeg = useMemo(() => {
    const v = score?.overall_0_10;
    if (v == null) return 0;
    return Math.max(0, Math.min(360, (Number(v) / 10) * 360));
  }, [score]);

  return (
    <div className="page">
      <div className="grid-hero">
        <div className="card card-strong">
          <div className="score-layout">
            <div
              className="score-ring"
              style={{
                background: `conic-gradient(from -90deg, #7b6fd6 ${fillDeg}deg, var(--ring-track) 0deg)`,
              }}
            >
              <div className="score-ring-inner">
                <div className="score-ring-value">{score?.overall_0_10 ?? "—"}</div>
                <div className="score-ring-label">Overall /10</div>
              </div>
            </div>
            <div>
              <h1 className="h1" style={{ marginBottom: "0.35rem" }}>
                {score?.product_name || "Product"}
              </h1>
              <div className="muted">
                Policy <span className="mono">{score?.policy_version ?? "—"}</span>
                {health ? <> · GenAI <strong>{health.genai_mode}</strong></> : null}
              </div>
              <p className="muted" style={{ marginTop: "0.75rem" }}>
                The ring represents the weighted 0–10 roll-up — not a regulatory certification.
                Dimension cards show <em>Sit → Run</em> bands from sub-dimension evidence.
                Every payload ships caveats; read them before acting on any number.
              </p>
              <CaveatList items={score?.caveats || []} />
            </div>
          </div>
        </div>
        <div className="card">
          <h2 className="h2" style={{ marginBottom: "0.35rem" }}>How scoring works</h2>
          <p className="muted">
            Sub-dimensions are scored 0–10 by connector plugins (Sonar, Snyk, Trivy, Prometheus, Loki, Postgres, GitHub…).
            Each carries a weight (0.1–1.0). Dimension numeric = weighted mean of sub-scores.
            Product score = Σ (dimension numeric × dimension weight).
            Bands map from numeric: &lt;2.5 Sit, &lt;5 Crawl, &lt;7.5 Walk, else Run.
          </p>
          <div className="sep" />
          <p className="muted" style={{ margin: 0 }}>
            Interactive OpenAPI: run the API and visit <span className="mono">/docs</span>.
          </p>
        </div>
      </div>

      <div className="grid-dims">
        {(score?.dimensions || []).map((d) => (
          <Link key={d.id} to={`/product/${productId}/dimension/${d.id}`} style={{ textDecoration: "none" }}>
            <div className="card dim-card" style={{ cursor: "pointer", height: "100%" }}>
              <div className="dim-top">
                <div>
                  <h3 className="h2" style={{ marginBottom: "0.25rem" }}>{d.title}</h3>
                  <div className="muted" style={{ minHeight: "2.75rem" }}>{d.description}</div>
                </div>
                <span className={bandClass(d.band)}>{d.band}</span>
              </div>
              {d.dimension_importance
                ? <p className="muted" style={{ marginTop: "0.65rem" }}>{d.dimension_importance}</p>
                : null}
              <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                <Chip>numeric {d.numeric_0_10 != null ? `${d.numeric_0_10}/10` : "n/a"}</Chip>
                <Chip>weight {d.weight}</Chip>
                <Chip>{d.subdimensions?.length || 0} sub-dims</Chip>
              </div>
              <CaveatList items={d.caveats || []} />
            </div>
          </Link>
        ))}
      </div>
      {error ? <p className="err">{error}</p> : null}
    </div>
  );
}
