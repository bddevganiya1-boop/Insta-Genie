import { NodeInstaPipeline } from "./pipeline";
import { WorkersAIClient } from "./cloudflare_ai";
import { MetaInstagramClient } from "./instagram";

export interface Env {
  AI?: any;
  CLOUDFLARE_ACCOUNT_ID?: string;
  CLOUDFLARE_API_TOKEN?: string;
  INSTAGRAM_ACCOUNT_ID?: string;
  INSTAGRAM_ACCESS_TOKEN?: string;
  META_GRAPH_API_VERSION?: string;
  DRY_RUN?: string;
}

// -----------------------------------------------------------------------------
// Cloudflare Worker Fetch & Scheduled Export
// -----------------------------------------------------------------------------
export default {
  // HTTP Request Handler
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    const headers = {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization"
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers });
    }

    try {
      // 1. Health Status
      if (url.pathname === "/api/status" && request.method === "GET") {
        return new Response(JSON.stringify({
          status: "online",
          runtime: "Cloudflare Workers / Node.js",
          dry_run: env.DRY_RUN === "true",
          has_ai_binding: !!env.AI
        }), { headers });
      }

      // 2. Generate Draft Content
      if (url.pathname === "/api/generate" && request.method === "POST") {
        const body: any = await request.json();
        const client = new WorkersAIClient(env);
        const draft = await client.generateContent(body.topic || "Autonomous AI Agents", body.tone);
        return new Response(JSON.stringify(draft), { headers });
      }

      // 3. Direct Publish
      if (url.pathname === "/api/publish" && request.method === "POST") {
        const body: any = await request.json();
        const ig = new MetaInstagramClient(env);
        const result = await ig.publishPhoto(body.image_url, body.caption);
        return new Response(JSON.stringify(result), { headers });
      }

      // 4. Run Full Pipeline
      if (url.pathname === "/api/run-pipeline" && request.method === "POST") {
        const body: any = await request.json();
        const pipeline = new NodeInstaPipeline(env);
        const result = await pipeline.executeCycle(body.topic || "Next-Gen AI Systems", body.image_url);
        return new Response(JSON.stringify(result), { headers });
      }

      return new Response(JSON.stringify({ error: "Endpoint Not Found" }), { status: 404, headers });

    } catch (err: any) {
      return new Response(JSON.stringify({ error: err.message }), { status: 500, headers });
    }
  },

  // Cloudflare Cron Trigger (Scheduled Auto-Posting)
  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
    console.log(`[CRON] Triggered scheduled post at ${new Date(event.scheduledTime).toISOString()}`);
    const topics = [
      "AI Innovations in Automation",
      "Future Tech & Web Architecture",
      "Creative Digital Storytelling",
      "Autonomous Agents in Production"
    ];
    const selectedTopic = topics[Math.floor(Math.random() * topics.length)];
    const pipeline = new NodeInstaPipeline(env);

    ctx.waitUntil(pipeline.executeCycle(selectedTopic));
  }
};
