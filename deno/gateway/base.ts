import { ConfigDefinition, ConfigProvider } from "@crupest/base/config";

export const PREFIX = "crupest";
export const CONFIG_DEFINITION: ConfigDefinition = {
  domain: {
    description: "the root domain",
  },
  github: {
    description: "site owner's github url",
  },
  v2rayPath: {
    description: "the path for v2ray websocket",
  },
  mailServerAwsInboundPath: {
    description: "the path for mail server aws inbound webhook",
  },
} as const satisfies ConfigDefinition;

export const configProvider = new ConfigProvider(PREFIX, CONFIG_DEFINITION);
export type Config = typeof configProvider;

export const GEOSITE_PATH = {
  has: "/srv/www/magic/has-rule.txt",
  notHas: "/srv/www/magic/not-has-rule.txt",
} as const;
