/// <reference no-default-lib="true" />
/// <reference lib="deno.worker" />

import { CronTask } from "@crupest/base/cron";
import { generateGeoSiteFiles } from "@crupest/base-contrib/geosite";
import { getDefaultWorkerLogger } from "@crupest/base/log/worker";

import { GEOSITE_PATH } from "../base.ts";

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
  interval: Temporal.Duration.from({ days: 1 }),
  callback: generate,
  enableNow: true,
});
