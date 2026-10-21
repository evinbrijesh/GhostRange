import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The frontend consumes typed API responses only. It never calculates
// authoritative coverage and never calls Nebius directly.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
