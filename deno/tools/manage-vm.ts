import os from "node:os";
import { join } from "@std/path";
// @ts-types="npm:@types/yargs"
import yargs from "yargs";

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
  sshForwardPort: number;
  kvm?: boolean;
}

interface VmSetup {
  arch: Arch;
  disk: string;
  sshForwardPort: number;
  kvm: boolean;
}

const MY_VMS: GeneralVmSetup[] = [
  {
    name: ["hurd", ...arches.i386.map((a) => `hurd-${a}`)],
    arch: "i386",
    disk: join(os.homedir(), "vms/hurd-i386.qcow2"),
    sshForwardPort: 3222,
  },
  {
    name: [...arches.x86_64.map((a) => `hurd-${a}`)],
    arch: "x86_64",
    disk: join(os.homedir(), "vms/hurd-x86_64.qcow2"),
    sshForwardPort: 3223,
  },
];

function normalizeVmSetup(generalSetup: GeneralVmSetup): VmSetup {
  const { arch, disk, sshForwardPort, kvm } = generalSetup;
  return {
    arch: normalizeArch(arch),
    disk,
    sshForwardPort,
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

function getNetworkArgs(sshForwardPort: number): string[] {
  return ["-net", "nic", "-net", `user,hostfwd=tcp::${sshForwardPort}-:22`];
}

function getDisplayArgs(): string[] {
  return ["-vga", "vmware"];
}

function getDiskArgs(disk: string): string[] {
  return ["-drive", `cache=writeback,file=${disk}`];
}

function createQemuArgs(setup: VmSetup): string[] {
  const { arch, disk, sshForwardPort } = setup;
  return [
    getQemuBin(arch),
    ...getLinuxHostArgs(setup.kvm),
    ...getMachineArgs(arch),
    ...getDisplayArgs(),
    ...getNetworkArgs(sshForwardPort),
    ...getDiskArgs(disk),
  ];
}

if (import.meta.main) {
  await yargs(Deno.args)
    .scriptName("manage-vm")
    .command({
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
        const cli = createQemuArgs(vm);
        console.log(`${cli.join(" ")}`);
      },
    })
    .demandCommand(1, "One command must be specified.")
    .help()
    .strict()
    .parse();
}
