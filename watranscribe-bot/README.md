# watranscribe-bot (Stage 0 spike)

A standalone proof-of-concept: a WhatsApp bot that receives a voice note
via the WhatsApp Business Cloud API, transcribes it with Deepgram, and
replies with the raw transcript.

This is a companion/spike project to
[WAtranscribe](https://transcribe.flyboybyte.com) (`trans/`), not a
subdirectory or dependency of it. Deepgram logic was vendor-copied and
adapted (API key passed as a plain argument instead of Flask's
`app.config`) — this repo has no shared code, no shared database, and no
network path into the production Flask app. The rationale (why a new repo,
why vendor instead of share, why sandbox-only for now, the security
constraints given this VPS also runs a budget-tracker and a stock-trading
app) is written up in full in the project plan; this README only covers
what's needed to run Stage 0.

Stage 0 scope, deliberately: sandbox/test number only, no rate limiting, no
per-sender abuse controls, no cost ceiling, no summarization (raw
transcript only), no database, no persistence of audio or transcript
beyond the single reply. Those are explicit Stage 1 hardening items, not
oversights — see the plan for the full staged roadmap.

## Setup

1. **Create a Meta for Developers app**: https://developers.facebook.com/apps
   - Add the "WhatsApp" product to the app.
   - Under WhatsApp > API Setup you'll get a **temporary access token**, a
     **test phone number** and its **phone number ID**, and can add up to 5
     recipient numbers for the sandbox (your own phone, e.g.).
   - Under App Settings > Basic you'll find the **App Secret**.

2. **Set environment variables** — copy `.env.example` to `.env` and fill in:
   - `WHATSAPP_VERIFY_TOKEN` — any random string you make up; you'll enter
     the same value into Meta's webhook configuration UI.
   - `WHATSAPP_APP_SECRET` — from App Settings > Basic.
   - `WHATSAPP_ACCESS_TOKEN` — the temporary (or later, permanent) token
     from WhatsApp > API Setup.
   - `WHATSAPP_PHONE_NUMBER_ID` — from the same page.
   - `DEEPGRAM_API_KEY` — from your Deepgram account.

3. **Install and run locally**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   flask --app wsgi.py run
   ```

4. **Expose a public HTTPS URL** so Meta can reach your webhook. For local
   dev, use a tunnel like [ngrok](https://ngrok.com/):
   ```bash
   ngrok http 5000
   ```
   Once deployed for real, this would be a real HTTPS URL on the VPS
   instead (its own systemd unit, own port — never sharing the port,
   secrets, or systemd user with `trans/` or any other project on the box).

5. **Register the webhook with Meta**: in the App Dashboard, WhatsApp >
   Configuration, set the Callback URL to `https://<your-public-url>/webhook`
   and the Verify Token to the same value as `WHATSAPP_VERIFY_TOKEN`. Meta
   will GET the URL to confirm; the app must be running and reachable for
   this to succeed. Subscribe to the `messages` webhook field.

6. **Test it**: from one of the up-to-5 registered recipient numbers, send
   a voice note to the test number in WhatsApp. You should get a text reply
   with the transcript within a few seconds.

## Security notes

- Every webhook POST is validated against `X-Hub-Signature-256`
  (HMAC-SHA256 of the raw body, keyed with `WHATSAPP_APP_SECRET`,
  compared with `hmac.compare_digest`) before any parsing happens — see
  `app/webhook.py`. Anything unsigned or mis-signed gets a 403 and is
  never parsed.
- Zero retention: audio bytes are held in memory just long enough to send
  to Deepgram, then dropped; no disk writes, no database, no logging of
  transcript or audio content anywhere in this codebase.
