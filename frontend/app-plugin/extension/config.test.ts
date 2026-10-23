import { describe, expect, it } from "vitest";
import { API_BASE } from "./config";
import manifest from "./public/manifest.json";

describe("extension API address", () => {
  it("is a different cookie host than the application, so the extension login keeps the app session", () => {
    expect(new URL(API_BASE).hostname).not.toBe("localhost");
  });

  it("is covered by the manifest host permissions", () => {
    expect(manifest.host_permissions).toEqual([`${API_BASE}/*`]);
  });
});
