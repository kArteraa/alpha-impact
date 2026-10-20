import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const MARKER = "node_modules/";
const lock = JSON.parse(readFileSync(new URL("../package-lock.json", import.meta.url), "utf8"));
const entries = Object.entries(lock.packages);

const recorded = new Set(
  entries
    .filter(([path]) => path.includes(MARKER))
    .map(([path]) => path.slice(path.lastIndexOf(MARKER) + MARKER.length)),
);

test("lockfile records every optional dependency, including other platforms' native builds", () => {
  const declared = new Set(entries.flatMap(([, entry]) => Object.keys(entry.optionalDependencies ?? {})));
  const missing = [...declared].filter((name) => !recorded.has(name)).sort();
  assert.deepEqual(
    missing,
    [],
    "frontend/package-lock.json lost optional platform packages (npm/cli#4828): delete frontend/node_modules and frontend/package-lock.json, then run npm install",
  );
});
