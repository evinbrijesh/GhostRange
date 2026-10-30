import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

// The frontend consumes typed API responses only. It never calculates
// authoritative coverage and never calls Nebius directly.
const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, repoRoot, "");

  return {
    envDir: repoRoot,
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target:
            process.env.VITE_API_URL ||
            env.VITE_API_URL ||
            "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
