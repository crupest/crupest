import type { RequestHandler } from "express";

export interface RateLimitOptions {
  requestsPerMinute: number;
}

function isCrawlerAgent(agent: string): boolean {
  const normalized = agent.toLowerCase();
  return ["bot", "crawler", "spider", "scrapy"].some((part) =>
    normalized.includes(part),
  );
}

export class CrawlerRateLimiter {
  readonly #requestsPerMinute: number;
  readonly #agentMap = new Map<string, number>();

  constructor(options?: Partial<RateLimitOptions>) {
    this.#requestsPerMinute = options?.requestsPerMinute ?? 10;
  }

  allow(agent: string | undefined): boolean {
    if (agent == null || !isCrawlerAgent(agent)) return true;

    const count = this.#agentMap.get(agent) ?? 0;
    this.#agentMap.set(agent, count + 1);
    setTimeout(() => {
      const current = this.#agentMap.get(agent) ?? 0;
      if (current <= 1) this.#agentMap.delete(agent);
      else this.#agentMap.set(agent, current - 1);
    }, 60_000).unref();

    return count < this.#requestsPerMinute;
  }

  middleware(): RequestHandler {
    return (request, response, next) => {
      if (this.allow(request.header("user-agent"))) {
        next();
        return;
      }
      response.setHeader("Retry-After", "60");
      response.status(429).send("Too Many Requests");
    };
  }
}

export function createRateLimitMiddleware(
  options?: Partial<RateLimitOptions>,
): RequestHandler {
  return new CrawlerRateLimiter(options).middleware();
}
