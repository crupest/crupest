import { readFile } from "node:fs/promises";
import type { IncomingHttpHeaders } from "node:http";

import type { RequestHandler } from "express";

import { isErrnoException } from "@crupest/base/runtime";

import { verifySha512Crypt } from "../util/crypt.js";

interface User {
  username: string;
  passwordHash: string;
}

async function readUsersFromFile(
  path: string,
  delimiter = ":",
): Promise<User[]> {
  const content = await readFile(path, "utf8");
  const users: User[] = [];
  let lineNumber = 0;
  for (const line of content.split("\n")) {
    lineNumber++;
    const trimmedLine = line.trim();
    if (trimmedLine === "" || trimmedLine.startsWith("#")) continue;

    const delimiterIndex = trimmedLine.indexOf(delimiter);
    if (delimiterIndex === -1) {
      throw new Error(
        `Invalid line format at line ${lineNumber}. Expected "username${delimiter}passwordHash".`,
      );
    }
    users.push({
      username: trimmedLine.slice(0, delimiterIndex).trim(),
      passwordHash: trimmedLine.slice(delimiterIndex + delimiter.length).trim(),
    });
  }
  return users;
}

function parseAuthorization(
  headers: IncomingHttpHeaders,
): [string, string] | null {
  const authorization = headers.authorization;
  if (authorization == null || !authorization.startsWith("Basic ")) {
    return null;
  }

  try {
    const decoded = Buffer.from(authorization.slice(6), "base64").toString(
      "utf8",
    );
    const separator = decoded.indexOf(":");
    if (separator === -1) return null;
    return [decoded.slice(0, separator), decoded.slice(separator + 1)];
  } catch {
    return null;
  }
}

export class FileBasicAuthenticator {
  constructor(readonly path: string) {}

  async verify(headers: IncomingHttpHeaders): Promise<boolean> {
    const credentials = parseAuthorization(headers);
    if (credentials == null) return false;
    const [username, password] = credentials;

    try {
      const users = await readUsersFromFile(this.path);
      const user = users.find((candidate) => candidate.username === username);
      return (
        user != null && (await verifySha512Crypt(password, user.passwordHash))
      );
    } catch (error) {
      if (isErrnoException(error, "ENOENT")) return false;
      throw error;
    }
  }

  middleware(): RequestHandler {
    return async (request, response, next) => {
      if (await this.verify(request.headers)) {
        next();
        return;
      }
      response.setHeader("WWW-Authenticate", 'Basic realm="Secure Area"');
      response.status(401).send("Unauthorized");
    };
  }
}

export function basicAuthFromFile(path: string): RequestHandler {
  return new FileBasicAuthenticator(path).middleware();
}
