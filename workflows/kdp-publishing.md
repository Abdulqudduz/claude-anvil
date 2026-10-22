# Workflow: Amazon KDP Book Publishing

This runbook guides an AI agent through preparing, formatting, generating covers for, and publishing commercial books on Amazon Kindle Direct Publishing (eBook and Paperback).

---

## Prerequisites and Setup
1. **Detect or Initialize Project**:
   - Run `python3 scripts/anvil detect`.
   - Ensure author and book metadata are configured in `.anvil/config.local.md` using `assets/templates/user-config-template.md`.
2. **Review Domain Reference**:
   - Consult [kdp-publishing.md](../references/kdp-publishing.md) for spine math, trim dimensions, and pricing thresholds.

---

## Phase 1: Manuscript Interior Audit

1. **Verify Interior Geometry**:
   - Confirm final page count, trim size (e.g., 5.5x8.5 or 6x9), and paper type (cream vs white).
   - Verify margins meet KDP minimums:
     - Gutter (inside margin): 0.375" (under 150 pages), 0.5" (151-300 pages), 0.625" (301-500 pages).
     - Outside/Top/Bottom margins: minimum 0.25".
2. **Compile Final Interior Artifacts**:
   - For Paperback: Export print-ready PDF with embedded fonts.
   - For eBook: Validate clean EPUB formatting with functional navigation table of contents.

---

## Phase 2: Listing Metadata and Copywriting Craft

1. **Craft the Blurb (Book Description)**:
   - Use the 5-part formula: Hook -> Premise -> Conflict -> Stakes -> Call to Action.
   - Format with Amazon-supported HTML tags (`<b>`, `<i>`, `<p>`, `<h2>`).
   - Consult `assets/exemplars/kdp-exemplars.md` for genre-specific examples.
2. **Generate Strategic Search Keywords**:
   - Populate exactly 7 multi-word keyword phrases (max 50 characters each).
   - Target high-intent customer search queries; do not repeat title words.
3. **Select Amazon Browse Categories**:
   - Identify 3 precise Amazon category paths with favorable sales rank competition.
4. **Author Bio**:
   - Tailor the author biography to the genre and target reader expectations.

---

## Phase 3: Automated Cover Generation Engine

1. **Calculate Exact Cover Dimensions**:
   - Calculate spine width using the formula:
     $$\text{Spine Width} = \text{Page Count} \times \text{Paper Factor}$$
   - Calculate full-wrap dimensions including 0.125" bleed on all outer edges.
2. **Generate or Validate Visuals**:
   - Front cover: Generate or audit 300 DPI high-resolution image (minimum 1600x2560 px for Kindle).
   - Use the Anvil MCP server (`kdp-cover`) or launcher script:
     ```bash
     bash kdp/mcp/run.sh
     ```
   - Generate full-wrap paperback PDF including back cover blurb, spine title typography, and barcode clearance zone.
3. **Pre-Flight Validation**:
   - Run `kdp_validate_cover` to verify pixel dimensions, aspect ratio, and bleed compliance.

---

## Phase 4: KDP Portal Submission and Proofing

1. **Upload Assets**:
   - Upload manuscript interior and cover wrap to KDP dashboard.
2. **Launch KDP Print Previewer**:
   - Check every page for text cutoff, spine misalignment, or font embedding warnings.
3. **Pricing and Royalty Strategy**:
   - For eBook: Select 70% royalty tier and set price between $2.99 and $9.99.
   - For Paperback: Compute print cost and verify list price meets royalty requirements.
4. **Order Physical Proof**:
   - Always order a physical printed proof copy before releasing the book live.
