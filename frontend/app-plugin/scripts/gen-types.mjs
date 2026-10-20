import { mkdir, readdir, writeFile } from "node:fs/promises";
import { basename, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { compileFromFile } from "json-schema-to-typescript";

const here = dirname(fileURLToPath(import.meta.url));
const schemasDir = resolve(here, "../../../backend/shared/contracts/openapi");
const outDir = resolve(here, "../src/types");

await mkdir(outDir, { recursive: true });
const files = (await readdir(schemasDir)).filter((name) => name.endsWith(".json")).sort();
for (const file of files) {
  const name = basename(file, ".json");
  const source = await compileFromFile(resolve(schemasDir, file), {
    cwd: schemasDir,
    additionalProperties: false,
  });
  await writeFile(resolve(outDir, `${name}.ts`), source);
  console.log(`${name}.ts`);
}
