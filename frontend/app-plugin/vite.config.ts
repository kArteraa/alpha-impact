import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const here = (path: string) => fileURLToPath(new URL(path, import.meta.url));

const library = defineConfig({
  plugins: [react()],
  build: {
    lib: { entry: here("src/index.ts"), formats: ["es"], fileName: "index" },
    rollupOptions: { external: ["react", "react-dom", "react/jsx-runtime"] },
  },
  test: {
    environment: "happy-dom",
    include: ["src/**/*.test.{ts,tsx}", "extension/**/*.test.{ts,tsx}"],
    css: { include: [/tokens\.css/] },
  },
});

const extension = defineConfig({
  plugins: [react()],
  root: here("extension"),
  base: "./",
  publicDir: here("extension/public"),
  build: {
    outDir: here("dist-extension"),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        sidepanel: here("extension/sidepanel.html"),
        popup: here("extension/popup.html"),
        background: here("extension/background.ts"),
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "[name].js",
        assetFileNames: "[name].[ext]",
      },
    },
  },
});

const content = defineConfig({
  publicDir: false,
  build: {
    outDir: here("dist-extension"),
    emptyOutDir: false,
    lib: { entry: here("extension/content.ts"), formats: ["iife"], name: "alphaImpactContent", fileName: () => "content.js" },
  },
});

const modes: Record<string, typeof library> = { extension, content };

export default defineConfig(({ mode }) => modes[mode] ?? library);
