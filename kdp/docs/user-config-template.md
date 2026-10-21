---
# kdp user configuration
# Copy this file to .claude/kdp.local.md in your project and fill in your details.

# Primary author
author:
  name: "First M. Last"
  email: "you@example.com"
  bio: ""                                # general author bio (adapted per genre by /kdp:kdp-listing)

# Amazon KDP book publication config
kdp:
  pen_name: null                       # if different from author.name
  publisher: null                      # imprint name, if any
  genre: ""                            # e.g., "epic fantasy", "thriller", "literary fiction"
  series:
    name: null                         # series name, if part of a series
    volume: null                       # volume/book number
  trim_size: "5.5x8.5"                 # one of KDP's trims (kdp_cover_specs lists them); "6x9" is common for nonfiction
  paper_type: "cream"                  # cream | white | groundwood (black ink); standard_color | premium_color (color on white)
  page_count: null                     # final interior page count (saved by /kdp:kdp-publish Phase 5; drives spine width)
  target: "both"                       # "ebook", "paperback", or "both"
  categories: []                       # Amazon browse category paths, 3 per format (populated by /kdp:kdp-listing)
  keywords: []                         # up to 7 phrases, each up to 50 characters (populated by /kdp:kdp-listing)
  blurb: ""                            # Amazon description (populated by /kdp:kdp-listing)
  author_bio: ""                       # genre-appropriate bio (populated by /kdp:kdp-listing)
  asin: null                           # eBook ASIN (saved after first publish)
  asin_paperback: null                 # paperback ASIN (saved after first publish)
  cover:
    front: null                        # path to approved front cover image
    full_wrap: null                    # path to full-wrap PDF (paperback)
    art_direction: ""                  # description of desired cover art style
    color_scheme: null                 # back cover color as "#rrggbb", or null to auto-extract from the front
  manuscript:
    path: null                         # final manuscript file for upload (saved by /kdp:kdp-publish Phase 5)
---

## Additional Context

Any free-form notes about the book that might help with audits, listing craft,
or publication decisions. For example:

- Synopsis or pitch
- Target audience and comparable titles
- Publication timeline
- Notes on cover design or formatting decisions
