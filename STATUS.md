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
file, not a build defect. **Next step: install via `adb install` instead of
a chat file transfer**, once the phone is connected (USB debugging or
wireless debugging). Local `adb` is already set up
(`~/Android/Sdk/platform-tools/adb`), just needs the device connected —
`adb devices -l` showed nothing attached as of the last check.

## To resume

1. Connect phone (USB debugging or wireless debugging via Developer
   options), confirm with `adb devices -l`.
2. `adb install -r /home/logan/projects/watranscribe-twa/app-release-signed.apk`
3. Open the app once, confirm it launches full-screen (no address bar) —
   this is the actual asset-links verification working.
4. Test: share a real voice note to it from WhatsApp or Signal.
5. If the intent-filter still doesn't show up in the OS share sheet after
   a real ADB install, that's a genuine new bug worth investigating
   (unlike the previous WebAPK-minting dead end, which was environmental,
   not fixable from this side).

## Rebuilding after a source change

```bash
cd ~/projects/watranscribe-twa
node gen.js   # regenerates twa-manifest.json + project from the live manifest.json
STOREPASS=$(grep -E '^RELEASE_STORE_PASSWORD=' ~/projects/drag-tree/android/local.properties | cut -d= -f2-)
KEYPASS=$(grep -E '^RELEASE_KEY_PASSWORD=' ~/projects/drag-tree/android/local.properties | cut -d= -f2-)
export BUBBLEWRAP_KEYSTORE_PASSWORD="$STOREPASS" BUBBLEWRAP_KEY_PASSWORD="$KEYPASS"
unset STOREPASS KEYPASS
printf 'n\n' | ./node_modules/.bin/bubblewrap build --skipPwaValidation
```
