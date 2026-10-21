# kdp: Claude Code Plugin

Amazon KDP (Kindle Direct Publishing) book publishing for Claude Code. Audit
manuscripts against KDP requirements, craft Amazon listings, generate and
validate covers, and run the full publishing workflow, for technical books,
fiction, and general nonfiction.

## Components

| Type | Name | Purpose |
|------|------|---------|
| Skill | `/kdp:kdp-audit` | Audit manuscript formatting, cover specs, and metadata against KDP requirements |
| Skill | `/kdp:kdp-listing` | Craft Amazon listing: blurb, keywords, categories, author bio |
| Skill | `/kdp:kdp-publish` | Full KDP publishing workflow from manuscript to submission |
| MCP tool | `kdp_cover_specs` | Paperback wrap dimensions, spine width, bleed, allowed page range |
| MCP tool | `kdp_validate_cover` | Check a cover image against KDP's eBook or paperback specs |
| MCP tool | `kdp_generate_cover` | Generate a front cover with OpenAI image generation (paid per image) |
| MCP tool | `kdp_generate_full_wrap` | Build a full paperback wrap PDF from a front cover and blurb |

## Install

```bash
/plugin install kdp@queelius-plugins
```

The MCP server needs Node.js and npm. On first start (and after an update that
changes its dependencies) it installs them into the plugin's persistent data
directory; this takes a few seconds and needs network access. When working
from a local checkout, `npm install` in `mcp/` works too.

`kdp_generate_cover` needs `OPENAI_API_KEY` in the environment that launches
Claude Code. The other tools work without it.

## User Config

Skills read `.claude/kdp.local.md` in your book project for author and KDP
preferences. On first run, the skill offers to create one from the bundled
template (`docs/user-config-template.md`).

## License

MIT
