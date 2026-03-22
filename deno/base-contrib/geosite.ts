const ATTR = "cn";
const REPO_NAME = "domain-list-community";
const URL =
  "https://github.com/v2fly/domain-list-community/archive/refs/heads/master.zip";
const SITES = [
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
  "anthropic",
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
      .replaceAll("\c\n", "\n")
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
          console.warn(`circular refs found: ${name} includes ${rule.value}.`);
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

export async function generateGeoSiteFiles(
  options: {
    hasPath: string;
    notHasPath: string;
    attr?: string;
    log?: boolean;
    workDir?: string;
    cleanup?: boolean;
  },
) {
  const log = (...args: unknown[]) => {
    if (options.log !== false) {
      console.log(...args);
    }
  };

  await using disposableStack = new AsyncDisposableStack();
  const addCleanup = (fn: () => Promise<void> | void) => {
    if (options.cleanup !== false) {
      disposableStack.defer(fn);
    }
  };

  const workDir = options.workDir ??
    await Deno.makeTempDir({ prefix: "geosite-rules-" });
  if (options.workDir == null) {
    addCleanup(async () => {
      log("Cleaning up work dir: " + workDir);
      await Deno.remove(workDir, { recursive: true });
    });
  }
  log("Work dir is ", workDir);

  const zipFilePath = workDir + "/repo.zip";
  log("Downloading repo from " + URL + " ...");
  const res = await fetch(URL);
  if (!res.ok) {
    throw new Error("Failed to download repo.");
  }
  await Deno.writeFile(zipFilePath, await res.bytes());
  addCleanup(async () => {
    log("Cleaning up zip file: " + zipFilePath);
    await Deno.remove(zipFilePath);
  });

  log("Unzipping repo ...");
  const unzip = new Deno.Command("unzip", {
    args: ["-q", zipFilePath],
    cwd: workDir,
  });
  if (!(await unzip.spawn().status).success) {
    throw new Error("Failed to unzip");
  }
  const dataDir = workDir + "/" + REPO_NAME + "-master/data";
  addCleanup(async () => {
    log("Cleaning up unzipped data dir: " + dataDir);
    await Deno.remove(dataDir, { recursive: true });
  });

  log("Calculating rules ...");
  const provider = (name: string) => Deno.readTextFile(dataDir + "/" + name);
  const rules = await extract(SITES, provider);
  const [has, notHas] = toNewFormat(rules, options.attr ?? ATTR);

  log(
    "Write result to: " + options.hasPath + " , " + options.notHasPath,
  );
  await Deno.writeTextFile(options.hasPath, has);
  await Deno.writeTextFile(options.notHasPath, notHas);
}
