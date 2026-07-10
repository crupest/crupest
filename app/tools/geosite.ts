import { mkdir, mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { getDefaultLogger } from "@crupest/base/log";
import { isMain } from "@crupest/base/runtime";
import { generateGeoSiteFiles } from "@crupest/base-contrib/geosite";

if (isMain(import.meta.url)) {
  const workDir = await mkdtemp(join(tmpdir(), "geosite-rules-"));
  const resultDir = join(workDir, "result");
  await mkdir(resultDir);
  const hasFile = join(resultDir, "has-rule.txt");
  const notHasFile = join(resultDir, "not-has-rule.txt");

  await generateGeoSiteFiles({
    hasPath: hasFile,
    notHasPath: notHasFile,
    logger: getDefaultLogger(),
    workDir,
    cleanup: false,
  });
}
