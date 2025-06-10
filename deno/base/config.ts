import { camelCaseToKebabCase } from "./text.ts";

export interface ConfigDefinitionItem {
  readonly description: string;
  readonly default?: string;
  readonly secret?: boolean;
}

interface ConfigMapItem extends ConfigDefinitionItem {
  readonly env: string;
  value?: string;
}

export type ConfigDefinition<K extends string = string> = Record<
  K,
  ConfigDefinitionItem
>;
type ConfigMap<K extends string = string> = Record<K, ConfigMapItem>;

export class ConfigProvider<K extends string> {
  readonly #prefix: string;
  readonly #map: ConfigMap<K>;

  constructor(prefix: string, ...definitions: Partial<ConfigDefinition<K>>[]) {
    this.#prefix = prefix;

    const map: ConfigMap = {};
    for (const definition of definitions) {
      for (const [key, def] of Object.entries(definition as ConfigDefinition)) {
        map[key] = {
          ...def,
          env: `${this.#prefix}-${camelCaseToKebabCase(key as string)}`
            .replaceAll("-", "_")
            .toUpperCase(),
        };
      }
    }
    this.#map = map as ConfigMap<K>;
  }

  resolveFromEnv(options?: { keys?: K[] }) {
    const keys = options?.keys ?? Object.keys(this.#map);
    for (const key of keys) {
      const { env, description, default: _default } = this.#map[key as K];
      const value = Deno.env.get(env) ?? _default;
      if (value == null) {
        throw new Error(`Required env ${env} (${description}) is not set.`);
      }
      this.#map[key as K].value = value;
    }
  }

  get(key: K): string {
    if (!(key in this.#map)) {
      throw new Error(`Unknown config key ${key as string}.`);
    }
    if (this.#map[key].value == null) {
      this.resolveFromEnv({ keys: [key] });
    }
    return this.#map[key].value!;
  }

  set(key: K, value: string) {
    if (!(key in this.#map)) {
      throw new Error(`Unknown config key ${key as string}.`);
    }
    this.#map[key].value = value;
  }

  getInt(key: K): number {
    return Number(this.get(key));
  }

  getList(key: K, separator: string = ","): string[] {
    const value = this.get(key);
    if (value.length === 0) return [];
    return value.split(separator);
  }

  [Symbol.for("Deno.customInspect")]() {
    const getValueString = (item: ConfigMapItem): string => {
      if (item.value == null) return "(unresolved)";
      if (item.secret === true) return "***";
      return item.value;
    };

    return Object.entries(this.#map as ConfigMap)
      .map(
        ([key, item]) => `${key} [env: ${item.env}]: ${getValueString(item)}`,
      )
      .join("\n");
  }
}
