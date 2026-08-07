# WAtranscribe TWA — status

Last updated: 2026-08-07

## What this is

A native Android app (`com.flyboybyte.watranscribe`) that wraps
`transcribe.flyboybyte.com` as a Trusted Web Activity (TWA), built with
Google's `bubblewrap` CLI. It exists because the site's existing PWA Web
Share Target (see `trans/app/static/manifest.json`) only registers with
Android's system share sheet if the browser mints a real **WebAPK** — which
requires a round-trip to Google's WebAPK server. On GrapheneOS (no Google
services), that round-trip never happens: Chrome/Brave both produce a
good-looking home-screen shortcut that never actually registers as a share
target (confirmed via `chrome://webapks`, which listed nothing).

A TWA sidesteps that entirely — it's a real, locally-built, signed APK with
the `SEND`/`SEND_MULTIPLE` intent-filter compiled directly into
`AndroidManifest.xml` at build time. No Google server dependency at
install time.

## How it was built (so this is reproducible, not just a one-off)

1. `bubblewrap`'s interactive `init` wizard is unusable non-interactively —
   its free-text `Input` prompts don't get consumed correctly over a piped
   stdin (confirmed repeatedly; confirm/Y-N prompts work fine piped, only
   text-input prompts break). Worked around this entirely: `gen.js` calls
   `@bubblewrap/core`'s `TwaManifest.fromWebManifest(url)` +
   `TwaGenerator.createTwaProject()` directly, bypassing the wizard.
2. Local tooling reused, no redundant downloads: JDK 21/26 via
   `archlinux-java`, but `bubblewrap` hard-requires JDK **17** specifically
   (Android Gradle Plugin's pinned/validated version) — neither installed
   version satisfies that, so bubblewrap's own managed JDK 17 was installed
   to `~/.bubblewrap/jdk` (~180-220MB, isolated, doesn't touch system Java).
   The Android SDK was **not** redownloaded — pointed at the existing
   `~/Android/Sdk`.
3. Bubblewrap's SDK path validator only recognizes a legacy top-level
   `tools/` or `bin/` folder; modern SDKs only have
   `cmdline-tools/latest/bin`. Fixed with a symlink:
   `~/Android/Sdk/bin -> ~/Android/Sdk/cmdline-tools/latest/bin`. Purely
   additive, doesn't touch the real SDK layout.
4. Signed with the **same keystore as `drag-tree`**
   (`/home/logan/@flyboybyte__drag-tree.jks`, alias
   `e2f4affc23a7141f202d26f6d9f2d4d0`) — Logan's explicit, deliberate choice
   ("I've been signing all my apps the same"), not a fresh dedicated key.
   Passwords come from `drag-tree/android/local.properties`
   (`RELEASE_STORE_PASSWORD` / `RELEASE_KEY_PASSWORD`) — never printed to
   chat or committed anywhere; passed straight into the build's environment
   (`BUBBLEWRAP_KEYSTORE_PASSWORD` / `BUBBLEWRAP_KEY_PASSWORD`) at build
   time only.
5. `trans/app/routes/transcribe.py` now serves
   `/.well-known/assetlinks.json` (exempted from the password gate in
   `app/auth.py`) with this APK's SHA-256 cert fingerprint
   (`FF:73:9C:...:83:7A`) — required for the TWA to open full-screen
   instead of falling back to a Custom Tab with an address bar. Deployed
   and confirmed live: `curl https://transcribe.flyboybyte.com/.well-known/assetlinks.json`.

## Known cosmetic issue, not fixed

Bubblewrap translates every entry in the source manifest's
`share_target.params.files[0].accept` array (which mixes MIME types and
file extensions, e.g. `"audio/*", ".opus", ".m4a"`) into native Android
`<data android:mimeType="...">` entries verbatim — so `.opus`, `.m4a`, etc.
end up as literal (invalid) `mimeType` values that never match anything.
Harmless: the `audio/*` wildcard entry is valid and does the real work,
since WhatsApp/Signal always set a real audio MIME type on shared files.
Not worth stripping extensions from the source `manifest.json` just for
this, since they're still useful for the browser-side PWA share target
(non-TWA users) as a fallback when a sharer's MIME type is generic.

## Current blocker

APK built, signature-verified locally (`apksigner verify`, zip integrity
checked with `unzip -t`, no native libs so no ABI concerns, SHA-256 of the
built file: `387fca79b4ea4dc7f647672e6d8e4b8bafc62a32eeaf723749aa141e4abf341b`).
Sent to Logan's phone via chat file transfer; install failed with Android's
generic "problem parsing the package" error, which — combined with a clean
local verification — points to the chat transfer corrupting/truncating the
file, not a build defect.

**2026-08-07**: project moved to `/home/logan/projects/trans/watranscribe-twa/`
(nested inside `trans/` alongside `watranscribe-bot/`, same "own git repo
nested on disk" pattern — see `trans/.gitignore`), pushed to its own GitHub
repo (`https://github.com/flyboy-byte/watranscribe-twa`, private), and the
built APK attached as a GitHub Release for direct phone download.

**v1.0.0 also failed to install** (confirmed not a transfer issue — the
downloaded file was byte-identical to the local build). Root cause: the
bubblewrap template's default `compileSdkVersion`/`targetSdkVersion` 36
(Android 16), pulled in transitively via `androidx.browser:browser:
1.9.0-alpha04` (an **alpha** release) through `androidbrowserhelper`.
Targeting an alpha dependency and a very new API level is the most likely
cause of "problem parsing the package" — aapt2/AGP output tied to a
non-stable API level can produce a manifest/resource binary format the
device's PackageParser doesn't handle correctly.

**Fix (v1.0.1)**: `app/build.gradle` now pins `compileSdkVersion`/
`targetSdkVersion` to **35** (stable, Android 15) and forces
`androidx.browser` to the last stable release (**1.8.0**) via a
`resolutionStrategy.force` block — added *after* the `dependencies` block
that bubblewrap's template generates, since `node gen.js` regenerates
`app/build.gradle` from that template every time and will wipe this
override if `gen.js` is rerun. **Reapply the `configurations.all {
resolutionStrategy { force 'androidx.browser:browser:1.8.0' } }` block and
the `compileSdkVersion 35` / `targetSdkVersion 35` edits after any future
`node gen.js` regeneration**, before rebuilding.
Released: https://github.com/flyboy-byte/watranscribe-twa/releases/tag/v1.0.1

## To resume

1. On the phone, open
   https://github.com/flyboy-byte/watranscribe-twa/releases/tag/v1.0.1 and
   download `app-release-signed.apk` directly (v1.0.0 is left up for
   history but is known-broken — use v1.0.1).
2. Install it, open the app once, confirm it launches full-screen (no
   address bar) — this is the actual asset-links verification working.
3. Test: share a real voice note to it from WhatsApp or Signal.
4. If the intent-filter still doesn't show up in the OS share sheet after
   a clean install, that's a genuine new bug worth investigating (unlike
   the previous WebAPK-minting dead end, which was environmental, not
   fixable from this side).
5. Fallback if the Release download also fails: `adb install -r
   app-release-signed.apk` with the phone connected via USB/wireless
   debugging (`adb devices -l` to confirm connection first).

## Rebuilding after a source change

```bash
cd ~/projects/trans/watranscribe-twa
node gen.js   # regenerates twa-manifest.json + project from the live manifest.json
STOREPASS=$(grep -E '^RELEASE_STORE_PASSWORD=' ~/projects/drag-tree/android/local.properties | cut -d= -f2-)
KEYPASS=$(grep -E '^RELEASE_KEY_PASSWORD=' ~/projects/drag-tree/android/local.properties | cut -d= -f2-)
export BUBBLEWRAP_KEYSTORE_PASSWORD="$STOREPASS" BUBBLEWRAP_KEY_PASSWORD="$KEYPASS"
unset STOREPASS KEYPASS
printf 'n\n' | ./node_modules/.bin/bubblewrap build --skipPwaValidation
```
