import { getDefaultLogger } from "@crupest/base/log";
import { generateGeoSiteFiles } from "@crupest/base-contrib/geosite";

if (import.meta.main) {
  const tmpDir = await Deno.makeTempDir({ prefix: "geosite-rules-" });
  const resultDir = tmpDir + "/result";
  await Deno.mkdir(resultDir);
  const hasFile = resultDir + "/has-rule.txt";
  const notHasFile = resultDir + "/not-has-rule.txt";

  await generateGeoSiteFiles({
    hasPath: hasFile,
    notHasPath: notHasFile,
    logger: getDefaultLogger(),
    workDir: tmpDir,
    cleanup: false,
  });
}
