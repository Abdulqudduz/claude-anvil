# alex-confidential: Claude Code Plugin

Confidentiality toolkit for Claude Code. Smart routing across three
complementary encryption tools: cryptoid (Hugo site encryption), pagevault
(HTML/file encryption), and gpg (file encryption and signing).

## Components

| Type | Name | Purpose |
|------|------|---------|
| Skill | `confidential` | Tool selection logic, usage patterns, and workflow guidance |

This is a skill-only plugin: the `confidential` skill triggers on natural
language (e.g. "encrypt this page", "sign this file"); there is no slash command.

## Install

```bash
# From the marketplace
/plugin install alex-confidential@queelius-plugins
```

## Requirements

The skill assumes these tools are installed and on PATH:

- `cryptoid` and `pagevault` (the user's own packages): `pip install pagevault` (on PyPI) and `pip install git+https://github.com/queelius/cryptoid` (cryptoid is not on PyPI)
- `gpg` (system package)

## Tool Selection

The skill picks the tool from what you're protecting and where it goes:
cryptoid for Hugo markdown, pagevault for HTML and files viewed in a browser,
gpg for signing and offline archives. The full selection table and decision
tree live in [`skills/confidential/SKILL.md`](skills/confidential/SKILL.md).

## License

MIT
