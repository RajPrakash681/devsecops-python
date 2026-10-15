import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development /api is proxied to a locally running backend. In containers nginx does the
// same job, and in Kubernetes the Ingress routes /api straight to the backend Service.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
});
