import { CronTask } from "@crupest/base/cron";
import { generateGeoSiteFiles } from "@crupest/base-contrib/geosite";
import { getDefaultWorkerLogger } from "@crupest/base/log/worker";
import { Duration } from "@crupest/base/runtime";

import { GEOSITE_PATH } from "../base.js";

async function generate() {
  await generateGeoSiteFiles({
    hasPath: GEOSITE_PATH.has,
    notHasPath: GEOSITE_PATH.notHas,
    logger: getDefaultWorkerLogger().withDefaultTag("worker:geosite"),
  });
}

await generate();

const _cron = new CronTask({
  name: "GeoSite Generator",
  interval: Duration.days(1),
  callback: generate,
  enableNow: true,
});
