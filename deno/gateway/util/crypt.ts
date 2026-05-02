/**
 * SHA-512 crypt ($6$) implementation following the Drepper specification.
 * Compatible with `openssl passwd -6`.
 */

const ITOA64 =
  "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" as const;

// Byte permutation for SHA-512 crypt encoding (from the Drepper spec)
const PERM = [
  [0, 21, 42],
  [22, 43, 1],
  [44, 2, 23],
  [3, 24, 45],
  [25, 46, 4],
  [47, 5, 26],
  [6, 27, 48],
  [28, 49, 7],
  [50, 8, 29],
  [9, 30, 51],
  [31, 52, 10],
  [53, 11, 32],
  [12, 33, 54],
  [34, 55, 13],
  [56, 14, 35],
  [15, 36, 57],
  [37, 58, 16],
  [59, 17, 38],
  [18, 39, 60],
  [40, 61, 19],
  [62, 20, 41],
] as const;

async function sha512(data: Uint8Array): Promise<Uint8Array> {
  return new Uint8Array(
    await crypto.subtle.digest("SHA-512", data as BufferSource),
  );
}

function concat(...arrays: Uint8Array[]): Uint8Array {
  const len = arrays.reduce((s, a) => s + a.length, 0);
  const r = new Uint8Array(len);
  let off = 0;
  for (const a of arrays) {
    r.set(a, off);
    off += a.length;
  }
  return r;
}

/** Concatenate `count` copies of `data`. */
function repeat(data: Uint8Array, count: number): Uint8Array {
  const r = new Uint8Array(data.length * count);
  let off = 0;
  for (let i = 0; i < count; i++) {
    r.set(data, off);
    off += data.length;
  }
  return r;
}

/** Push the first `n` bytes of `buf`, repeating `buf` as needed to reach `n` bytes. */
function pushRepeated(parts: Uint8Array[], n: number, buf: Uint8Array) {
  let remaining = n;
  while (remaining > 64) {
    parts.push(buf);
    remaining -= 64;
  }
  parts.push(buf.slice(0, remaining));
}

function encode(md: Uint8Array): string {
  let result = "";
  for (const [a, b, c] of PERM) {
    let w = (md[a] << 16) | (md[b] << 8) | md[c];
    result += ITOA64[w & 0x3f];
    w >>= 6;
    result += ITOA64[w & 0x3f];
    w >>= 6;
    result += ITOA64[w & 0x3f];
    w >>= 6;
    result += ITOA64[w & 0x3f];
  }
  // Last byte (md[63]) as 2 chars
  result += ITOA64[md[63] & 0x3f];
  result += ITOA64[md[63] >> 6];
  return result;
}

export async function sha512crypt(
  password: string,
  salt: string,
  rounds = 5000,
): Promise<string> {
  const enc = new TextEncoder();
  const P = enc.encode(password);
  const S = enc.encode(salt);
  const klen = P.length;
  const slen = S.length;

  // B = SHA512(P || S || P) — steps 4-8
  const B = await sha512(concat(P, S, P));

  // A = SHA512(P || S || repeat(B, klen) || alternate bits of keylen) — steps 1-3, 9-12
  const partsA: Uint8Array[] = [];
  partsA.push(P, S);
  pushRepeated(partsA, klen, B);
  for (let i = klen; i > 0; i >>= 1) {
    partsA.push(i & 1 ? B : P);
  }
  let md = await sha512(concat(...partsA));

  // DP = SHA512(P repeated klen times) — steps 13-15
  const DP = await sha512(repeat(P, klen));

  // DS = SHA512(S repeated 16 + A[0] times) — steps 17-19
  const DS = await sha512(repeat(S, 16 + md[0]));

  // Round loop — step 21
  for (let i = 0; i < rounds; i++) {
    const parts: Uint8Array[] = [];

    if (i & 1) pushRepeated(parts, klen, DP);
    else parts.push(md);

    if (i % 3) parts.push(DS.slice(0, slen));

    if (i % 7) pushRepeated(parts, klen, DP);

    if (i & 1) parts.push(md);
    else pushRepeated(parts, klen, DP);

    md = await sha512(concat(...parts));
  }

  return encode(md);
}

export async function verifySha512Crypt(
  password: string,
  storedHash: string,
): Promise<boolean> {
  const parts = storedHash.split("$");
  if (parts.length < 4 || parts[1] !== "6") return false;

  let salt: string;
  let rounds = 5000;
  let hash: string;

  if (parts[2].startsWith("rounds=")) {
    rounds = parseInt(parts[2].substring(7), 10);
    salt = parts[3];
    hash = parts[4];
  } else {
    salt = parts[2];
    hash = parts[3];
  }

  return await sha512crypt(password, salt, rounds) === hash;
}
