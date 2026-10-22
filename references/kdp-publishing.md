# Amazon KDP Publishing and Cover Engine Reference

This document provides complete domain knowledge for commercial book publishing on Amazon Kindle Direct Publishing (KDP), including manuscript interior auditing, listing metadata craft, pricing strategy, and automated cover generation using the Anvil skill (embodying the KDP methodology).

---

## 1. Amazon KDP Publishing Architecture

Publishing a book on Amazon KDP spans two distinct formats (eBook and Paperback/Hardcover) and requires synchronized metadata and visual assets:

```
┌────────────────────────────────────────────────────────┐
│ Manuscript Interior (Word, EPUB, PDF, or LaTeX)        │
│ Interior proofing • Page budget • Formatting           │
└───────────────────────────┬────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌───────────────────────────┐ ┌───────────────────────────┐
│ Metadata & Listing Craft  │ │ Cover Engine & Visuals    │
│ • Blurb (Hook/Conflict)   │ │ • Front cover (300 DPI)   │
│ • 7 Strategic Keywords    │ │ • Spine width calculation │
│ • 3 Amazon Categories     │ │ • Full-wrap print PDF     │
└─────────────┬─────────────┘ └───────────┬───────────────┘
              └─────────────┬─────────────┘
                            ▼
┌────────────────────────────────────────────────────────┐
│ KDP Submission & Post-Launch Management                │
│ Pricing thresholds • KDP Select • Proof copies         │
└────────────────────────────────────────────────────────┘
```

---

## 2. Print Cover Geometry and Spine Mathematics

Paperback covers require an exact, single-sheet full-wrap cover (Back Cover + Spine + Front Cover + Bleed). The dimensions depend strictly on interior page count and paper type:

### A. Paper Thickness Multipliers
To compute spine width in inches:
$$\text{Spine Width} = \text{Page Count} \times \text{Paper Thickness Factor}$$

| Paper Type | Color | Factor (inches/page) |
|------------|-------|----------------------|
| **White**  | Black & White | `0.002252` |
| **Cream**  | Black & White | `0.0025`   |
| **Standard Color** | Color | `0.002252` |
| **Premium Color**  | Color | `0.002347` |

### B. Full-Wrap Dimension Calculations
For a trim width $W$, trim height $H$, spine width $S$, and standard print bleed $B = 0.125\text{ in}$:
$$\text{Total Width} = B + W + S + W + B = 2W + S + 2B$$
$$\text{Total Height} = H + 2B$$

At 300 DPI (dots per inch), convert inches to pixels:
$$\text{Width (px)} = \text{Total Width (in)} \times 300$$
$$\text{Height (px)} = \text{Total Height (in)} \times 300$$

### C. Safety Zones & Barcode Clearance
- **Spine Text**: Spine text is only allowed on books with **79 pages or more**. Keep text 0.0625" (1/16") away from both spine fold lines.
- **Bleed Margin**: All background images must extend 0.125" beyond the trim edge.
- **Live Matter Margin**: Keep all vital text and logos at least 0.25" inside the trim edge.
- **Barcode Zone**: KDP places a 2.0" wide $\times$ 1.2" high barcode on the lower-right quadrant of the back cover. Do not place critical text or artwork in this zone.

---

## 3. The Cover Generation Engine

Anvil includes a TypeScript MCP cover generation engine (`kdp/mcp/`) that renders production-ready covers:
- `kdp_cover_specs`: Computes exact pixel and inch dimensions for any trim size, paper type, and page count.
- `kdp_validate_cover`: Audits an image or PDF against KDP print geometry and resolution constraints.
- `kdp_generate_cover`: Generates a high-resolution front cover image with typography and art direction.
- `kdp_generate_full_wrap`: Combines front cover art, auto-extracted color schemes, styled spine typography, and back cover blurb into a print-ready full-wrap PDF.

---

## 4. Listing Craft Discipline

A book listing on Amazon must maximize both algorithmic discoverability and human conversion:

### A. The 5-Part Blurb Formula
1. **The Hook (Headline)**: Bold, 1-2 sentence high-concept hook that establishes genre and premise.
2. **The Character & World**: Introduce the protagonist, their everyday reality, and the inciting incident.
3. **The Conflict**: The primary antagonist, dilemma, or systemic obstacle.
4. **The Stakes**: What catastrophic outcome occurs if the protagonist fails?
5. **Call to Action (CTA)**: Genre tropes, comparable authors ("For fans of X and Y"), and an invitation to buy/read.

### B. The 7 Strategic Keyword Slots
Amazon allows up to 7 search keyword phrases (each up to 50 characters). Follow these rules:
- **Do**: Use multi-word customer search phrases (e.g., `hard sci fi space exploration`, `bayesian statistics textbook`).
- **Do**: Combine character traits, sub-genres, tropes, and thematic elements.
- **Don't**: Repeat words from the book title, subtitle, or author name (Amazon indexes those automatically).
- **Don't**: Include competitor names, trademarks, or subjective promotional claims like "best-selling" or "free".

### C. Category Selection
Select 3 exact Amazon browse category paths (e.g., `Books > Computers & Technology > Programming > Algorithms`). Choose categories that are relevant yet low enough in competition to rank in the Top 100 for that niche.

---

## 5. Pricing and Royalties

- **eBook 70% Royalty**: Price must be set between **$2.99 and $9.99** USD. Outside this window, royalty drops to 35%.
- **Paperback Royalty**: 60% of list price minus print cost:
  $$\text{Royalty} = (0.60 \times \text{List Price}) - \text{Fixed Cost} - (\text{Page Count} \times \text{Per-Page Cost})$$
- Always verify print cost against current Amazon KDP print pricing tables before confirming list price.
