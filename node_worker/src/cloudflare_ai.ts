export interface GeneratedPostContent {
  hook: string;
  body: string;
  hashtags: string[];
  full_caption: string;
  image_prompt: string;
}

export class WorkersAIClient {
  private aiBinding?: any;
  private accountId?: string;
  private apiToken?: string;
  private textModel: string;
  private imageModel: string;

  constructor(env: any) {
    this.aiBinding = env.AI;
    this.accountId = env.CLOUDFLARE_ACCOUNT_ID;
    this.apiToken = env.CLOUDFLARE_API_TOKEN;
    this.textModel = env.CF_TEXT_MODEL || "@cf/meta/llama-3.3-70b-instruct-fp8-fast";
    this.imageModel = env.CF_IMAGE_MODEL || "@cf/black-forest-labs/flux-1-schnell";
  }

  async generateContent(topic: string, tone = "engaging & visionary"): Promise<GeneratedPostContent> {
    const systemPrompt = `You are an elite Instagram growth strategist. Generate a viral Instagram post about the given topic. 
Respond ONLY with valid JSON in this structure:
{
  "hook": "Catchy first-line hook",
  "caption": "Full body text with emojis, bullet points, and CTA",
  "hashtags": ["#tag1", "#tag2", "#tag3"],
  "image_prompt": "Ultra-detailed, photorealistic prompt for FLUX/SDXL image model, 1:1 square ratio, cinematic studio lighting, 8k resolution, no text."
}`;

    const userPrompt = `Topic: ${topic}\nTone: ${tone}`;

    let rawText = "";

    // 1. Try native Workers AI binding if running inside Cloudflare Worker
    if (this.aiBinding && typeof this.aiBinding.run === "function") {
      const response: any = await this.aiBinding.run(this.textModel, {
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt }
        ],
        max_tokens: 1024
      });
      rawText = response.response || JSON.stringify(response);
    } 
    // 2. Fallback to Cloudflare Workers AI REST API
    else if (this.accountId && this.apiToken) {
      const res = await fetch(`https://api.cloudflare.com/client/v4/accounts/${this.accountId}/ai/run/${this.textModel}`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${this.apiToken}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userPrompt }
          ]
        })
      });
      const data: any = await res.json();
      rawText = data?.result?.response || "";
    } 
    // 3. Mock fallback
    else {
      return this.getMockContent(topic);
    }

    try {
      const jsonMatch = rawText.match(/\{[\s\S]*\}/);
      const parsed = JSON.parse(jsonMatch ? jsonMatch[0] : rawText);
      const hook = parsed.hook || `✨ Exploring ${topic}`;
      const body = parsed.caption || `Deep dive into ${topic}. Tap into the future!`;
      const hashtags = (parsed.hashtags || []).map((t: string) => t.startsWith("#") ? t : `#${t}`);
      const fullCaption = `${hook}\n\n${body}\n\n.\n.\n${hashtags.join(" ")}`;

      return {
        hook,
        body,
        hashtags,
        full_caption: fullCaption,
        image_prompt: parsed.image_prompt || `Futuristic aesthetic 3D render representing ${topic}, 8k, photorealistic`
      };
    } catch {
      return this.getMockContent(topic);
    }
  }

  async generateImage(prompt: string): Promise<Uint8Array> {
    if (this.aiBinding && typeof this.aiBinding.run === "function") {
      const res: any = await this.aiBinding.run(this.imageModel, {
        prompt,
        num_steps: 4
      });
      return new Uint8Array(res);
    } else if (this.accountId && this.apiToken) {
      const res = await fetch(`https://api.cloudflare.com/client/v4/accounts/${this.accountId}/ai/run/${this.imageModel}`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${this.apiToken}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ prompt, num_steps: 4 })
      });
      const buffer = await res.arrayBuffer();
      return new Uint8Array(buffer);
    }

    // Return 1x1 dummy PNG byte buffer
    return new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10]);
  }

  private getMockContent(topic: string): GeneratedPostContent {
    const tag = topic.replace(/[^a-zA-Z0-9]/g, "");
    const hook = `🚀 The Revolution of ${topic} Starts Now!`;
    const body = `Discover how ${topic} is transforming our workflows and digital future.\n\n3 key takeaways:\n• Innovation never stops.\n• Automate the repetitive tasks.\n• Lead with value.\n\n👇 Drop your thoughts below!`;
    const hashtags = [`#${tag}`, "#InstaGenie", "#AITools", "#MetaGraphAPI", "#ExplorePage"];
    return {
      hook,
      body,
      hashtags,
      full_caption: `${hook}\n\n${body}\n\n.\n.\n${hashtags.join(" ")}`,
      image_prompt: `Futuristic cinematic render representing ${topic}, neon accents, 8k`
    };
  }
}
