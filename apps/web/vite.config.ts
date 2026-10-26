import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The frontend consumes typed API responses only. It never calculates
// authoritative coverage and never calls Nebius directly.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_URL || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
