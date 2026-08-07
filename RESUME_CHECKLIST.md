# Resume WhatsApp Bot

Read `PROJECT_STATE.md` and `DECISIONS.md` first — don't re-derive the architecture, it's
already settled. This project was deliberately parked on 2026-08-06, not abandoned.

1. Read `PROJECT_STATE.md` and `DECISIONS.md` in full.
2. Confirm no credentials leaked while parked: check this repo's git log (`git log --stat`,
   should show only the parking checkpoint commit and scaffold — no `.env`), and check that
   `.env` still exists and is still gitignored (`git check-ignore -v .env`).
3. **Rotate the Meta access token** if that wasn't already confirmed done before parking (see
   `PROJECT_STATE.md`'s Secrets section — a token was pasted in plaintext chat once and must be
   treated as compromised regardless of elapsed time). Generate a fresh one in Meta's App
   Dashboard → WhatsApp → API Setup, put it directly in `.env` yourself (never paste it in chat).
4. Check current Meta WhatsApp Cloud API documentation and pin a Graph API version in
   `app/config.py` (not pinned yet — do not assume the version from whenever this was parked is
   still current).
5. Confirm the Meta app and test number still exist and haven't been reset/expired.
6. Finish "Register your WhatsApp phone number" (Meta dashboard Step 2) using the existing test
   number — this does not require a real/purchased business number.
7. Run the existing test suite (`pytest`) to confirm the scaffold still passes against current
   dependency versions.
8. Deploy to the VPS per `PLAN.md`: new systemd `--user` unit, new port (check `ss -tlnp` for
   what's free — 5759 is taken by `trans/`), `bot.flyboybyte.com` subdomain with its own nginx
   server block and certbot cert (see `DECISIONS.md` D-011). Do not touch
   `transcribe.flyboybyte.com`'s existing config.
9. Register the resulting webhook URL + verify token with Meta, subscribe to the `messages`
   field.
10. Send one real voice note from a registered test phone number, confirm exactly one transcript
    comes back, and confirm nothing persists on disk/in logs afterward (per the Stage 0
    verification checkpoint in `PLAN.md`).
11. Only then: decide whether to continue toward a private beta, or park again.
