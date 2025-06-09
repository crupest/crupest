import { dirname, join, relative } from "@std/path";
import { copySync, existsSync, walkSync } from "@std/fs";
import { parse } from "@std/dotenv";
import { distinct } from "@std/collections"
// @ts-types="npm:@types/mustache"
import Mustache from "mustache"

Mustache.tags = ["@@", "@@"];
Mustache.escape = (value) => String(value);

function getVariableKeys(original: string): string[] {
  return distinct(
    Mustache.parse(original)
      .filter(function (v) {
        return v[0] === "name";
      })
      .map(function (v) {
        return v[1];
      }),
  );
}

export function loadVariables(files: string[]): Record<string, string> {
  const vars: Record<string, string> = {}
  for (const file of files) {
    const text = Deno.readTextFileSync(file);
    for (const [key, valueText] of Object.entries(parse(text))) {
      getVariableKeys(valueText).forEach((name) => {
        if (!(name in vars)) {
          throw new Error(
            `Variable ${name} is not defined yet, perhaps due to typos or wrong order.`,
          );
        }
      });
      vars[key] = Mustache.render(valueText, vars);
    }
  }
  return vars;
}

const TEMPLATE_FILE_EXT = ".template"

export class TemplateDir {
  templates: { path: string; ext: string; text: string; vars: string[] }[] = [];
  plains: { path: string }[] = [];

  constructor(public dir: string) {
    console.log("Scanning template dir:");
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
          vars: getVariableKeys(text),
        });
      } else {
        console.log(`  (plain) ${path}`);
        this.plains.push({ path });
      }
    });
    console.log("Done scanning template dir.");
  }

  allNeededVars() {
    return distinct(this.templates.flatMap((t) => t.vars));
  }

  generate(vars: Record<string, string>, generatedDir?: string) {
    console.log(
      `Generating, template dir: ${this.dir}, generated dir: ${generatedDir ?? "[dry-run]"}:`,
    );

    const undefinedVars = this.allNeededVars().filter((v) => !(v in vars));
    if (undefinedVars.length !== 0) {
      throw new Error(
        `Needed variables are not defined: ${undefinedVars.join(", ")}`,
      );
    }

    if (generatedDir != null) {
      if (existsSync(generatedDir)) {
        console.log(` delete old generated dir ${generatedDir}`);
        Deno.removeSync(generatedDir, { recursive: true });
      }

      for (const file of this.plains) {
        const [source, destination] = [
          join(this.dir, file.path),
          join(generatedDir, file.path),
        ];
        console.log(`  copy ${source} to ${destination} ...`);
        Deno.mkdirSync(dirname(destination), { recursive: true });
        copySync(source, destination);
      }
      for (const file of this.templates) {
        const [source, destination] = [
          join(this.dir, file.path),
          join(generatedDir, file.path.slice(0, -file.ext.length)),
        ];
        console.log(`  generate ${source} to ${destination} ...`);
        const rendered = Mustache.render(file.text, vars);
        Deno.mkdirSync(dirname(destination), { recursive: true });
        Deno.writeTextFileSync(destination, rendered);
      }
    }
    console.log(`Done generating.`);
  }

  generateWithVariableFiles(varFiles: string[], generatedDir?: string) {
    console.log("Scanning defined vars:");
    const vars = loadVariables(varFiles);
    Object.keys(vars).forEach((name) => console.log(`  ${name}`));
    console.log("Done scanning defined vars.");
    this.generate(vars, generatedDir);
  }
}
