import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import extractZip from "extract-zip";

import type { ILogger } from "@crupest/base/log";

const ATTR = "cn";
const REPO_NAME = "domain-list-community";
const URL =
  "https://github.com/v2fly/domain-list-community/archive/refs/heads/master.zip";
const SITES = [
  "akamai",
  "aws",
  "github",
  "google",
  "youtube",
  "twitter",
  "facebook",
  "discord",
  "reddit",
  "twitch",
  "quora",
  "medium",
  "telegram",
  "imgur",
  "stackexchange",
  "onedrive",
  "duckduckgo",
  "wikimedia",
  "gitbook",
  "gitlab",
  "huggingface",
  "anthropic",
  "openai",
  "creativecommons",
  "archive",
  "matrix",
  "tor",
  "python",
  "ruby",
  "rust",
  "nodejs",
  "npmjs",
  "qt",
  "docker",
  "v2ray",
  "homebrew",
  "bootstrap",
  "heroku",
  "vercel",
  "ieee",
  "sci-hub",
  "libgen",
];

const prefixes = ["include", "domain", "keyword", "full", "regexp"] as const;

interface Rule {
  kind: (typeof prefixes)[number];
  value: string;
  attrs: string[];
}

type FileProvider = (name: string) => string | Promise<string>;

async function extract(
  starts: string[],
  provider: FileProvider,
  logger: ILogger,
): Promise<Rule[]> {
  function parseLine(line: string): Rule {
    let kind = prefixes.find((p) => line.startsWith(p + ":"));
    if (kind != null) {
      line = line.slice(line.indexOf(":") + 1);
    } else {
      kind = "domain";
    }
    const segs = line.split("@");
    return {
      kind,
      value: segs[0].trim(),
      attrs: [...segs.slice(1)].map((s) => s.trim()),
    };
  }

  function parse(text: string): Rule[] {
    return text
      .replaceAll("\r\n", "\n")
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length !== 0 && !l.startsWith("#"))
      .map((l) => parseLine(l));
  }

  const visited = [] as string[];
  const rules = [] as Rule[];

  async function add(name: string) {
    const text = await provider(name);
    for (const rule of parse(text)) {
      if (rule.kind === "include") {
        if (visited.includes(rule.value)) {
          logger.warn(`circular refs found: ${name} includes ${rule.value}.`);
          continue;
        } else {
          visited.push(rule.value);
          await add(rule.value);
        }
      } else {
        rules.push(rule);
      }
    }
  }

  for (const start of starts) {
    await add(start);
  }

  return rules;
}

function toNewFormat(rules: Rule[], attr: string): [string, string] {
  function toLine(rule: Rule) {
    const prefixMap = {
      domain: "DOMAIN-SUFFIX",
      full: "DOMAIN",
      keyword: "DOMAIN-KEYWORD",
      regexp: "DOMAIN-REGEX",
    } as const;
    if (rule.kind === "include") {
      throw new Error("Include rule not parsed.");
    }
    return `${prefixMap[rule.kind]},${rule.value}`;
  }

  function toLines(rules: Rule[]) {
    return rules.map((r) => toLine(r)).join("\n");
  }

  const has: Rule[] = [];
  const notHas: Rule[] = [];
  rules.forEach((r) => (r.attrs.includes(attr) ? has.push(r) : notHas.push(r)));

  return [toLines(has), toLines(notHas)];
}

export async function generateGeoSiteFiles({
  logger,
  ...options
}: {
  hasPath: string;
  notHasPath: string;
  logger: ILogger;
  attr?: string;
  workDir?: string;
  cleanup?: boolean;
}) {
  const cleanupFunctions: (() => Promise<void> | void)[] = [];
  const addCleanup = (fn: () => Promise<void> | void): void => {
    if (options.cleanup !== false) {
      cleanupFunctions.push(fn);
    }
  };

  const workDir =
    options.workDir ?? (await mkdtemp(join(tmpdir(), "geosite-rules-")));
  if (options.workDir == null) {
    addCleanup(async () => {
      logger.info("Cleaning up work dir: " + workDir);
      await rm(workDir, { recursive: true, force: true });
    });
  }
  logger.info("Work dir is " + workDir);

  try {
    const zipFilePath = join(workDir, "repo.zip");
    logger.info("Downloading repo from " + URL + " ...");
    const response = await fetch(URL);
    if (!response.ok) {
      throw new Error("Failed to download repo.");
    }
    await writeFile(zipFilePath, Buffer.from(await response.arrayBuffer()));
    addCleanup(async () => {
      logger.info("Cleaning up zip file: " + zipFilePath);
      await rm(zipFilePath, { force: true });
    });

    logger.info("Unzipping repo ...");
    await extractZip(zipFilePath, { dir: workDir });
    const dataDir = join(workDir, `${REPO_NAME}-master`, "data");
    addCleanup(async () => {
      logger.info("Cleaning up unzipped data dir: " + dataDir);
      await rm(dataDir, { recursive: true, force: true });
    });

    logger.info("Calculating rules ...");
    const provider = (name: string) =>
      readFile(join(dataDir, name), { encoding: "utf8" });
    const rules = await extract(SITES, provider, logger);
    const [has, notHas] = toNewFormat(rules, options.attr ?? ATTR);

    logger.info(`Write result to: ${options.hasPath} , ${options.notHasPath}`);
    await writeFile(options.hasPath, has);
    await writeFile(options.notHasPath, notHas);
  } finally {
    for (const cleanup of cleanupFunctions.reverse()) {
      await cleanup();
    }
  }
}
