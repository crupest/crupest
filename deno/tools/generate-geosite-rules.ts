const PROXY_NAME = "node-select";
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
  "telegram",
  "imgur",
  "stackexchange",
  "onedrive",
  "duckduckgo",
  "wikimedia",
  "gitbook",
  "gitlab",
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

type FileProvider = (name: string) => string;

function extract(starts: string[], provider: FileProvider): Rule[] {
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

  function add(name: string) {
    const text = provider(name);
    for (const rule of parse(text)) {
      if (rule.kind === "include") {
        if (visited.includes(rule.value)) {
          console.warn(`circular refs found: ${name} includes ${rule.value}.`);
          continue;
        } else {
          visited.push(rule.value);
          add(rule.value);
        }
      } else {
        rules.push(rule);
      }
    }
  }

  for (const start of starts) {
    add(start);
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

if (import.meta.main) {
  const tmpDir = Deno.makeTempDirSync({ prefix: "geosite-rules-" });
  console.log("Work dir is ", tmpDir);
  const zipFilePath = tmpDir + "/repo.zip";
  const res = await fetch(URL);
  if (!res.ok) {
    throw new Error("Failed to download repo.");
  }
  Deno.writeFileSync(zipFilePath, await res.bytes());
  const unzip = new Deno.Command("unzip", {
    args: ["-q", zipFilePath],
    cwd: tmpDir,
  });
  if (!(await unzip.spawn().status).success) {
    throw new Error("Failed to unzip");
  }

  const dataDir = tmpDir + "/" + REPO_NAME + "-master/data";
  const provider = (name: string) =>
    Deno.readTextFileSync(dataDir + "/" + name);

  const rules = extract(SITES, provider);
  const [has, notHas] = toNewFormat(rules, ATTR);
  const hasFile = tmpDir + "/has-rule";
  const notHasFile = tmpDir + "/not-has-rule";
  console.log("Write result to: " + hasFile + " , " + notHasFile);
  Deno.writeTextFileSync(hasFile, has);
  Deno.writeTextFileSync(notHasFile, notHas);
}
