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
  cpuNumber?: number;
  memory?: number;
  disk: string;
  usbTablet?: boolean;
  sshForwardPort?: number;
  tpm?: boolean;
  kvm?: boolean;
}

interface VmSetup {
  arch: Arch;
  cpuNumber: number;
  memory: number;
  disk: string;
  usbTablet: boolean;
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
    cpuNumber: 4,
    memory: 16,
    disk: getDiskFilePath("win"),
    usbTablet: true,
    tpm: true,
  },
];

function normalizeVmSetup(generalSetup: GeneralVmSetup): VmSetup {
  const { arch, cpuNumber, memory, disk, usbTablet, sshForwardPort, tpm, kvm } =
    generalSetup;

  const normalizedArch = normalizeArch(arch);
  const is64 = normalizedArch === "x86_64";

  return {
    arch: normalizedArch,
    disk,
    cpuNumber: cpuNumber ?? 1,
    memory: memory ?? (is64 ? 8 : 4),
    usbTablet: usbTablet ?? false,
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

function getMachineArgs(vm: VmSetup): string[] {
  const is64 = vm.arch === "x86_64";
  const machineArgs = is64 ? ["-machine", "q35"] : [];
  return [...machineArgs, "-smp", String(vm.cpuNumber), "-m", `${vm.memory}G`];
}

function getDeviceArgs(vm: VmSetup): string[] {
  const { usbTablet } = vm;
  return usbTablet ? ["-usb", "-device", "usb-tablet"] : [];
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
    ...getMachineArgs(setup),
    ...getDeviceArgs(setup),
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
