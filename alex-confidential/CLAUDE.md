# CLAUDE.md (alex-confidential plugin)

Editing guidance for the confidentiality plugin. Read before editing.

## Architecture

A skill-only plugin: no commands, no agents, no MCP server (none of the three
tools ships one; the CLIs are the interface). Routing and the cross-tool safety
rules live in `skills/confidential/SKILL.md`; exact command syntax lives in
`references/{cryptoid,pagevault,gpg}.md`.

- Edit `references/*.md` for tool-specific command syntax.
- Edit `SKILL.md` only for routing, compound workflows, or safety rules. Keep it
  lean: it loads in full on every trigger, so do not copy command blocks into it.

The skill triggers on natural language; there is no slash command.

## External dependencies

- `cryptoid` (the user's own package, source `~/github/repos/cryptoid`): Hugo
  markdown encryption.
- `pagevault` (the user's own package, source `~/github/repos/pagevault`): HTML
  and arbitrary-file encryption for browser delivery.
- `gpg` (system): signing and offline archives only. `gpg.md` deliberately
  covers just that role; do not grow it into a general gpg manual.

Each reference states the version it was verified against. When a CLI changes,
re-run its `--help` (and test on throwaway files in a temp dir with an isolated
`HOME`/`XDG_CONFIG_HOME`/`GNUPGHOME`, so real configs and keyrings are not
touched), then update the reference and its version line.

## Selection matrix

The cryptoid / pagevault / gpg selection table and decision tree live only in
`SKILL.md`. The README links to it rather than repeating it.

## Security-doc discipline

- Never document passing a secret on argv (`-p "pw"`, `--passphrase`,
  `echo "pw" |`). Show the prompt, the config file, `PAGEVAULT_PASSWORD`, or
  gpg's `--passphrase-file` / `--passphrase-fd 3` with `--pinentry-mode loopback`.
- Example configs contain cleartext credentials: keep the "add to .gitignore"
  warning and use obviously-fake placeholders.
- Signature-verification recipes must pin the expected signer (fingerprint or
  `gpgv --keyring`), and key import must go through fingerprint checking and
  `--quick-lsign-key`, never ultimate trust.
- Every "deploy" recipe must deploy the locked output, not the plaintext input.

## Version bumps

Keep `.claude-plugin/plugin.json` and the `alex-confidential` entry in the root
`.claude-plugin/marketplace.json` in sync.
