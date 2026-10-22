---
# Anvil Universal Project Configuration
# Location: .anvil/config.local.md (or .claude/pub-pipeline.local.md / .claude/kdp.local.md)

# Primary Author / Creator Metadata
author:
  name: "First M. Last"
  email: "you@example.com"
  orcid: "0000-0000-0000-0000"
  affiliation: "Institution or Independent"
  bio: "General professional author bio"

# Additional Co-authors / Collaborators
coauthors: []
  # - name: "Co Author"
  #   orcid: "0000-0000-0000-0000"
  #   email: "coauthor@example.com"
  #   affiliation: "Their Institution"

# Academic & Software Publication (Pub-Pipeline)
publication:
  title: ""
  venue_targets: []                    # e.g., ["CRAN", "JOSS", "JSS", "NeurIPS", "ICLR"]
  domain: ""                           # e.g., "computational statistics", "distributed systems"
  audience: ""                         # e.g., "researchers and practitioners"
  ai_usage:
    used: false
    tools: []                          # e.g., ["Google Antigravity", "OpenCode", "Claude Code"]
    scope: ""                          # e.g., "code validation, literature indexing assistance"
    human_oversight: "All technical claims and final text verified by authors"

# R Package Publishing Configuration (if applicable)
r_package:
  universe: ""                         # R-universe user or organization
  competitors: []                      # Existing CRAN packages in same space
  dependency_chain: []                 # Sibling packages that must precede on CRAN

# Python Package Publishing Configuration (if applicable)
python_package:
  package_name: ""
  pypi_repository: "pypi"              # "pypi" or "testpypi"

# Amazon KDP Book Publishing (if applicable)
kdp:
  pen_name: null                       # Pen name if distinct from author.name
  publisher: null                      # Imprint or publisher name
  genre: ""                            # e.g., "science fiction", "computer science", "thriller"
  series:
    name: null
    volume: null
  trim_size: "6x9"                     # "5.5x8.5", "6x9", "7x10", "8.5x11"
  paper_type: "white"                  # "cream", "white", "groundwood", "standard_color", "premium_color"
  page_count: null                     # Interior page count (used for spine width formula)
  target: "both"                       # "ebook", "paperback", or "both"
  categories: []                       # 3 Amazon browse category paths
  keywords: []                         # Up to 7 keyword phrases (max 50 chars each)
  blurb: ""                            # Formatted Amazon description
  author_bio: ""                       # Genre-tailored bio
  asin: null                           # eBook ASIN (populated after publish)
  asin_paperback: null                 # Paperback ASIN (populated after publish)
  cover:
    front: null                        # Path to approved front cover image
    full_wrap: null                    # Path to generated full-wrap PDF
    art_direction: ""                  # Visual aesthetic prompt for generative cover engine
    color_scheme: null                 # Spine/back hex color (e.g., "#1a1a2e") or null for auto
  manuscript:
    path: null                         # Final upload interior file (PDF or EPUB)
---

## Project Notes & Operational Context

Record domain notes, project genesis, comparable titles, target milestones, and design choices here:

- Background and motivation
- Key technical or creative innovations
- Constraints and special considerations
