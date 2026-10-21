# pagevault Reference

Verified against pagevault 0.4.2.

## Overview

Password-protect regions of HTML files or wrap arbitrary files into self-contained encrypted
HTML. Works with any static site generator. Uses AES-256-GCM with PBKDF2-SHA256 (310,000
iterations). All decryption happens client-side via WebCrypto API.

## Configuration: `.pagevault.yaml`

```yaml
password: "your-strong-passphrase"
salt: "auto-generated"

defaults:
  remember: "ask"          # "none", "session", "local", "ask"
  remember_days: 0         # 0 = no expiration
  auto_prompt: true        # Show password prompt on page load

template:
  title: "Protected Content"
  button_text: "Unlock"
  error_text: "Incorrect password"
  placeholder: "Enter password"
  # username_placeholder: "Enter username"  # multi-user mode
  color_primary: "#4CAF50"
  color_secondary: "#76B852"

# Multi-user (optional)
users:
  alice: "alice-password"
  bob: "bob-password"

# Managed globs (optional): paths that a bare `pagevault sync` re-encrypts
managed:
  - "_locked/**/*.html"
```

Create with `pagevault config init`. Add to `.gitignore`.

Environment variable overrides: `PAGEVAULT_PASSWORD`, `PAGEVAULT_SALT`.

A global config at `~/.config/pagevault/config.yaml` (or
`$XDG_CONFIG_HOME/pagevault/config.yaml`) has the same structure and is merged
under every project's `.pagevault.yaml`; local users override global users of
the same name. Edit it with `pagevault config set --global ...`.

The password hint is per-lock (`--hint TEXT`), not a `template:` field.

## CLI Commands

Passwords come from the config, `PAGEVAULT_PASSWORD`, or a prompt. `-p/--password`
exists but puts the secret on argv (visible in `ps`, saved in history): avoid it.

### Lock (Encrypt)

Output never overwrites the input. HTML goes to `_locked/` (change with `-d DIR`;
`-d` may not contain the input). Non-HTML files become a sibling `NAME.html`
(`report.pdf` -> `report.html`); choose the path with `-o FILE`, since `-d` is
rejected for non-HTML input.

```bash
pagevault lock page.html                    # Marked regions (or whole body) -> _locked/page.html
pagevault lock docs/ -r -d _locked/docs/    # HTML files only, recursive; other files ignored
pagevault lock report.pdf -o _locked/report.pdf.html   # Wrap a file with its viewer
pagevault lock site/ --site -o site.html    # Bundle a whole directory (all file types)
pagevault lock page.html -s "#secret"       # Encrypt only matching selector
pagevault lock page.html --pad              # Pad to hide content size
```

### Unlock (Decrypt)
```bash
pagevault unlock _locked/page.html          # Back to marked state, written to _unlocked/
pagevault unlock _locked/ -r -d restored/   # Recursive
```

`unlock --stdout` in 0.4.2 does NOT recover a wrapped file's original bytes (it
echoes the HTML), despite its help text. Keep the original, or open the locked
file in a browser via `pagevault dev serve`.

### Mark (Add Encryption Tags)
```bash
pagevault mark page.html                    # Wrap entire body
pagevault mark page.html -s ".private"      # Wrap elements matching CSS selector
pagevault mark page.html -s "#secret" --hint "Contact admin"
```

### Inspect and Verify
```bash
pagevault inspect encrypted.html            # Show metadata (no password needed)
pagevault inspect encrypted.html --check   # Prompts for the password (exit 0 = correct)
pagevault inspect encrypted.html --check -u alice  # Multi-user check
pagevault audit                             # Health check config and passwords
```

### Config
```bash
pagevault config init                       # Create .pagevault.yaml
pagevault config show                       # Display current config
pagevault config where                      # Find config file location
pagevault config set KEY VALUE              # Update a config value
pagevault config user add alice             # Add a user (prompts for password)
pagevault config user list                  # List users
pagevault config user passwd alice          # Change a user's password
pagevault config user rm alice              # Remove a user
```

### Dev Preview
```bash
pagevault dev serve _locked/                # Local HTTP preview (WebCrypto needs
                                            # http(s); file:// breaks decryption)
```

### Sync (Re-wrap keys for the current users)
```bash
pagevault sync _locked/ -r                  # Re-wrap keys after adding/removing users
```

`sync` requires a `users:` block (it errors without one). It decrypts each file
with a credential from the current config, then re-encrypts with a fresh content
key wrapped for the current users, so removed users lose access to the new
ciphertext. It cannot recover a file none of the current passwords open. To
change a single shared password, unlock and re-lock instead.

## Viewer Plugins

pagevault includes built-in viewers for common file types. When locking a non-HTML file,
the appropriate viewer is automatically selected:

| File type | Viewer | What it does |
|-----------|--------|-------------|
| `.html` | HTML viewer | Renders decrypted HTML inline |
| `.md` | Markdown viewer | Renders markdown to HTML |
| `.pdf` | PDF viewer | Embedded PDF viewer |
| `.png`, `.jpg`, `.gif`, `.svg` | Image viewer | Displays image |
| `.mp4`, `.webm` | Video viewer | Video player |
| `.mp3`, `.wav` | Audio viewer | Audio player |
| `.txt`, `.csv`, `.json` | Text viewer | Monospace text display |

Other file types get a download link after successful decryption.

## Self-Contained Output

Every encrypted HTML file includes the full decryption runtime:
- Web Component (`<pagevault-encrypted>`)
- JavaScript decryption logic (WebCrypto API)
- CSS for the password prompt UI
- No external dependencies at runtime

## Configuration Cascade

Priority order (highest first):
1. Command-line arguments (`--hint`, etc.; `-p` works but avoid it)
2. Environment variables (`PAGEVAULT_PASSWORD`, `PAGEVAULT_SALT`)
3. `.pagevault.yaml` (searched upward from the working directory)
4. Global config (`~/.config/pagevault/config.yaml`)
5. Built-in defaults

## Hugo Integration Example

```bash
hugo -d build/
# lock refuses to write inside its input, so lock to a staging dir...
pagevault lock build/posts/ -r -d _locked/posts/ --css styles/pagevault.css
# ...then copy the locked pages over the plaintext ones before deploying build/
cp -r _locked/posts/. build/posts/
grep -rl 'TEXT-ONLY-IN-THE-SECRET-PAGE' build/ && echo "PLAINTEXT LEFT, do not deploy"
```

## Known Limitations

- Encrypted regions are replaced with password prompts; page structure is visible
- File sizes may hint at content length (use `--pad` to mitigate)
- JavaScript must be enabled for decryption
