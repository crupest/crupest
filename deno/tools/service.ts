import { dirname, join, relative } from "@std/path";
import { copySync, existsSync, walkSync } from "@std/fs";
import { parse } from "@std/dotenv";
import { distinct } from "@std/collections";
// @ts-types="npm:@types/mustache"
import Mustache from "mustache";

import { defineYargsModule, DEMAND_COMMAND_MESSAGE } from "./yargs.ts";

const MUSTACHE_RENDER_OPTIONS: Mustache.RenderOptions = {
  tags: ["@@", "@@"],
  escape: (value: unknown) => String(value),
};

function mustacheParse(template: string) {
  return Mustache.parse(template, MUSTACHE_RENDER_OPTIONS.tags);
}

function mustacheRender(template: string, view: Record<string, string>) {
  return Mustache.render(template, view, {}, MUSTACHE_RENDER_OPTIONS);
}

function getVariableKeysOfTemplate(template: string): string[] {
  return distinct(
    mustacheParse(template)
      .filter((v) => v[0] === "name")
      .map((v) => v[1]),
  );
}

function loadTemplatedConfigFiles(
  files: string[],
): Record<string, string> {
  console.log("Scan config files ...");
  const config: Record<string, string> = {};
  for (const file of files) {
    console.log(`  from file ${file}`);
    const text = Deno.readTextFileSync(file);
    for (const [key, valueText] of Object.entries(parse(text))) {
      // TODO: dotenv silently override old values, so everything will be new for now.
      console.log(`    (${key in config ? "override" : "new"}) ${key}`);
      getVariableKeysOfTemplate(valueText).forEach((name) => {
        if (!(name in config)) {
          throw new Error(
            `Variable ${name} is not defined yet, perhaps due to typos or wrong order.`,
          );
        }
      });
      config[key] = mustacheRender(valueText, config);
    }
  }
  return config;
}

const TEMPLATE_FILE_EXT = ".template";

class TemplateDir {
  templates: { path: string; ext: string; text: string; vars: string[] }[] = [];
  plains: { path: string }[] = [];

  constructor(public dir: string) {
    console.log(`Scan template dir ${dir} ...`);
    Array.from(
      walkSync(dir, { includeDirs: false, followSymlinks: true }),
    ).forEach(({ path }) => {
      path = relative(this.dir, path);
      if (path.endsWith(TEMPLATE_FILE_EXT)) {
        console.log(`  (template) ${path}`);
        const text = Deno.readTextFileSync(join(dir, path));
        this.templates.push({
          path,
          ext: TEMPLATE_FILE_EXT,
          text,
          vars: getVariableKeysOfTemplate(text),
        });
      } else {
        console.log(`  (plain) ${path}`);
        this.plains.push({ path });
      }
    });
  }

  allNeededVars() {
    return distinct(this.templates.flatMap((t) => t.vars));
  }

  generate(vars: Record<string, string>, generatedDir?: string) {
    console.log(
      `Generate to dir ${generatedDir ?? "[dry-run]"} ...`,
    );

    const undefinedVars = this.allNeededVars().filter((v) => !(v in vars));
    if (undefinedVars.length !== 0) {
      throw new Error(
        `Needed variables are not defined: ${undefinedVars.join(", ")}`,
      );
    }

    if (generatedDir != null) {
      if (existsSync(generatedDir)) {
        console.log(`  delete old generated dir`);
        Deno.removeSync(generatedDir, { recursive: true });
      }

      for (const file of this.plains) {
        const [source, destination] = [
          join(this.dir, file.path),
          join(generatedDir, file.path),
        ];
        console.log(`  copy ${file.path}`);
        Deno.mkdirSync(dirname(destination), { recursive: true });
        copySync(source, destination);
      }
      for (const file of this.templates) {
        const path = file.path.slice(0, -file.ext.length);
        const destination = join(generatedDir, path);
        console.log(`  generate ${path}`);
        const rendered = mustacheRender(file.text, vars);
        Deno.mkdirSync(dirname(destination), { recursive: true });
        Deno.writeTextFileSync(destination, rendered);
      }
    }
  }
}

export default defineYargsModule({
  command: "service",
  aliases: ["sv"],
  describe: "Manage services.",
  builder: (builder) => {
    return builder
      .option("project-dir", {
        type: "string",
      })
      .demandOption("project-dir")
      .command({
        command: "gen-tmpl",
        describe: "Generate files from templates",
        builder: (builder) => {
          return builder
            .option("dry-run", {
              type: "boolean",
              default: true,
            })
            .strict();
        },
        handler: (argv) => {
          const { projectDir, dryRun } = argv;

          const config = loadTemplatedConfigFiles(
            [
              join(projectDir, "data/config"),
              join(projectDir, "services/config.template"),
            ],
          );

          new TemplateDir(
            join(projectDir, "services/templates"),
          ).generate(
            config,
            dryRun ? undefined : join(projectDir, "services/generated"),
          );
          console.log("Done!");
        },
      })
      .demandCommand(1, DEMAND_COMMAND_MESSAGE);
  },
  handler: () => {},
});
