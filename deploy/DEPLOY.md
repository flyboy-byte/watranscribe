# Deploying WAtranscribe to the VPS

Target: `transcribe.flyboybyte.com`, one of several projects on the same
box (`flyboybyte.com`, 51.81.80.126). These steps were written after
recon'ing the actual VPS (not assumed) — they match the exact pattern
already used by the other projects there (`budget`, `disc_tracker`, etc.):
**user-level systemd units** (`systemctl --user`, no root/system services,
no dedicated per-app system user — everything runs as `ubuntu`), projects
cloned straight into `/home/ubuntu/<project>/`, and a `deploy.sh` that pushes
to GitHub then pulls+restarts remotely.

Port **5759** is used below (5757 and 5758 are already taken by other apps
on this box; check `ss -tlnp` again before assuming it's still free).

## 1. Clone and set up the app

```bash
ssh ubuntu@flyboybyte.com
git clone https://github.com/flyboy-byte/watranscribe.git ~/watranscribe
cd ~/watranscribe

python3 -m venv .venv
.venv/bin/pip install -e .

cp .env.example .env
# Edit .env: SECRET_KEY, DEEPGRAM_API_KEY, ANTHROPIC_API_KEY, APP_PASSWORD_HASH,
# FLASK_ENV=production
chmod 600 .env
```

Generate the two secrets you need (do this locally, not on the VPS, so the
plaintext password never touches the server's shell history):

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"                              # SECRET_KEY
python3 -c "from werkzeug.security import generate_password_hash as g; print(g('yourpassword'))"  # APP_PASSWORD_HASH
```

## 2. Install the user systemd unit

```bash
mkdir -p ~/.config/systemd/user
cp deploy/transcribe.service ~/.config/systemd/user/transcribe.service
systemctl --user daemon-reload
systemctl --user enable --now transcribe.service
systemctl --user status transcribe.service
curl -i http://127.0.0.1:5759/
```

Lingering is already enabled for `ubuntu` on this box (`loginctl show-user
ubuntu` → `Linger=yes`), so the unit keeps running across reboots/logout —
no extra step needed there.

## 3. nginx + TLS

```bash
sudo cp deploy/nginx_transcribe.conf /etc/nginx/sites-available/transcribe.flyboybyte.com
sudo ln -s /etc/nginx/sites-available/transcribe.flyboybyte.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d transcribe.flyboybyte.com
```

certbot rewrites the block to add the 443 listener + cert paths and
generates the port-80-redirect block, matching every other site on this
box — don't hand-edit those in afterward.

The config reuses this box's existing shared `zone=login` rate-limit bucket
(defined once in `/etc/nginx/nginx.conf`, already used by `budget`'s
`/login`) and the shared `snippets/security-headers.conf` include — no new
global nginx config needed.

## 4. Session-purge cron job (privacy: no data retention)

This app has no database — everything lives only in server-side session
files (`instance/flask_session/`) that expire after
`PERMANENT_SESSION_LIFETIME` (6 hours, see `app/config.py`). Flask-Session's
filesystem backend only checks/deletes expiry lazily, on next access to that
same session — an abandoned session (user never returns) would otherwise
sit on disk indefinitely with someone's audio in it. Add a cron job so
expired files are actually removed promptly, matching the "we don't keep
your data" privacy notice on the page:

```bash
crontab -e
# add:
15 * * * * find /home/ubuntu/watranscribe/instance/flask_session -type f -mmin +360 -delete
```

## 5. Point DNS

`transcribe.flyboybyte.com` has no A record yet — add one pointing at
`51.81.80.126` before running certbot (certbot's HTTP-01 challenge needs it
resolvable first).

## 6. Verify end-to-end

- Visit `https://transcribe.flyboybyte.com` — should redirect to `/login` if
  `APP_PASSWORD_HASH` is set.
- Log in, upload a real audio file, confirm transcription happens
  immediately and a summary is generated only after you pick a
  condensation level — with production API keys.
- `journalctl --user -u transcribe.service -f` while testing.
- `curl -I https://transcribe.flyboybyte.com` — confirm HSTS/X-Frame-Options
  etc. from the shared security-headers snippet are present.

## Updating a running deployment

From your local machine:

```bash
echo "VPS_HOST=ubuntu@flyboybyte.com" >> .env   # once, not committed
./deploy.sh
```

`deploy.sh` pushes to GitHub, then on the VPS: `git pull`, reinstalls deps,
byte-compiles as a syntax check, and restarts `transcribe.service` — same
pattern as this box's other projects' `deploy.sh` scripts.
