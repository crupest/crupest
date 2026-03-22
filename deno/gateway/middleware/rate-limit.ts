import { createMiddleware } from "hono/factory";

export interface RateLimitOptions {
  requestsPerMinute: number;
}

function isCrawlerAgent(agent: string): boolean {
  agent = agent.toLowerCase();
  for (const botAgentSubstr of ["bot", "crawler", "spider", "scrapy"]) {
    if (agent.includes(botAgentSubstr)) {
      return true;
    }
  }
  return false;
}

export function createRateLimitMiddleware(options?: Partial<RateLimitOptions>) {
  const { requestsPerMinute } = {
    requestsPerMinute: 10,
    ...options,
  };

  const agentMap = new Map<string, number>();

  return createMiddleware(async (c, next) => {
    const agent = c.req.header("user-agent");
    if (agent == null || !isCrawlerAgent(agent)) {
      await next();
      return;
    }

    const count = agentMap.get(agent) ?? 0;
    agentMap.set(agent, count + 1);
    setTimeout(() => {
      const count = agentMap.get(agent) ?? 0;
      if (count <= 1) {
        agentMap.delete(agent);
      } else {
        agentMap.set(agent, count - 1);
      }
    }, 60000);

    if (count >= requestsPerMinute) {
      c.header("Retry-After", String(60));
      return c.text("Too Many Requests", 429);
    } else {
      await next();
      return;
    }
  });
}
