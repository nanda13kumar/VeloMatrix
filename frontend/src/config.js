/**
 * Bootstrap: API base, branding, and session-level admin key (never persisted to git).
 */
export const config = {
  appName: "VeloMatrix",
  tagline: "Engineering maturity cockpit",
  apiBaseUrl: "/api/v1",
};

/** Runtime-only admin API key — stored in sessionStorage, never in source. */
export function getAdminKey() {
  return sessionStorage.getItem("vm-admin-key") || "";
}

export function setAdminKey(key) {
  if (key) sessionStorage.setItem("vm-admin-key", key);
  else sessionStorage.removeItem("vm-admin-key");
}
