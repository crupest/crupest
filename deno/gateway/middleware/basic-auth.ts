import { basicAuth } from "hono/basic-auth";

import { verifySha512Crypt } from "../util/crypt.ts";

interface User {
  username: string;
  passwordHash: string;
}

async function readUsersFromFile(
  path: string,
  delimiter: string = ":",
): Promise<User[]> {
  const content = await Deno.readTextFile(path);
  const lines = content.split("\n");
  const users: User[] = [];
  for (const line of lines) {
    const trimmedLine = line.trim();
    if (trimmedLine === "" || trimmedLine.startsWith("#")) {
      continue; // Skip empty lines and comments
    }
    const delimiterIndex = trimmedLine.indexOf(delimiter);
    if (delimiterIndex === -1) {
      throw new Error(
        `Invalid line format: "${line}". Expected "username${delimiter}passwordHash".`,
      );
    }
    const username = trimmedLine.substring(0, delimiterIndex).trim();
    const passwordHash = trimmedLine.substring(
      delimiterIndex + delimiter.length,
    ).trim();
    users.push({ username, passwordHash });
  }
  return users;
}

export function basicAuthFromFile(path: string) {
  return basicAuth({
    verifyUser: async (username, password) => {
      try {
        const users = await readUsersFromFile(path);
        const user = users.find((u) => u.username === username);
        if (!user) return false;
        return verifySha512Crypt(password, user.passwordHash);
      } catch (e) {
        if (e instanceof Deno.errors.NotFound) {
          return false;
        } else {
          throw e;
        }
      }
    },
  });
}
