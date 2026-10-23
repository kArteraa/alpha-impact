import { afterEach, describe, expect, it } from "vitest";
import { forgetUser, loadRole, loadUser, saveRole, saveUser } from "./storage";

describe("session storage", () => {
  afterEach(() => localStorage.clear());

  it("remembers the signed-in user", () => {
    expect(loadUser()).toBeNull();

    saveUser("user_cfo_wholesale");

    expect(loadUser()).toBe("user_cfo_wholesale");
  });

  it("keeps a role for each user", () => {
    saveRole("user_cfo_wholesale", "treasurer");

    expect(loadRole("user_cfo_wholesale")).toBe("treasurer");
    expect(loadRole("user_cfo_construction")).toBeNull();
  });

  it("ignores a stored value that is not a role", () => {
    localStorage.setItem("alpha-impact.role.user_cfo_wholesale", "admin");

    expect(loadRole("user_cfo_wholesale")).toBeNull();
  });

  it("ignores a stored value named like an object property", () => {
    localStorage.setItem("alpha-impact.role.user_cfo_wholesale", "constructor");

    expect(loadRole("user_cfo_wholesale")).toBeNull();
  });

  it("forgets the signed-in user", () => {
    saveUser("user_cfo_wholesale");

    forgetUser();

    expect(loadUser()).toBeNull();
  });
});
