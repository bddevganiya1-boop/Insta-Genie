export interface InstagramPublishResult {
  success: boolean;
  container_id?: string;
  published_id?: string;
  permalink?: string;
  error?: string;
}

export class MetaInstagramClient {
  private accountId: string;
  private accessToken: string;
  private apiVersion: string;
  private isDryRun: boolean;

  constructor(env: any) {
    this.accountId = env.INSTAGRAM_ACCOUNT_ID || "";
    this.accessToken = env.INSTAGRAM_ACCESS_TOKEN || "";
    this.apiVersion = env.META_GRAPH_API_VERSION || "v20.0";
    this.isDryRun = env.DRY_RUN === "true" || !this.accountId || !this.accessToken;
  }

  async publishPhoto(imageUrl: string, caption: string): Promise<InstagramPublishResult> {
    if (this.isDryRun) {
      console.log("[DRY_RUN] Simulating Meta Graph API publish.");
      return {
        success: true,
        container_id: "mock_container_987654321",
        published_id: "18029384729182391",
        permalink: "https://www.instagram.com/p/C_mockPostInstaGenie/"
      };
    }

    try {
      // 1. Create container
      const containerUrl = `https://graph.facebook.com/${this.apiVersion}/${this.accountId}/media`;
      const containerRes = await fetch(containerUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_url: imageUrl,
          caption: caption,
          access_token: this.accessToken
        })
      });

      const containerData: any = await containerRes.json();
      if (!containerRes.ok || !containerData.id) {
        throw new Error(`Failed to create media container: ${JSON.stringify(containerData)}`);
      }

      const creationId = containerData.id;

      // 2. Poll status if needed (wait 2s)
      await new Promise(r => setTimeout(r, 2000));

      // 3. Publish
      const publishUrl = `https://graph.facebook.com/${this.apiVersion}/${this.accountId}/media_publish`;
      const publishRes = await fetch(publishUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          creation_id: creationId,
          access_token: this.accessToken
        })
      });

      const publishData: any = await publishRes.json();
      if (!publishRes.ok || !publishData.id) {
        throw new Error(`Failed to publish container: ${JSON.stringify(publishData)}`);
      }

      const publishedId = publishData.id;
      return {
        success: true,
        container_id: creationId,
        published_id: publishedId,
        permalink: `https://www.instagram.com/p/${publishedId}/`
      };
    } catch (err: any) {
      return {
        success: false,
        error: err.message
      };
    }
  }
}
