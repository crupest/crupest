export const APP_PREFIX = "crupest";
export const APP_NAME = "mail-server";

export interface ConfigItemDefinition {
  description: string;
  default?: string;
  secret?: boolean;
}

export const CONFIG_DEFINITIONS = {
  mailDomain: {
    description: "the part after `@` of an address",
  },
  dataPath: {
    description: "path to save app persistent data",
  },
  ldaPath: {
    description: "full path of lda executable",
    "default": "/dovecot/libexec/dovecot/dovecot-lda",
  },
  inboundFallback: {
    description: "comma separated addresses used as fallback recipients",
    "default": "",
  },
  awsInboundPath: {
    description: "(random set) path for aws sns",
  },
  awsInboundKey: {
    description: "(random set) http header Authorization for aws sns",
  },
  awsRegion: {
    description: "aws region",
  },
  awsUser: {
    description: "aws access key id",
  },
  awsPassword: {
    description: "aws secret access key",
    secret: true,
  },
  awsMailBucket: {
    description: "aws s3 bucket saving raw mails",
    secret: true,
  },
} as const satisfies Record<string, ConfigItemDefinition>;

type ConfigDefinitions = typeof CONFIG_DEFINITIONS;
type ConfigNames = keyof ConfigDefinitions;
type ConfigMap = {
  [K in ConfigNames]: ConfigDefinitions[K] & {
    readonly env: string;
    readonly value: string;
  };
};

function resolveConfig(): ConfigMap {
  const result: Record<string, ConfigMap[ConfigNames]> = {};
  for (const [name, def] of Object.entries(CONFIG_DEFINITIONS)) {
    const env = `${APP_PREFIX}-${APP_NAME}-${
      name.replace(/[A-Z]/g, (m) => "-" + m.toLowerCase())
    }`.replaceAll("-", "_").toUpperCase();
    const value = Deno.env.get(env) ?? (def as ConfigItemDefinition).default;
    if (value == null) {
      throw new Error(`Required env ${env} (${def.description}) is not set.`);
    }
    result[name] = { ...def, env, value };
  }
  return result as ConfigMap;
}

export class Config {
  #config = resolveConfig();

  readonly HTTP_HOST = "0.0.0.0";
  readonly HTTP_PORT = 2345;
  readonly SMTP_HOST = "127.0.0.1";
  readonly SMTP_PORT = 2346;

  getAllConfig<K extends ConfigNames>(key: K): ConfigMap[K] {
    return this.#config[key];
  }

  get(key: ConfigNames): string {
    return this.getAllConfig(key).value;
  }

  getList(key: ConfigNames, separator: string = ","): string[] {
    const value = this.get(key);
    if (value.length === 0) return [];
    return value.split(separator);
  }

  [Symbol.for("Deno.customInspect")]() {
    return Object.entries(this.#config).map(([key, item]) =>
      `${key} [env: ${item.env}]: ${
        (item as ConfigItemDefinition).secret === true ? "***" : item.value
      }`
    ).join("\n");
  }
}

const config = new Config();
export default config;
