import { CronTask } from "@crupest/base/cron";
import { generateGeoSiteFiles } from "@crupest/base-contrib/geosite";

import { GEOSITE_PATH } from "../base.ts";

async function generate() {
  await generateGeoSiteFiles({
    hasPath: GEOSITE_PATH.has,
    notHasPath: GEOSITE_PATH.notHas,
    log: true,
  });
}

await generate();

const _cron = new CronTask({
  name: "GeoSite Generator",
  interval: 24 * 60 * 60 * 1000, // 24 hours
  callback: generate,
  startNow: true,
});
