# Tool output shapes

Full JSON shape for each Vista MCP tool's response.

## On-demand tools

`topic_followups`, `paper_followups`, `find_seminal`, `broad_followups`
all return the same paper shape:

```jsonc
{
  "topic" | "query" | "identifier": "...",        // input echoed back
  "params": { /* parameters used, useful for tuning */ },
  "papers": [ /* see Paper below */ ],
  "paper_count": 8
}
```

`paper_followups` returns just the single Paper (no wrapper). When a title
has no exact match it returns instead:

```jsonc
{ "identifier": "...", "error": "not found",
  "candidates": [ { "paper_id": "W...", "title": "...", "year": 2019, "cited_by_count": 120 } ] }
```

An unknown name in `broad_followups(fields=...)` is rejected by the tool
schema (an enum of the configured fields).

### Paper

```jsonc
{
  "paper_id": "W2907492528",                 // OpenAlex ID
  "title": "...",
  "authors": ["A. Author", "B. Coauthor"],   // truncated to 8
  "year": 2020,
  "venue": "Conference / journal name",
  "cited_by_count": 8883,
  "doi": "10.xxxx/yyyy",
  "arxiv_id": "1901.00596",
  "arxiv_url": "https://arxiv.org/abs/1901.00596",
  "doi_url": "https://doi.org/10.xxxx/yyyy",
  "abstract": "...",
  "field": "ad-hoc",                         // or ml | ai | stats | ransomware
  "track": "topic",                          // or recent | legacy | seed | broad | paper
  "sections": [
    {
      "type": "future_work",                 // future_work | limitations | discussion | conclusion
      "heading": "Future Directions",        // the actual heading we matched
      "method": "outline",                   // outline (PDF bookmarks) | font | regex
      "content": "...",                      // raw section text
      "char_count": 1914
    }
  ],
  "note": "pdf_unavailable"                  // optional; present when fetch failed
}
```

If a paper has no sections (PDF unavailable, extraction failed), the
`sections` array is empty and `note` may be set. Skip those papers in your
synthesis or flag them to the user.

## Catalog tools

`search_directions` and `list_directions` return the same row shape (both
read the `v_directions_full` view):

```jsonc
{
  "query": "...",                            // omitted in list_directions
  "count": 25,
  "results": [
    {
      "direction_id": 42,                    // use with mark_direction
      "direction": "...",
      "rationale": "...",
      "quote": "...",
      "feasibility": "medium",
      "novelty": "high",
      "dependencies": "...",
      "user_status": "open",
      "user_notes": null,
      "field_tags": ["gnn", "theory"],
      "paper_id": "Wxxx",                    // use with get_paper
      "paper_title": "...",
      "year": 2020,
      "venue": "...",
      "field": "ml",
      "track": "recent",
      "cited_by_count": 1234,
      "doi": "...",
      "arxiv_id": "..."
    }
  ]
}
```

`get_paper`: same as Paper above, plus `directions: [...]` (rows from the
directions table).

## Curation tools

`submit_directions`:

```jsonc
{ "paper_id": "Wxxx", "mode": "append", "stored": 5, "total": 12 }
// or { "paper_id": "...", "error": "paper not in store" }
```

`stored` is how many were written; `total` is the paper's direction count
afterwards. A direction whose text matches an existing one (ignoring case and
spacing) updates it in place, keeping its `direction_id`, `user_status`, and
`user_notes` and merging tags. `mode="replace"` also deletes the paper's other
directions unless they are curated (status not `open`, or notes set).

`mark_direction`:

```jsonc
{ "direction_id": 42, "status": "interesting", "notes": "..." }
// or { "direction_id": 42, "error": "no such direction" }
```

## Pipeline tools

`discover`:

```jsonc
{ "counts": { "ml/recent": 25, "ai/recent": 20, ... } }
```

`extract_pending`:

```jsonc
{
  "fetch":   { "attempted": 30, "ok": 27, "failed": 3 },
  "extract": { "attempted": 27, "with_sections": 25, "no_sections": 2 }
}
```

`render_markdown`:

```jsonc
{ "render": { "papers": 75 }, "out_dir": "/path/to/out" }
```

`status`:

```jsonc
{
  "totals": { "papers": 75, "directions": 432 },
  "by_field_track": [
    { "field": "ml", "track": "recent", "papers": 25, "with_pdf": 25,
      "with_sections": 24, "with_directions": 24 }   // with_sections: non-empty only
  ]
}
```

## SQL tools

`run_sql`:

```jsonc
{ "row_count": 12, "truncated": false, "rows": [ { /* per-column key-value */ } ] }
// or { "error": "syntax error..." }
```

At most `limit` (default 200) rows come back; `truncated` is true when more
existed. Anything but a read (DML, DDL, ATTACH, PRAGMA, VACUUM INTO) fails
with an engine `"not authorized"` error. A query running longer than about 3 seconds is
aborted with `{"error": "query exceeded the 3s time limit"}`.

`get_schema`:

```jsonc
{ "schema": "CREATE TABLE papers (...) ..." }
```
