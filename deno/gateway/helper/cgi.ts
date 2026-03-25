import { Context } from "hono";
import { getConnInfo } from "hono/deno";

export interface CgiHandlerOptions {
  command: string;
  args?: string[];
  cwd?: string;
  extraEnv?: Record<string, string>;
}

export function createCgiHandler(options: CgiHandlerOptions) {
  const { command, args = [], cwd, extraEnv } = options;

  return async (c: Context) => {
    const url = new URL(c.req.url);
    const remoteAddr = getConnInfo(c).remote.address ?? "";

    const env: Record<string, string> = {
      GATEWAY_INTERFACE: "CGI/1.1",
      REQUEST_METHOD: c.req.method,
      QUERY_STRING: url.search.slice(1),
      PATH_INFO: url.pathname,
      SCRIPT_NAME: url.pathname,
      SERVER_NAME: url.hostname,
      SERVER_PORT: url.port || (url.protocol === "https:" ? "443" : "80"),
      SERVER_PROTOCOL: "HTTP/1.1",
      SERVER_SOFTWARE: "crupest-gateway",
      REMOTE_ADDR: remoteAddr,
      REMOTE_HOST: remoteAddr,
      ...extraEnv,
    };

    const contentType = c.req.header("content-type");
    if (contentType) {
      env.CONTENT_TYPE = contentType;
    }

    const contentLength = c.req.header("content-length");
    if (contentLength) {
      env.CONTENT_LENGTH = contentLength;
    }

    for (const [key, value] of Object.entries(c.req.header())) {
      env[`HTTP_${key.toUpperCase().replaceAll("-", "_")}`] = value;
    }

    const proc = new Deno.Command(command, {
      args,
      cwd,
      env,
      stdin: "piped",
      stdout: "piped",
      stderr: "inherit",
    }).spawn();

    const requestBody = c.req.raw.body;
    const writeStdin = requestBody
      ? requestBody.pipeTo(proc.stdin)
      : proc.stdin.close();
    const readStdout = new Response(proc.stdout).arrayBuffer();

    const [, stdoutBuffer] = await Promise.all([writeStdin, readStdout]);
    await proc.status;

    const responseBytes = new Uint8Array(stdoutBuffer);

    // Find the blank-line separator between CGI headers and body
    let separatorEnd = -1;
    for (let i = 0; i < responseBytes.length; i++) {
      if (
        i + 3 < responseBytes.length &&
        responseBytes[i] === 0x0d &&
        responseBytes[i + 1] === 0x0a &&
        responseBytes[i + 2] === 0x0d &&
        responseBytes[i + 3] === 0x0a
      ) {
        separatorEnd = i + 4;
        break;
      }
      if (
        i + 1 < responseBytes.length &&
        responseBytes[i] === 0x0a &&
        responseBytes[i + 1] === 0x0a
      ) {
        separatorEnd = i + 2;
        break;
      }
    }

    if (separatorEnd === -1) {
      return new Response(responseBytes, { status: 200 });
    }

    const headerText = new TextDecoder().decode(
      responseBytes.slice(0, separatorEnd),
    );
    const bodyBytes = responseBytes.slice(separatorEnd);

    const headers = new Headers();
    let status = 200;

    for (const line of headerText.split(/\r?\n/)) {
      if (!line.trim()) continue;
      const colonIdx = line.indexOf(":");
      if (colonIdx === -1) continue;
      const name = line.slice(0, colonIdx).trim();
      const value = line.slice(colonIdx + 1).trim();
      if (name.toLowerCase() === "status") {
        const statusCode = parseInt(value);
        if (!isNaN(statusCode)) status = statusCode;
      } else {
        headers.append(name, value);
      }
    }

    return new Response(bodyBytes, { status, headers });
  };
}
