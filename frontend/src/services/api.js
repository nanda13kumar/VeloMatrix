import { config, getAdminKey } from "../config.js";

async function request(path, options = {}) {
  const url = `${config.apiBaseUrl}${path}`;
  const adminKey = getAdminKey();
  const extraHeaders = adminKey ? { "X-VeloMatrix-Admin-Key": adminKey } : {};
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
      ...extraHeaders,
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${text}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export function getHealth() {
  return request("/health");
}

export function getBootstrap() {
  return request("/bootstrap");
}

export function listProducts() {
  return request("/products");
}

export function getProductScore(productId) {
  return request(`/products/${encodeURIComponent(productId)}/score`);
}

export function explainSubdimension(productId, body) {
  return request(`/products/${encodeURIComponent(productId)}/dimensions/explain`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ── Admin: connectors ─────────────────────────────────────────────────────────

export function listConnectors() {
  return request("/admin/connectors");
}

export function testConnector(body) {
  return request("/admin/connectors/test", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ── Admin: bindings ───────────────────────────────────────────────────────────

export function listBindings(productId) {
  return request(`/admin/products/${encodeURIComponent(productId)}/bindings`);
}

export function putBinding(productId, subdimensionId, body) {
  return request(
    `/admin/products/${encodeURIComponent(productId)}/bindings/${encodeURIComponent(subdimensionId)}`,
    { method: "PUT", body: JSON.stringify(body) }
  );
}

export function deleteBinding(productId, subdimensionId) {
  return request(
    `/admin/products/${encodeURIComponent(productId)}/bindings/${encodeURIComponent(subdimensionId)}`,
    { method: "DELETE" }
  );
}

// ── Admin: evidence ledger ────────────────────────────────────────────────────

export function listEvidenceSubdims(productId) {
  return request(`/admin/products/${encodeURIComponent(productId)}/evidence`);
}

export function getEvidenceLog(productId, subdimId, limit = 20) {
  return request(
    `/admin/products/${encodeURIComponent(productId)}/evidence/${encodeURIComponent(subdimId)}?limit=${limit}`
  );
}
