import { rm } from "node:fs/promises";

import { Site } from "./site.js";

const outDir = "./dist";

await rm(outDir, { recursive: true, force: true });

const site = await new Site().load();

for (const resource of site.resources) {
  console.log(`Processing resource: ${resource.outputPath}`);
  await resource.writeAllOutputFiles(outDir);
}

console.log(`\nOutput in ${outDir}/`);
