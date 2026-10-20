import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "tests/e2e",
  reporter: "list",
  use: {
    baseURL: "http://localhost:5173",
  },
});
