import { CronTask } from "@crupest/base/cron";
import { generateGeoSiteFiles } from "@crupest/base-contrib/geosite";

import { GEOSITE_PATH } from "../base.ts";

async function generate() {
  await generateGeoSiteFiles({
    hasPath: GEOSITE_PATH.has,
    notHasPath: GEOSITE_PATH.notHas,
    logger: (message: string) => console.log(`[worker:geosite] ${message}`),
  });
}

await generate();

const _cron = new CronTask({
  name: "GeoSite Generator",
  interval: Temporal.Duration.from({ days: 1 }),
  callback: generate,
  enableNow: true,
});
