import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function resolvePropertiesPath() {
  const fromEnv = process.env.APPLICATION_PROPERTIES?.trim();
  if (fromEnv) {
    return path.resolve(fromEnv);
  }
  let dir = __dirname;
  for (let i = 0; i < 12; i++) {
    const candidate = path.join(dir, "application.properties");
    if (fs.existsSync(candidate)) {
      return candidate;
    }
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

function loadApplicationProperties() {
  const filePath = resolvePropertiesPath();
  if (!filePath) {
    return {};
  }
  const props = {};
  const text = fs.readFileSync(filePath, "utf8");
  for (const line of text.split(/\r?\n/)) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const eq = t.indexOf("=");
    if (eq === -1) continue;
    const k = t.slice(0, eq).trim();
    const v = t.slice(eq + 1).trim();
    if (k) props[k] = v;
  }
  return props;
}

const props = loadApplicationProperties();
const backendPort = Number.parseInt(props["backend.port"] || "", 10) || 8000;
const frontendPort = Number.parseInt(props["frontend.port"] || "", 10) || 3000;
const backendTarget = `http://127.0.0.1:${backendPort}`;

export default defineConfig({
  plugins: [react()],
  server: {
    port: frontendPort,
    proxy: {
      "/api": { target: backendTarget, changeOrigin: true },
    },
  },
});
