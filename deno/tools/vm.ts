import os from "node:os";
import { join } from "@std/path";
import { defineYargsModule, DEMAND_COMMAND_MESSAGE } from "./yargs.ts";

type ArchAliasMap = { [name: string]: string[] };
const arches = {
  x86_64: ["x86_64", "amd64"],
  i386: ["i386", "x86", "i686"],
} as const satisfies ArchAliasMap;
type Arch = keyof typeof arches;
type GeneralArch = (typeof arches)[Arch][number];

function normalizeArch(generalName: GeneralArch): Arch {
  for (const [name, aliases] of Object.entries(arches as ArchAliasMap)) {
    if (aliases.includes(generalName)) return name as Arch;
  }
  throw Error("Unknown architecture name.");
}

interface GeneralVmSetup {
  name?: string[];
  arch: GeneralArch;
  disk: string;
  sshForwardPort?: number;
  tpm?: boolean;
  kvm?: boolean;
}

interface VmSetup {
  arch: Arch;
  disk: string;
  sshForwardPort?: number;
  tpm: boolean;
  kvm: boolean;
}

const VM_DIR = join(os.homedir(), "vms");

function getDiskFilePath(name: string): string {
  return join(VM_DIR, `${name}.qcow2`);
}

const MY_VMS: GeneralVmSetup[] = [
  {
    name: ["hurd", ...arches.i386.map((a) => `hurd-${a}`)],
    arch: "i386",
    disk: getDiskFilePath("hurd-i386"),
    sshForwardPort: 3222,
  },
  {
    name: [...arches.x86_64.map((a) => `hurd-${a}`)],
    arch: "x86_64",
    disk: getDiskFilePath("hurd-x86_64"),
    sshForwardPort: 3223,
  },
  {
    name: ["win"],
    arch: "x86_64",
    disk: getDiskFilePath("win"),
    tpm: true,
  },
];

function normalizeVmSetup(generalSetup: GeneralVmSetup): VmSetup {
  const { arch, disk, sshForwardPort, tpm, kvm } = generalSetup;
  return {
    arch: normalizeArch(arch),
    disk,
    sshForwardPort,
    tpm: tpm ?? false,
    kvm: kvm ?? Deno.build.os === "linux",
  };
}

function resolveVmSetup(
  name: string,
  vms: GeneralVmSetup[],
): VmSetup | undefined {
  const setup = vms.find((vm) => vm.name?.includes(name));
  return setup == null ? undefined : normalizeVmSetup(setup);
}

const qemuBinPrefix = "qemu-system" as const;

const qemuBinSuffix = {
  x86_64: "x86_64",
  i386: "x86_64",
} as const;

function getQemuBin(arch: Arch): string {
  return `${qemuBinPrefix}-${qemuBinSuffix[arch]}`;
}

function getLinuxHostArgs(kvm: boolean): string[] {
  return kvm ? ["-enable-kvm"] : [];
}

function getMachineArgs(arch: Arch): string[] {
  const is64 = arch === "x86_64";
  const machineArgs = is64 ? ["-machine", "q35"] : [];
  const memory = is64 ? 8 : 4;
  return [...machineArgs, "-m", `${memory}G`];
}

function getNetworkArgs(sshForwardPort?: number): string[] {
  const args = ["-net", "nic"];
  if (sshForwardPort != null) {
    args.push("-net", `user,hostfwd=tcp::${sshForwardPort}-:22`);
  }
  return args;
}

function getDisplayArgs(): string[] {
  return ["-vga", "vmware"];
}

function getDiskArgs(disk: string): string[] {
  return ["-drive", `cache=writeback,file=${disk}`];
}

function getTpmControlSocketPath(): string {
  return join(VM_DIR, "tpm2/swtpm-sock");
}

function getTpmArgs(tpm: boolean): string[] {
  if (!tpm) return [];
  return [
    "-chardev",
    `socket,id=chrtpm,path=${getTpmControlSocketPath()}`,
    "-tpmdev",
    "emulator,id=tpm0,chardev=chrtpm",
    "-device",
    "tpm-tis,tpmdev=tpm0",
  ];
}

function getTpmPreCommand(): string[] {
  return [
    "swtpm",
    "socket",
    "--tpm2",
    "--tpmstate",
    `dir=${join(VM_DIR, "tpm2")}`,
    "--ctrl",
    `type=unixio,path=${getTpmControlSocketPath()}`,
  ];
}

function createPreCommands(setup: VmSetup): string[][] {
  const { tpm } = setup;
  const result = [];
  if (tpm) result.push(getTpmPreCommand());
  return result;
}

function createQemuArgs(setup: VmSetup): string[] {
  const { arch, disk, sshForwardPort, tpm } = setup;
  return [
    getQemuBin(arch),
    ...getLinuxHostArgs(setup.kvm),
    ...getMachineArgs(arch),
    ...getDisplayArgs(),
    ...getNetworkArgs(sshForwardPort),
    ...getDiskArgs(disk),
    ...getTpmArgs(tpm),
  ];
}

const gen = defineYargsModule({
  command: "gen <name>",
  describe: "generate cli command to run the vm",
  builder: (builder) => {
    return builder
      .positional("name", {
        describe: "name of the vm to run",
        type: "string",
      })
      .demandOption("name")
      .strict();
  },
  handler: (argv) => {
    const vm = resolveVmSetup(argv.name, MY_VMS);
    if (vm == null) {
      console.error(`No vm called ${argv.name} is found.`);
      Deno.exit(-1);
    }
    const preCommands = createPreCommands(vm);
    const cli = createQemuArgs(vm);
    for (const command of preCommands) {
      console.log(`${command.join(" ")} &`);
    }
    console.log(`${cli.join(" ")}`);
  },
});

export default defineYargsModule({
  command: "vm",
  describe: "Manage (qemu) virtual machines.",
  builder: (builder) => {
    return builder.command(gen).demandCommand(1, DEMAND_COMMAND_MESSAGE);
  },
  handler: () => {},
});
