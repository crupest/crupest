import { Site } from "./site.ts";

const outDir = "./dist";

if (await Deno.stat(outDir).catch(() => false)) {
  await Deno.remove(outDir, { recursive: true });
}

const site = await new Site().load();

for (const resource of site.resources) {
  console.log(`Processing resource: ${resource.outputPath}`);
  resource.writeAllOutputFiles(outDir);
}

console.log(`\nOutput in ${outDir}/`);
