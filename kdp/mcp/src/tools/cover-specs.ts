import { calculateCoverDimensions, type CoverDimensions } from "../lib/cover-layout.js";
import { CoverSpecsSchema, type CoverSpecsInput } from "../lib/schemas.js";
import type { PaperType, TrimSize } from "../lib/kdp-specs.js";

export type CoverSpecsOutput = CoverDimensions & { trim_size: TrimSize; paper_type: PaperType };

export function handleCoverSpecs(input: CoverSpecsInput): CoverSpecsOutput {
  const { page_count, trim_size, paper_type } = CoverSpecsSchema.parse(input);
  return {
    trim_size,
    paper_type,
    ...calculateCoverDimensions({ pageCount: page_count, trimSize: trim_size, paperType: paper_type }),
  };
}
