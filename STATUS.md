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

## Install failure — root cause found and fixed (2026-08-07)

Every install attempt (v1.0.0 chat transfer, v1.0.0 GitHub Release
download, v1.0.1 rebuild) failed with a generic-looking parse error. Two
wrong theories were chased first (chat-transfer corruption — ruled out by
a byte-identical download comparison; targeting a too-new/alpha SDK —
ruled out once Logan confirmed his phone runs Android 17). The real cause,
found via `pm install` on-device through Termux/adb, which surfaces the
actual Android error instead of the generic Play-Store-style dialog:

```
Failure [INSTALL_PARSE_FAILED_MANIFEST_MALFORMED:
android.content.IntentFilter$MalformedMimeTypeException: .opus]
```

The source site manifest's `share_target.params.files[0].accept` list
mixed real MIME types with bare file extensions (`"audio/*", ".opus",
".m4a", ".mp3", ...`). Bubblewrap translates every entry verbatim into
`AndroidManifest.xml` `<data android:mimeType="...">`. A bare extension
isn't a valid `type/subtype` MIME string, and Android's manifest parser
throws on the **first** invalid one it hits — which fails the entire
package parse, not just that one intent-filter entry. This is why it
failed identically regardless of signing, SDK level, or transfer method:
none of those were ever the problem.

**Fix**: `trans/app/static/manifest.json`'s `accept` list now only
contains real MIME types (`audio/*`, `audio/opus`, `audio/mp4`,
`audio/mpeg`, `audio/wav`, `audio/ogg`) — deployed live. Regenerated this
project with `node gen.js` (which re-reads the live manifest and rebuilds
`AndroidManifest.xml` with corrected `<data>` entries), rebuilt, and
reverted the earlier compileSdk-35/androidx.browser-1.8.0 pin from v1.0.1
back to bubblewrap's plain defaults (compileSdk/targetSdk 36) since that
was never the real bug.

Verified on the new APK: `aapt2 dump xmltree` shows all six `mimeType`
values are now valid `type/subtype` strings; `apksigner verify --verbose`
shows v1/v2/v3 all pass.

Released: https://github.com/flyboy-byte/watranscribe-twa/releases/tag/v1.0.2
(v1.0.0 and v1.0.1 left up for history but are known-broken — use v1.0.2.)

## To resume

1. On the phone, download `app-release-signed.apk` from
   https://github.com/flyboy-byte/watranscribe-twa/releases/tag/v1.0.2 and
   install it.
2. Open the app once, confirm it launches full-screen (no address bar) —
   this is the asset-links verification working.
3. Test: share a real voice note to it from WhatsApp or Signal — this is
   the actual feature the fixed `<data android:mimeType>` entries enable.
4. If install fails again, get the *real* error via `pm install` (not the
   generic on-device dialog) — either `adb install` with the phone
   connected via USB/wireless debugging, or on-device via Termux:
   `cp <apk> /data/local/tmp/app.apk && pm install /data/local/tmp/app.apk`
   (installing straight from `/sdcard` hits an unrelated SELinux/FUSE
   denial — copy to `/data/local/tmp` first).

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
