import { WorkersAIClient } from "./cloudflare_ai";
import { MetaInstagramClient } from "./instagram";

export class NodeInstaPipeline {
  private ai: WorkersAIClient;
  private ig: MetaInstagramClient;
  private env: any;

  constructor(env: any) {
    this.env = env;
    this.ai = new WorkersAIClient(env);
    this.ig = new MetaInstagramClient(env);
  }

  async executeCycle(topic: string, imageUrlOverride?: string) {
    console.log(`[PIPELINE] Starting execution for: ${topic}`);

    // 1. Generate text
    const content = await this.ai.generateContent(topic);

    // 2. Generate or host image (Use public URL fallback if hosting not configured)
    const publicImageUrl = imageUrlOverride || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1080&q=80";

    // 3. Publish to Instagram
    const result = await this.ig.publishPhoto(publicImageUrl, content.full_caption);

    return {
      topic,
      content,
      image_url: publicImageUrl,
      result
    };
  }
}
