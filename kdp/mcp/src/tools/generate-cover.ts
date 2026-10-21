import { generateCoverImage } from "../lib/openai-client.js";
import { IMAGE_PRICE_USD, type ImageQuality } from "../lib/kdp-specs.js";
import { GenerateCoverSchema, type GenerateCoverInput } from "../lib/schemas.js";

export interface GenerateCoverOutput {
  path: string;
  quality: ImageQuality;
  /** OpenAI list price for this one image, from IMAGE_PRICE_USD. */
  estimated_cost_usd: number;
}

export async function handleGenerateCover(input: GenerateCoverInput): Promise<GenerateCoverOutput> {
  const args = GenerateCoverSchema.parse(input);
  const path = await generateCoverImage(args);
  return {
    path,
    quality: args.quality,
    estimated_cost_usd: IMAGE_PRICE_USD[args.quality],
  };
}
