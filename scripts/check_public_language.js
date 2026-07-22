import { readFile, readdir } from "node:fs/promises";
import { extname, join } from "node:path";

const roots = ["README.md", "web"];
const forbidden = [
  [/Premium Calculation/gi, "legacy premium heading"],
  [/annual premium/gi, "affirmative annual premium claim"],
  [/\$\s?\d+(?:[,.]\d+)?/g, "currency-valued output"],
  [/ensur(?:e|ing) fairness/gi, "unsupported fairness claim"],
  [/improves? (?:the )?accuracy/gi, "unsupported accuracy claim"],
];

async function filesAt(path) {
  if (extname(path)) return [path];
  const entries = await readdir(path, { withFileTypes: true });
  const nested = await Promise.all(
    entries
      .filter((entry) => entry.name !== "public")
      .map((entry) => filesAt(join(path, entry.name))),
  );
  return nested.flat();
}

const files = (await Promise.all(roots.map(filesAt)))
  .flat()
  .filter((path) => /\.(?:html|js|css|md)$/.test(path));
const errors = [];
for (const path of files) {
  const source = await readFile(path, "utf8");
  for (const [pattern, label] of forbidden) {
    if (pattern.test(source)) errors.push(`${path}: ${label}`);
    pattern.lastIndex = 0;
  }
  if (
    (path.endsWith(".html") || path === "README.md") &&
    !source.includes("Synthetic research simulator, not an insurance quote")
  ) {
    errors.push(`${path}: missing required synthetic-research disclosure`);
  }
}
if (errors.length) {
  console.error(errors.join("\n"));
  process.exitCode = 1;
} else {
  console.log(`Public-language check passed across ${files.length} files.`);
}
