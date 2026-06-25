import { useEffect, useState } from "react";
import { Link, NavLink, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";

import { config, getAdminKey, setAdminKey } from "./config.js";
import { getBootstrap, listProducts } from "./services/api.js";
import { Modal } from "./components/Modal.jsx";
import { Overview } from "./pages/Overview.jsx";
import { DimensionPage } from "./pages/DimensionPage.jsx";
import { AdminBindings } from "./pages/AdminBindings.jsx";
import { AdminConnectors } from "./pages/AdminConnectors.jsx";
import { AdminEvidence } from "./pages/AdminEvidence.jsx";

function useTheme() {
  const [theme, setTheme] = useState(() => localStorage.getItem("vm-theme") || "light");
  useEffect(() => {
    document.documentElement.dataset.theme = theme === "dark" ? "dark" : "light";
    localStorage.setItem("vm-theme", theme);
  }, [theme]);
  return [theme, setTheme];
}

function AdminKeyModal({ open, onClose, authEnabled }) {
  const [val, setVal] = useState(getAdminKey);
  function save() { setAdminKey(val.trim()); onClose(); }
  return (
    <Modal open={open} title="Admin API key" onClose={onClose}>
      <p className="muted">
        {authEnabled
          ? "This VeloMatrix instance has admin auth enabled. Provide the X-VeloMatrix-Admin-Key to access admin endpoints."
          : "Admin auth is not configured (open dev mode). You can still set a key here if needed."}
      </p>
      <input
        type="password"
        className="input"
        style={{ width: "100%", marginBottom: "0.65rem" }}
        placeholder="Paste API key…"
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") save(); }}
      />
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button type="button" className="btn btn-small" onClick={save}>Save (session)</button>
        <button type="button" className="btn btn-ghost btn-small" onClick={() => { setAdminKey(""); setVal(""); onClose(); }}>
          Clear
        </button>
      </div>
    </Modal>
  );
}

function FirstProductRedirect() {
  const [target, setTarget] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    listProducts()
      .then((ps) => {
        setTarget(ps?.length ? `/product/${encodeURIComponent(ps[0].id)}` : "/no-catalog");
      })
      .catch((e) => setErr(String(e.message || e)));
  }, []);
  if (err) {
    return (
      <div className="page">
        <div className="card">
          <p className="err">{err}</p>
          <p className="muted">Start the API and run <span className="mono">python3 scripts/seed_local_demo.py</span>.</p>
        </div>
      </div>
    );
  }
  if (!target) return <div className="page"><div className="muted">Loading…</div></div>;
  return <Navigate to={target} replace />;
}

function NoCatalog() {
  return (
    <div className="page">
      <div className="card card-strong">
        <h1 className="h1" style={{ marginBottom: "0.35rem" }}>No local policy yet</h1>
        <p className="muted">
          VeloMatrix reads <span className="mono">local/demo-data/catalog.json</span> and{" "}
          <span className="mono">bindings.json</span> (gitignored). Generate them from the repo root:
        </p>
        <pre className="mono" style={{ padding: "0.75rem", borderRadius: 12, border: "1px solid var(--line)", overflow: "auto" }}>
          python3 scripts/seed_local_demo.py
        </pre>
        <p className="muted" style={{ marginTop: "0.75rem" }}>
          Then refresh — you'll get full dimensions, sub-dimensions, weighted scoring, and connector bindings.
        </p>
      </div>
    </div>
  );
}

function Sidebar({ productId, dataLayout }) {
  const na = (path, label, end = false) => (
    <NavLink
      className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
      to={path}
      end={end}
    >
      {label}
    </NavLink>
  );

  return (
    <aside className="sidebar">
      <div className="side-brand">
        <strong>{config.appName}</strong>
        <span>{config.tagline}</span>
      </div>
      <div className="nav-section">Portfolio</div>
      {na(`/product/${productId}`, "Overview", true)}
      <div className="nav-section" style={{ marginTop: "0.75rem" }}>Admin</div>
      {na(`/product/${productId}/admin/bindings`, "Connector bindings")}
      {na(`/product/${productId}/admin/connectors`, "Connector catalog")}
      {na(`/product/${productId}/admin/evidence`, "Evidence ledger")}
      <div className="muted" style={{ fontSize: "0.78rem", padding: "0.5rem", marginTop: "auto" }}>
        {dataLayout ? (
          <>
            <div>catalog: <strong>{dataLayout.catalog_present ? "yes" : "no"}</strong>{" "}
              bindings: <strong>{dataLayout.bindings_present ? "yes" : "no"}</strong>
            </div>
            <div style={{ marginTop: "0.25rem" }}>
              auth: <strong>{dataLayout.admin_auth_enabled ? "on" : "off"}</strong>
            </div>
            <div className="mono" style={{ wordBreak: "break-all", marginTop: "0.25rem", fontSize: "0.72rem" }}>
              {dataLayout.data_base_path}
            </div>
          </>
        ) : null}
      </div>
    </aside>
  );
}

function Layout({ children, productId, products, theme, setTheme, onProductChange, dataLayout, onAdminKey }) {
  return (
    <div className="shell">
      <Sidebar productId={productId} dataLayout={dataLayout} />
      <div className="layout-main">
        <header className="topbar">
          <div className="topbar-left">
            <span className="pill">Portfolio</span>
            <div className="muted" style={{ fontSize: "0.85rem" }}>
              Weighted 0–10 roll-up · Sit→Run bands
            </div>
          </div>
          <div className="topbar-actions">
            <label className="muted" htmlFor="product-select">Product</label>
            <select
              id="product-select"
              className="select"
              value={productId}
              onChange={(e) => onProductChange(e.target.value)}
            >
              {products.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <button type="button" className="btn btn-ghost btn-small" onClick={onAdminKey}>
              Admin key {getAdminKey() ? "✓" : "—"}
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-small"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            >
              {theme === "dark" ? "Light" : "Dark"}
            </button>
          </div>
        </header>
        {children}
      </div>
    </div>
  );
}

function LayoutShell({ products, theme, setTheme, dataLayout }) {
  const { productId } = useParams();
  const navigate = useNavigate();
  const [keyModal, setKeyModal] = useState(false);

  function onProductChange(id) {
    navigate(`/product/${encodeURIComponent(id)}`);
  }

  if (!productId) return <FirstProductRedirect />;

  return (
    <>
      <Layout
        productId={productId}
        products={products}
        theme={theme}
        setTheme={setTheme}
        onProductChange={onProductChange}
        dataLayout={dataLayout}
        onAdminKey={() => setKeyModal(true)}
      >
        <Routes>
          <Route index element={<Overview />} />
          <Route path="dimension/:dimensionId" element={<DimensionPage />} />
          <Route path="admin/bindings" element={<AdminBindings />} />
          <Route path="admin/connectors" element={<AdminConnectors />} />
          <Route path="admin/evidence" element={<AdminEvidence />} />
        </Routes>
      </Layout>
      <AdminKeyModal
        open={keyModal}
        onClose={() => setKeyModal(false)}
        authEnabled={dataLayout?.admin_auth_enabled}
      />
    </>
  );
}

export default function App() {
  const [theme, setTheme] = useTheme();
  const [products, setProducts] = useState([]);
  const [dataLayout, setDataLayout] = useState(null);

  useEffect(() => {
    listProducts().then(setProducts).catch(() => setProducts([]));
    getBootstrap().then((b) => setDataLayout(b?.data_layout || null)).catch(() => {});
  }, []);

  return (
    <Routes>
      <Route path="/no-catalog" element={<NoCatalog />} />
      <Route path="/" element={<FirstProductRedirect />} />
      <Route
        path="/product/:productId/*"
        element={
          <LayoutShell
            products={products}
            theme={theme}
            setTheme={setTheme}
            dataLayout={dataLayout}
          />
        }
      />
    </Routes>
  );
}
