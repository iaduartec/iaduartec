import { createAdminClient } from "npm:@insforge/sdk";

const insforge = createAdminClient({
  baseUrl: Deno.env.get("INSFORGE_URL")!,
  apiKey: Deno.env.get("INSFORGE_API_KEY")!
});

const webhookSecret = Deno.env.get("REVOLUT_WEBHOOK_SECRET");
if (!webhookSecret) {
  throw new Error("REVOLUT_WEBHOOK_SECRET must be configured");
}

export default async function (req: Request) {
  try {
    const authorization = req.headers.get("authorization");
    if (authorization !== `Bearer ${webhookSecret}`) {
      return new Response(JSON.stringify({ ok: false, error: "unauthorized" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }

    const { body_preview } = await req.json();
    if (typeof body_preview !== "string" || body_preview.length === 0 || body_preview.length > 50000) {
      return new Response(JSON.stringify({ ok: false, error: "invalid_body_preview" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    const prompt = `Parse this email body into JSON: { "asset_symbol": string, "side": "BUY" | "SELL", "quantity": number, "price": number }. Email: ${body_preview}`;

    // Using insforge.ai for AI completions as instructed
    const { data: aiResponse, error: aiError } = await insforge.ai.chat.completions.create({
      model: 'openai/gpt-4o',
      messages: [{ role: 'user', content: prompt }]
    });

    if (aiError) throw aiError;

    // AI content is typically a string, need to ensure valid JSON parsing
    const content = aiResponse.choices[0].message.content;
    const trade = JSON.parse(content.replace(/```json\n?|\n?```/g, ''));
    if (
      !trade ||
      typeof trade.asset_symbol !== "string" ||
      !/^[A-Z0-9._-]{1,32}$/.test(trade.asset_symbol) ||
      !["BUY", "SELL"].includes(trade.side) ||
      !Number.isFinite(trade.quantity) || trade.quantity <= 0 ||
      !Number.isFinite(trade.price) || trade.price < 0
    ) {
      throw new Error("invalid_trade");
    }

    const { error: dbError } = await insforge.database.from("trading_trades").insert([trade]);

    if (dbError) throw dbError;

    return new Response(JSON.stringify({ ok: true }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    console.error("Error processing request:", error);
    const message = error instanceof Error ? error.message : "request_failed";
    return new Response(JSON.stringify({ ok: false, error: message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
