import {
  request as createHttpRequest,
  type IncomingMessage,
  type RequestOptions,
} from "node:http";
import type { Duplex } from "node:stream";
import { TLSSocket } from "node:tls";

import type { RequestHandler } from "express";

export interface ReverseProxy {
  middleware: RequestHandler;
  upgrade(request: IncomingMessage, socket: Duplex, head: Buffer): void;
}

function prepareForwardHeaders(
  request: IncomingMessage,
  protocol: "http" | "https",
): void {
  const host = request.headers.host;
  const remoteAddress = request.socket.remoteAddress;
  if (host != null) {
    request.headers["x-forwarded-host"] = host;
  }
  request.headers["x-forwarded-proto"] = protocol;
  if (remoteAddress != null) {
    request.headers["x-real-ip"] = remoteAddress;
    const forwardedFor = request.headers["x-forwarded-for"];
    request.headers["x-forwarded-for"] =
      forwardedFor == null
        ? remoteAddress
        : `${forwardedFor}, ${remoteAddress}`;
  }
}

function createRequestOptions(
  target: URL,
  request: IncomingMessage,
): RequestOptions {
  return {
    headers: request.headers,
    hostname: target.hostname,
    method: request.method,
    path: request.url,
    port: target.port,
    protocol: target.protocol,
  };
}

function writeRawResponse(socket: Duplex, response: IncomingMessage): void {
  const statusCode = response.statusCode ?? 502;
  const statusMessage = response.statusMessage ?? "Bad Gateway";
  const headers: string[] = [];
  for (let i = 0; i < response.rawHeaders.length; i += 2) {
    headers.push(`${response.rawHeaders[i]}: ${response.rawHeaders[i + 1]}`);
  }
  socket.write(
    `HTTP/${response.httpVersion} ${statusCode} ${statusMessage}\r\n${headers.join("\r\n")}\r\n\r\n`,
  );
}

function writeUpgradeError(socket: Duplex): void {
  if (socket.destroyed) return;
  socket.end(
    "HTTP/1.1 502 Bad Gateway\r\n" +
      "Connection: close\r\n" +
      "Content-Length: 11\r\n" +
      "Content-Type: text/plain; charset=utf-8\r\n" +
      "\r\n" +
      "Bad Gateway",
  );
}

export function createReverseProxy({
  originServer,
}: {
  originServer: string;
}): ReverseProxy {
  const target = new URL(`http://${originServer}`);

  return {
    middleware(request, response) {
      prepareForwardHeaders(
        request,
        request.socket instanceof TLSSocket ? "https" : "http",
      );

      const proxyRequest = createHttpRequest(
        createRequestOptions(target, request),
        (proxyResponse) => {
          response.writeHead(
            proxyResponse.statusCode ?? 502,
            proxyResponse.statusMessage,
            proxyResponse.headers,
          );
          proxyResponse.pipe(response);
        },
      );

      proxyRequest.on("error", () => {
        if (!response.headersSent) {
          response.writeHead(502, {
            "Content-Type": "text/plain; charset=utf-8",
          });
        }
        response.end("Bad Gateway");
      });
      request.on("aborted", () => proxyRequest.destroy());
      request.on("error", () => proxyRequest.destroy());
      response.on("close", () => {
        if (!response.writableEnded) proxyRequest.destroy();
      });
      response.on("error", () => proxyRequest.destroy());
      request.pipe(proxyRequest);
    },
    upgrade(request, socket, head) {
      prepareForwardHeaders(
        request,
        request.socket instanceof TLSSocket ? "https" : "http",
      );

      const proxyRequest = createHttpRequest(
        createRequestOptions(target, request),
      );
      proxyRequest.on("upgrade", (proxyResponse, proxySocket, proxyHead) => {
        writeRawResponse(socket, proxyResponse);
        if (proxyHead.length !== 0) socket.write(proxyHead);
        if (head.length !== 0) proxySocket.write(head);

        socket.on("error", () => proxySocket.destroy());
        proxySocket.on("error", () => socket.destroy());
        socket.pipe(proxySocket);
        proxySocket.pipe(socket);
      });
      proxyRequest.on("response", (proxyResponse) => {
        writeRawResponse(socket, proxyResponse);
        proxyResponse.pipe(socket);
      });
      proxyRequest.on("error", () => writeUpgradeError(socket));
      socket.on("close", () => proxyRequest.destroy());
      socket.on("error", () => proxyRequest.destroy());
      proxyRequest.end();
    },
  };
}

export function createReverseProxyHandler(options: {
  originServer: string;
}): RequestHandler {
  return createReverseProxy(options).middleware;
}
