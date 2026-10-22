# Workflow: Content Operations, Cross-Posting, and Intelligence

This runbook guides an AI agent through multi-platform cross-posting with Crier, repository health audits with Repoindex, static site publishing with MF, and document encryption with Alex-Confidential.

---

## Prerequisites and Setup
1. **Detect or Initialize Project**:
   - Run `python3 scripts/anvil detect`.
2. **Review Domain Reference**:
   - Consult [content-operations.md](../references/content-operations.md) for detailed platform limits and encryption selection matrices.

---

## Phase 1: Cross-Platform Content Distribution (Crier)

1. **Identify Unposted Content**:
   - Query unposted blog posts via Crier MCP tool or local directory search.
2. **Transform Formatting per Target**:
   - For long-form (Dev.to / Hashnode): Add canonical URL, adapt markdown headers.
   - For microblogging (Bluesky / Mastodon / Twitter): Condense post into a compelling short-form summary or thread respecting character limits (300 for Bluesky, 500 for Mastodon, 280 for Twitter).
3. **Two-Phase Approval**:
   - Present preview of all transformed text to the author.
   - Upon author approval, dispatch cross-posting calls.

---

## Phase 2: Repository Collection Intelligence (Repoindex)

1. **Sprint Triage**:
   - Identify uncommitted files, unpushed commits, and release candidates across local checkouts:
     ```bash
     python3 scripts/anvil status
     ```
2. **Audit Gaps**:
   - Inspect missing licenses, broken CI, or stale dependencies.
3. **Weekly Digest**:
   - Compile commit velocity and changelog notes into an activity report.

---

## Phase 3: Cryptographic Protection (Alex-Confidential)

1. **Determine Target Environment**:
   - Hugo static blog -> Use `cryptoid`.
   - Standalone HTML or browser asset -> Use `pagevault`.
   - Raw developer file, credential tarball, or signing -> Use `gpg`.
2. **Execution**:
   - For `cryptoid`: Encrypt markdown section with password prompt.
   - For `pagevault`: Compile into self-decrypting HTML package.
   - For `gpg`: Sign or encrypt using recipient public key (`gpg -e -r <recipient> <file>`).
