import { mkdir, mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { getDefaultLogger } from "@crupest/base/log";
import { generateGeoSiteFiles } from "@crupest/base-contrib/geosite";

import { defineYargsModule } from "./yargs.js";

export default defineYargsModule({
  command: "geosite",
  describe: "Generate GeoSite rule files.",
  handler: async () => {
    const workDir = await mkdtemp(join(tmpdir(), "geosite-rules-"));
    const resultDir = join(workDir, "result");
    await mkdir(resultDir);

    await generateGeoSiteFiles({
      hasPath: join(resultDir, "has-rule.txt"),
      notHasPath: join(resultDir, "not-has-rule.txt"),
      logger: getDefaultLogger(),
      workDir,
      cleanup: false,
    });
  },
});
