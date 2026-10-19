import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

const API_PREFIX = "/api";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, "../../..", "");
  const target = process.env.API_PROXY_TARGET ?? env.API_PROXY_TARGET;
  const proxy = {
    [API_PREFIX]: {
      target,
      changeOrigin: true,
      rewrite: (path: string) => path.slice(API_PREFIX.length),
    },
  };
  return {
    plugins: [react()],
    server: { proxy },
    preview: { proxy, allowedHosts: true },
    test: {
      environment: "happy-dom",
      include: ["src/**/*.test.tsx"],
    },
  };
});
