"use node";

import { execFile } from "node:child_process";
import { readFile } from "node:fs/promises";
import { promisify } from "node:util";
import { internalActionGeneric as internalAction } from "convex/server";

const execute = promisify(execFile);

// Official run_backend.sh execs convex-local-backend as container PID1. The
// bundled native Node executor shares that PID namespace and serving cgroup.
// Read only public process-clock metadata: never argv, environment or secrets.
export const backendUptime = internalAction({
  args: {},
  handler: async () => {
    const [stat, uptime, ticks] = await Promise.all([
      readFile("/proc/1/stat", "utf8"),
      readFile("/proc/uptime", "utf8"),
      execute("getconf", ["CLK_TCK"]),
    ]);
    const end = stat.lastIndexOf(")");
    const command = stat.slice(stat.indexOf("(") + 1, end);
    if (!command.startsWith("convex-local-")) throw new Error("Unexpected backend PID namespace");
    const frequency = Number(ticks.stdout.trim());
    // After comm, array index0 is stat field3; starttime is field22.
    const startTicks = Number(stat.slice(end + 1).trim().split(/\s+/)[19]);
    const bootSeconds = Number(uptime.trim().split(/\s+/)[0]);
    const seconds = bootSeconds - startTicks / frequency;
    if (!Number.isSafeInteger(frequency) || frequency <= 0 ||
        !Number.isSafeInteger(startTicks) || startTicks <= 0 ||
        !Number.isFinite(seconds) || seconds < 0) throw new Error("Backend clock unavailable");
    return Math.floor(seconds);
  },
});
