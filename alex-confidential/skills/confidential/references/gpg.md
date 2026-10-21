# gpg Reference (signing and offline archives)

Verified against GnuPG 2.4.4. In this toolkit gpg signs cryptoid/pagevault output and
makes offline archives; general gpg usage is out of scope. Recipes are non-interactive
(`--batch`) where scripts need them; drop `--batch` to get the normal prompts.

```bash
# Sign / verify (detached: FILE.sig beside FILE)
gpg --detach-sign -u "$MY_FPR" _locked/report.pdf.html
shopt -s globstar nullglob   # bash: needed for ** to recurse
for f in public/**/*.html; do gpg --batch --yes --detach-sign "$f"; done

# Verify AGAINST THE EXPECTED SIGNER, not just "Good signature" (gpg --verify exits 0
# for any valid key in your keyring). Either a keyring holding only that signer:
gpgv --keyring ./signer.kbx report.pdf.html.sig report.pdf.html
# or pin the fingerprint from gpg's status output:
[ "$(gpg --status-fd 1 --verify report.pdf.html.sig report.pdf.html 2>/dev/null \
    | awk '$2=="VALIDSIG"{print $3}')" = "$SIGNER_FPR" ] && pagevault unlock report.pdf.html

# Importing someone's key: compare the fingerprint out of band, then local-sign it.
gpg --import alice.pub
gpg --fingerprint alice@example.com      # confirm by phone/in person
gpg --quick-lsign-key "$ALICE_FPR"       # never "trust 5 (ultimate)": that is for YOUR keys

# Offline archive to a recipient (or yourself), optionally signed
gpg -e -r "$RECIPIENT_FPR" -o report.pdf.gpg report.pdf
gpg -se -u "$MY_FPR" -r "$RECIPIENT_FPR" -o report.pdf.gpg report.pdf

# Passphrase archive. Interactive: gpg -c report.pdf (prompts). Scripted: the passphrase
# comes from a 0600 file or fd 3, never argv. gpg 2.1+ needs --pinentry-mode loopback.
gpg --batch --yes --pinentry-mode loopback --passphrase-file "$PWFILE" -c report.pdf
gpg --batch --pinentry-mode loopback --passphrase-fd 3 -o report.pdf -d report.pdf.gpg 3<<<"$GPG_PW"
```

The default symmetric cipher is already AES256; do not add `--cipher-algo` (the man page
warns it can violate OpenPGP preferences).
