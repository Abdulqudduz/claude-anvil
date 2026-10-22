# Content Operations, Intelligence, and Encryption Reference

This document provides complete domain knowledge for cross-platform content distribution (Crier), repository intelligence (Repoindex), static site operations (MF), and cryptographic confidentiality (Alex-Confidential) using the Anvil skill.

---

## 1. Multi-Platform Cross-Posting (Crier)

Crier distributes long-form and short-form content from a source blog (e.g., Hugo, Jekyll, Astro) to multiple external networks while respecting each platform's distinct formatting, character constraints, and API semantics.

### Supported Platforms and Invariants

| Platform | Type | Max Chars | Special Requirements |
|----------|------|-----------|----------------------|
| **Dev.to** | Long-form | Unlimited | Requires `canonical_url`, frontmatter tags, markdown |
| **Hashnode** | Long-form | Unlimited | Requires `canonical_url`, publication ID, markdown |
| **Medium** | Long-form | Unlimited | Requires canonical link, import API |
| **Bluesky** | Microblog | 300 | Threading support, facets for links and mentions |
| **Mastodon** | Microblog | 500 (typical)| Instance-specific limits, CW (content warnings) |
| **Twitter / X**| Microblog| 280 | Strict character counts, thread numbering |

### The Two-Phase Cross-Posting Protocol
1. **Audit & Preview Phase**:
   - Query unposted articles via `crier_unposted` or local file glob.
   - Adapt long-form prose into short-form microblog threads or cross-post markdown.
   - Present the full formatted draft to the author for explicit confirmation.
2. **Publish Phase**:
   - Dispatch approved posts through the MCP server (`crier_publish`).
   - Record publication timestamp and remote URL in local frontmatter or database.

---

## 2. Repository Intelligence and Operations (Repoindex)

Repoindex provides structured, MCP-first intelligence across collections of Git repositories:

### Core Workflows
- **Sprint Triage (`repo-sprint`)**: Evaluates all local checkouts and prioritizes repos requiring attention:
  1. Dirty uncommitted changes
  2. Unpushed local commits
  3. Release candidates (tagged or bumped without release)
  4. Audit gaps (missing tests, failing CI, stale dependencies)
- **Status Rollup (`repo-status`)**: Generates an overview of branches, recent commit velocity, and open issues for a specific repo or group.
- **Weekly Digest (`repo-week`)**: Aggregates all development work across the repository collection over a given time window (default 7 days).
- **Mirroring (`repo-mirror`)**: Synchronizes local checkouts to external backup or mirror remotes (e.g., GitLab, self-hosted forge).

---

## 3. Confidentiality and Cryptographic Toolkit (Alex-Confidential)

Smart routing between three complementary encryption tools based on target environment and threat model:

```
                          ┌─────────────────────────────┐
                          │ What needs encryption?      │
                          └──────────────┬──────────────┘
                                         │
                 ┌───────────────────────┼───────────────────────┐
                 ▼                       ▼                       ▼
      ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
      │ Hugo Markdown Post  │ │ Standalone HTML /   │ │ Raw Files, Backups, │
      │ or Site Section     │ │ Browser Asset       │ │ Signatures, Keys    │
      └──────────┬──────────┘ └──────────┬──────────┘ └──────────┬──────────┘
                 │                       │                       │
                 ▼                       ▼                       ▼
      ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
      │      cryptoid       │ │      pagevault      │ │         gpg         │
      │ In-browser decrypt  │ │ Self-contained HTML │ │ Asymmetric signing  │
      │ via WebCrypto API   │ │ with embedded viewer│ │ and offline archive │
      └─────────────────────┘ └─────────────────────┘ └─────────────────────┘
```

### Selection Rules:
1. **`cryptoid`**: Use when authoring articles for a Hugo static site where certain sections or whole posts require password protection for select readers.
2. **`pagevault`**: Use when sharing private HTML dashboards, documents, or data files with non-technical stakeholders who only have a web browser.
3. **`gpg`**: Use for standard developer workflows: signing commits, encrypting credential tarballs, asymmetric key exchange, and offline archives.

---

## 4. Hugo Site Management (MF)

Metafunctor site management coordinates content architecture over the `mf` CLI:
- **Taxonomy Audits**: Validates tag and category hierarchies across hundreds of posts.
- **Paper to Post Synchronization**: Extracts abstracts, figures, and key findings from academic papers into reader-friendly blog summaries.
- **Series Management**: Maintains sequential navigational links and metadata across multi-part essay series.
- **Handoff to Crier**: Once content is published or updated on the Hugo site, trigger Crier to broadcast across external platforms.
