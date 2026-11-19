import { CronTask } from "@crupest/base/cron";
import { generateGeoSiteFiles } from "@crupest/base-contrib/geosite";
import { getDefaultLogger } from "@crupest/base/log";

// Where nginx serves the generated rule files from.
const GEOSITE_PATH = {
  has: "/srv/www/gen/magic/has-rule.txt",
  notHas: "/srv/www/gen/magic/not-has-rule.txt",
} as const;

const logger = getDefaultLogger().withDefaultTag("geosite");

async function generate(): Promise<void> {
  try {
    await generateGeoSiteFiles({
      hasPath: GEOSITE_PATH.has,
      notHasPath: GEOSITE_PATH.notHas,
      logger,
    });
  } catch (e) {
    logger.warn("Failed to generate geosite data files:", e);
  }
}

await generate();

new CronTask({
  name: "GeoSite Generator",
  interval: Temporal.Duration.from({ days: 1 }),
  callback: generate,
  enableNow: true,
});
