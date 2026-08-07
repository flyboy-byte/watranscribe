# Claude Handoff: Privacy-Conscious WhatsApp Voice-Note Transcription Bot

**Project:** WAtranscribe / `transcribe.flyboybyte.com`  
**Owner:** Logan  
**Prepared:** 2026-08-06  
**Purpose of this document:** Give Claude enough context, constraints, architecture, sequencing, stop points, and acceptance criteria to help plan or implement the WhatsApp integration without turning a small utility into an accidental SaaS platform.

---

## 0. Instructions to Claude

Read this entire handoff before proposing code.

Do **not** assume Logan wants immediate implementation. There are two equally valid outcomes:

1. Produce a clean, realistic plan and park the project until Logan has more time.
2. Continue in small, explicitly approved phases.

Your first response after reading this document should contain only:

- A concise restatement of the project and its privacy boundary.
- A list of facts you can verify from the repository/server.
- A list of unknowns that materially affect the design.
- A recommended next phase: **Park**, **Audit**, or **Proof of Concept**.
- A rough time/complexity estimate for that next phase.
- Any single decision Logan must make before you proceed.

Do not begin a rewrite. Inspect and reuse the current application.

Do not expose credentials in chat, command output, screenshots, commits, shell history, logs, test fixtures, or documentation. If a credential appears in existing material, treat it as compromised and tell Logan exactly what needs to be rotated.

Before changing production:

- Inspect the current repository, process manager, reverse proxy, Python/runtime version, transcription engine, summarization path, and deployment layout.
- Create or use a dedicated Git branch.
- Show the proposed file changes.
- State the rollback procedure.
- Obtain explicit approval.
- Preserve the existing website.

Use small commits with one purpose each. Keep `PROJECT_STATE.md`, `DECISIONS.md`, and `RESUME_CHECKLIST.md` current so the project can be paused for months and resumed without reconstructing context.

---

## 1. Executive summary

The existing product is a web-based WhatsApp voice-note transcription tool. The present user flow is inconvenient:

1. A user receives or records a WhatsApp voice note.
2. The user downloads the Opus/OGG file to the device.
3. The user opens `transcribe.flyboybyte.com`.
4. The user uploads the file.
5. The site transcribes it and may offer summarization.

The desired flow is:

1. The user sends or forwards a WhatsApp voice note to a dedicated WhatsApp business contact.
2. Meta sends an incoming-message webhook to Logan's VPS.
3. The VPS retrieves the media using Meta's official WhatsApp Cloud API.
4. The existing self-hosted transcription pipeline transcribes the audio.
5. The bot sends the transcript back in the same WhatsApp conversation.
6. Temporary audio and transcript data are deleted.

The recommended architecture is **direct Meta WhatsApp Cloud API at the transport boundary, with self-hosted processing behind it**.

Do not add Twilio by default. Twilio does not remove Meta's WhatsApp Business Platform requirements; it adds another proprietary processor, another API, another account, and another billing layer. It is justified only if its operational support or multi-channel API later solves a specific problem.

Do not use unofficial WhatsApp Web automation such as Baileys, whatsapp-web.js, or WAHA for the production path. Those tools may be useful for experiments, but they add account-ban risk, protocol-breakage risk, and a maintenance burden that conflicts with the goal of a dependable utility.

Do not confuse this project with **WhatsApp Flows**. Flows are interactive form-like experiences. This bot needs ordinary webhooks, media retrieval, and message sending.

---

## 2. Logan's operating preferences

Design decisions should reflect the following preferences:

- Privacy-conscious, but not absolutist.
- Uses tools such as GrapheneOS, Ente, Brave, Arch Linux, and self-hosted services.
- Prefers FOSS and inspectable infrastructure where practical.
- Accepts that WhatsApp itself is a Meta-controlled boundary because that is where the users and voice notes already are.
- Wants to minimize additional processors rather than pretend Meta is absent.
- Prefers straightforward Linux services and understandable systems over fashionable complexity.
- Is a college student and automotive technician; available time is limited and uneven.
- May prefer excellent planning now and implementation later.
- Does not need a public SaaS, growth stack, analytics platform, Kubernetes cluster, or enterprise support system.
- Values honest privacy language over exaggerated claims.

The design principle is:

> Meta at the unavoidable messaging boundary; self-hosted, minimal, inspectable processing everywhere else.

---

## 3. Known project state

Treat these as current conversational facts, but verify all technical details from the actual repository and server.

- Public site/domain: `https://transcribe.flyboybyte.com`
- Existing web workflow accepts downloaded WhatsApp voice-note files, likely Opus audio in an OGG container.
- Existing transcription functionality already works.
- Existing summarization functionality may exist.
- Claude has previously helped with the project and may have additional repository-specific context.
- A Meta developer account and app have been created.
- A Meta-provided WhatsApp test number has been claimed.
- A test message has been sent successfully from the Meta setup screen.
- Production webhook configuration has not been completed.
- A temporary Meta access token was visible in a screenshot. It must be treated as exposed, even if it has already expired.
- The intended deployment target is Logan's existing server/VPS.
- The production phone number and business-registration path are not yet settled.
- The user-facing bot is expected to behave like an ordinary WhatsApp contact.
- The initial audience can be private and allowlisted.

Unknowns Claude must verify:

- Repository location and remote.
- Current branch and uncommitted changes.
- Server distribution and version.
- Current Python/Node/other runtime.
- Reverse proxy: Caddy, nginx, Apache, Traefik, or other.
- Process manager: systemd, Docker Compose, Podman, supervisor, or other.
- Existing transcription library/model.
- CPU/GPU/RAM limits.
- Current temp-file behavior.
- Current logging behavior.
- Whether audio is uploaded to the VPS or processed in the browser.
- Whether summarization is local or calls an external API.
- Current privacy-policy wording.
- Current dependency licensing.
- Whether the app already has an internal transcription API that can be reused.
- Whether the domain currently routes `/api/*` to an application service.
- Whether the production site has automated backups and whether those backups currently include uploaded audio, logs, or databases.

---

## 4. Product definition

### 4.1 Core user story

> As an allowlisted WhatsApp user, I can send or forward a voice note to the bot and receive a readable transcript without downloading and manually uploading the audio.

### 4.2 Minimum proof of concept

The smallest useful proof of concept must:

- Use Meta's provided test number.
- Receive a real voice note through an official webhook.
- Validate the webhook source.
- Retrieve the media.
- Reuse the existing transcription pipeline.
- Return the transcript through WhatsApp.
- Delete temporary audio.
- Avoid storing transcript contents.
- Avoid logging phone numbers, payloads, media URLs, or transcript text.
- Avoid duplicate replies when Meta retries a webhook.

The proof of concept does **not** need:

- A permanent production phone number.
- Business verification.
- Public registration.
- Payments.
- Templates.
- WhatsApp Flows.
- Twilio.
- Redis.
- Celery.
- PostgreSQL.
- Kubernetes.
- Multiple workers.
- A dashboard.
- Analytics.
- User accounts.
- Subscription billing.
- Automatic summarization.

### 4.3 Private beta

The private beta adds:

- A dedicated production number.
- Durable production credentials.
- Sender allowlist.
- Rate limits.
- Conservative duration/file-size limits.
- Reliable job handling.
- Clear user-facing errors.
- Privacy disclosure.
- Test coverage.
- Deployment hardening.
- Operational cleanup.
- A documented pause/resume procedure.

### 4.4 Explicit non-goals

Unless Logan later changes scope, do not build:

- A general customer-support bot.
- A CRM.
- A message history viewer.
- A searchable transcript archive.
- Cross-user sharing.
- Team workspaces.
- Public onboarding.
- A mobile app.
- Advertising or analytics.
- Long-term content storage.
- Voice identification.
- Speaker identity inference.
- Automated decisions based on message content.
- An external-LLM summary by default.
- Business-initiated marketing messages.
- Message templates beyond what Meta eventually requires for a specific, approved function.

---

## 5. Privacy model

### 5.1 Honest boundary

The service cannot truthfully claim that a WhatsApp voice note remains only on the user's device or browser. The bot requires the audio to pass through WhatsApp/Meta and then through Logan's server.

The defensible privacy claim is narrower:

- Meta is already the transport platform.
- No additional messaging intermediary such as Twilio is used.
- Audio is processed on Logan's server.
- Audio and transcript contents are not retained after delivery.
- Content is not used for training, analytics, advertising, profiling, or resale.
- Operational metadata is minimized and automatically expired.
- External AI services are not used unless the user explicitly requests a feature that requires one and receives a clear disclosure.

### 5.2 Threat model

Protect against:

- Accidental content retention.
- Audio or transcripts entering backups.
- Transcript contents appearing in logs.
- Phone numbers appearing in logs.
- Exposed Meta tokens or app secrets.
- Forged webhook requests.
- Duplicate webhook delivery.
- A malicious user exhausting CPU, RAM, disk, or model capacity.
- Oversized or malformed audio.
- Temporary files surviving failures.
- Worker crashes leaving stale files.
- Dependency or model downloads at runtime.
- Debug mode exposing request data.
- Third-party crash reporting collecting payloads.
- Public health endpoints revealing internal details.
- Shell commands accidentally printing secrets.
- Git commits containing `.env` files.
- Reverse-proxy access logs recording sensitive query strings or headers.
- Future maintainers making privacy claims that the architecture cannot support.

Out of scope, but disclose honestly:

- Meta's own collection and handling of WhatsApp account and messaging metadata.
- The sender's device security.
- A sender forwarding audio they do not have permission to share.
- A fully compromised VPS/root account.
- Legal demands directed at Meta or the VPS provider.
- Content visible in the user's own WhatsApp history after the transcript is delivered.

### 5.3 Data classification

| Data | Sensitivity | Needed? | Retention |
|---|---:|---:|---:|
| Audio content | Very high | Yes, transiently | Delete immediately after processing |
| Transcript content | Very high | Yes, transiently | Keep in memory where practical; delete after send |
| Sender phone number | High PII | Yes, transiently | Avoid logs; retain only as necessary to reply |
| WhatsApp message ID | Moderate/linkable | Yes for idempotency | HMAC or short-lived operational storage |
| Media ID | Moderate/linkable | Yes for retrieval | Delete job record after completion |
| Media download URL | Secret-like, short-lived | Yes transiently | Never persist or log |
| Meta access token | Secret | Yes | Secret store only |
| Meta app secret | Secret | Yes | Secret store only |
| Webhook verify token | Secret-ish | Yes | Secret store only |
| Phone Number ID/WABA ID/App ID | Operational identifiers | Yes | Config; not credentials by themselves |
| Processing duration/model/error code | Low if de-identified | Useful | Short retention |
| Full webhook body | High | No | Never persist |
| Summary prompt/output | Very high | Optional | No retention; external use requires disclosure |

### 5.4 Privacy-preserving operational identifiers

For allowlisting, rate limiting, or short-term diagnostics, use an HMAC rather than a plain hash:

```text
sender_key = HMAC-SHA256(server_secret, normalized_phone_number)
message_key = HMAC-SHA256(server_secret, whatsapp_message_id)
```

A plain hash of a telephone number is weak because the input space is predictable. An HMAC prevents straightforward dictionary recovery without the server secret.

Do not claim this makes the data anonymous. It makes identifiers less directly readable and less reversible if the database alone leaks.

### 5.5 Proposed bot privacy notice

Claude should adapt this after auditing the actual implementation:

> This bot uses WhatsApp, so messages and account metadata are also handled under WhatsApp/Meta's terms. Voice messages are temporarily downloaded to a server controlled by the operator and processed to generate a transcript. Audio and transcript contents are deleted after processing and are not used for advertising, analytics, model training, or resale. Limited operational metadata may be retained briefly to prevent duplicate processing and diagnose failures. Do not submit recordings you are not authorized to share.

If summarization calls an external provider:

> Summarization uses [provider name] and sends the transcript to that provider only after you explicitly request a summary. Do not use summarization for sensitive content unless you accept that additional disclosure.

Do not reuse a browser-only statement such as “audio never leaves your browser” for the WhatsApp bot.

---

## 6. Architecture decision

### 6.1 Recommended path

```text
WhatsApp user
    ↓
WhatsApp / Meta Cloud API
    ↓ HTTPS webhook
Existing reverse proxy on transcribe.flyboybyte.com
    ↓ localhost
Webhook application
    ↓ enqueue
Local worker
    ↓
Meta Media API → temporary private runtime file
    ↓
Existing local transcription engine
    ↓
Response formatter
    ↓
Meta Messages API
    ↓
WhatsApp user
```

### 6.2 Why direct Meta Cloud API

- It is the official transport for a WhatsApp business bot.
- It sends inbound events to a webhook.
- Media messages provide a media identifier that can be retrieved through Meta's Media API.
- Webhook payloads can be validated using the app secret and `X-Hub-Signature-256`.
- It avoids adding Twilio or another provider to the audio path.
- It aligns with the privacy objective of minimizing processors.
- It avoids reverse-engineered WhatsApp Web behavior.

### 6.3 Why not Twilio initially

Twilio may improve onboarding documentation, support, and multi-channel messaging, but it does not make WhatsApp independent of Meta. A production WhatsApp sender still sits on the WhatsApp Business Platform and requires sender registration. Twilio also receives message/media data as another processor and introduces another credential/billing surface.

Reconsider Twilio only if one of these becomes true:

- Meta's direct API remains blocked after a documented attempt.
- Twilio support materially reduces an operational risk Logan actually has.
- The product expands to SMS/MMS and a unified API has clear value.
- Logan wants a supported commercial intermediary more than the privacy/minimalism benefit of direct integration.

### 6.4 Why not unofficial WhatsApp Web libraries

Unofficial libraries can be quick for hobby prototypes but should not be the recommended production route because:

- They automate or reproduce WhatsApp Web behavior.
- They can break when WhatsApp changes the protocol.
- They can cause re-pairing/session failures.
- They may conflict with platform terms or trigger account restrictions.
- They create ongoing maintenance unrelated to the transcription product.
- They risk a personal or dedicated account.

If Logan explicitly chooses this route later, Claude must label it an experimental, higher-risk branch and isolate it from the official Cloud API plan.

---

## 7. Project tracks and realistic effort

These are planning estimates, not promises. Actual effort depends heavily on the current codebase and Meta account state.

### Track A: Park cleanly

Expected effort: roughly 1–3 focused hours.

Deliverables:

- Rotate/revoke exposed credentials.
- Confirm the repository is committed and backed up.
- Write `PROJECT_STATE.md`.
- Write `DECISIONS.md`.
- Write `RESUME_CHECKLIST.md`.
- Record non-secret Meta identifiers.
- Disable or remove any half-configured public webhook.
- Stop any incomplete bot service.
- List the exact next three tasks.
- Open issues for unresolved work.
- Make no production behavior changes.

This is a successful outcome, not abandonment.

### Track B: Audit only

Expected effort: roughly 2–5 focused hours.

Deliverables:

- Current architecture diagram.
- Repository and deployment inventory.
- Data-flow audit.
- Privacy-claim audit.
- Dependency inventory.
- Testability assessment.
- Reuse plan for the existing transcription function.
- Minimal file-change proposal.
- Updated time estimate.
- No production implementation unless separately approved.

### Track C: Meta test-number proof of concept

Expected effort: roughly 4–12 focused hours after the audit, assuming the transcription function is reusable.

Deliverables:

- Webhook verification.
- Webhook signature validation.
- Inbound audio event parsing.
- Media retrieval.
- Temporary-file cleanup.
- Existing transcription integration.
- Transcript reply.
- Duplicate-event protection.
- End-to-end test using the Meta test number.
- No dedicated number or public launch.

### Track D: Private production beta

Expected effort: roughly 8–25 additional focused hours plus unpredictable Meta administrative time.

Deliverables:

- Dedicated number.
- Production credentials.
- Allowlist and rate limits.
- Durable/recoverable queue design.
- Systemd/reverse-proxy hardening.
- Privacy notice.
- Failure handling.
- Operational documentation.
- Test matrix and acceptance checks.
- Rollback plan.

Meta account review, number registration, display-name review, or business verification can take an unpredictable amount of calendar time. Keep that administrative uncertainty separate from coding estimates.

### Track E: Public service

Do not start this by default.

It adds abuse controls, support expectations, policy work, monitoring, capacity planning, cost controls, legal/privacy review, and likely more Meta onboarding. The contact-style interface does not make a service a beta; restricted access and limited guarantees do.

---

## 8. Phase plan with stop gates

### Phase 0: Secure and preserve

Tasks:

- Rotate the access token visible in the screenshot.
- Check the repository history for committed credentials.
- Check shell history, environment files, deployment scripts, screenshots, CI logs, and documentation.
- Add or verify `.gitignore` entries for environment files, local databases, temporary media, model caches if appropriate, and secrets.
- Confirm no production logs contain webhook payloads or transcripts.
- Create a clean Git checkpoint.
- Create the three state documents.
- Decide whether to park or continue.

Stop gate:

> Do not proceed until exposed credentials are invalidated and the current project state can be reconstructed from documentation.

### Phase 1: Audit

Claude should inspect, not guess.

Required report:

```text
Current web stack:
Current reverse proxy:
Current process manager:
Current transcription entry point:
Current summarization entry point:
Current temp-file lifecycle:
Current logging:
Current data retention:
Current test suite:
Current deployment command:
Current rollback method:
Current server resource limits:
Reusable components:
Components that should not be reused:
Privacy claims that are accurate:
Privacy claims that must change for the bot:
```

Stop gate:

> Logan approves the minimal architecture and confirms whether to continue now or park.

### Phase 2: Test-number proof of concept

Use only the Meta test number and development credentials.

Success path:

```text
Voice note
→ verified webhook
→ deduplicated event
→ media retrieval
→ local transcription
→ reply
→ cleanup
```

Keep the POC deliberately limited:

- One server process or one webhook plus one worker.
- One active transcription job at a time.
- Allow only Logan/test recipients.
- Short duration limit.
- No database unless idempotency cannot be handled safely without one.
- No automatic summary.
- No public onboarding.
- No new frontend.

Stop gate:

> A real voice note sent through WhatsApp produces exactly one correct transcript, and no audio/transcript remains on disk or in logs.

### Phase 3: Private-beta hardening

Add only what the test uncovers:

- Reliable queue.
- Restart recovery.
- Allowlist.
- Rate limit.
- Input validation.
- Privacy commands/help text.
- Production secrets.
- Dedicated number.
- Systemd hardening.
- Backup exclusions.
- Cleanup timer.
- Test coverage.
- Documentation.

Stop gate:

> The acceptance checklist in Section 20 passes.

### Phase 4: Optional summarization

Treat summarization as a separate privacy feature.

Before implementation, answer:

- Is the model local?
- If external, which provider receives the transcript?
- Is the user explicitly opting in?
- Is the provider named in the disclosure?
- Is the summary retained?
- Can the transcript exceed provider limits?
- What content is prohibited?
- What is the failure behavior?

Do not automatically summarize every voice note.

### Phase 5: Public release, only by explicit decision

Before public release:

- Re-check current Meta policies and pricing.
- Re-check message/media limits.
- Review privacy notice.
- Add abuse and capacity controls.
- Define support expectations.
- Define account deletion/data request behavior.
- Define who can contact the bot.
- Confirm phone-number/display-name presentation.
- Decide whether the service remains free.
- Confirm server capacity.

---

## 9. Repository and module design

Do not impose this layout if the existing project already has a clean equivalent. Prefer adapting the current architecture.

Suggested logical boundaries:

```text
app/
  config.py
  main.py

  whatsapp/
    client.py          # Graph API requests
    webhook.py         # GET verification and POST receiver
    signatures.py      # X-Hub-Signature-256 validation
    parser.py          # Extract supported inbound messages
    responses.py       # User-facing text and chunking

  transcription/
    service.py         # Adapter around existing transcription engine
    audio.py           # Inspection/conversion/duration
    models.py          # Result types

  jobs/
    queue.py            # POC in-memory or beta SQLite queue
    worker.py
    store.py
    cleanup.py

  privacy/
    identifiers.py      # HMAC sender/message keys
    redaction.py

tests/
  fixtures/
  test_webhook_verification.py
  test_webhook_signature.py
  test_webhook_parser.py
  test_idempotency.py
  test_audio_validation.py
  test_reply_chunking.py
  test_cleanup.py

deploy/
  watranscribe-web.service
  watranscribe-worker.service
  caddy-or-nginx-snippet.conf
  tmpfiles.conf
  cleanup.service
  cleanup.timer

docs/
  PROJECT_STATE.md
  DECISIONS.md
  RESUME_CHECKLIST.md
  PRIVACY_MODEL.md
  RUNBOOK.md
```

Architectural rule:

> The WhatsApp adapter should call the same transcription service used by the website. Do not fork the core transcription logic into a second implementation.

The transcription service should accept a local path or file-like object and return a structured result independent of HTTP or WhatsApp:

```python
@dataclass
class TranscriptResult:
    text: str
    language: str | None
    duration_seconds: float | None
    model_name: str
```

The WhatsApp layer handles Meta-specific concerns. The transcription layer should not know phone numbers, message IDs, webhooks, or access tokens.

---

## 10. Webhook contract

Use an endpoint such as:

```text
GET  /api/whatsapp/webhook
POST /api/whatsapp/webhook
```

Confirm the exact route against the existing reverse proxy.

### 10.1 GET verification

Meta verifies ownership of the callback by sending query parameters such as the mode, challenge, and verification token.

Required behavior:

- Compare the received verification token using constant-time comparison where practical.
- Return the challenge exactly when valid.
- Return a non-success response when invalid.
- Do not log the verification token.
- Do not expose debug details.

Pseudocode:

```python
if mode == "subscribe" and secure_compare(received_token, configured_token):
    return PlainTextResponse(challenge, status_code=200)
return Response(status_code=403)
```

### 10.2 POST event receiver

Correct order:

1. Read the raw request body.
2. Validate `X-Hub-Signature-256` against the app secret.
3. Reject invalid signatures.
4. Parse JSON only after signature validation.
5. Extract supported inbound message events.
6. Ignore delivery/read/status events.
7. Create idempotency key.
8. Enqueue or schedule work.
9. Return HTTP 200 quickly.

Important:

- Signature validation must use the exact raw bytes received, not re-serialized JSON.
- Use `hmac.compare_digest`.
- Do not log the body on parsing or validation failures.
- Meta can retry webhooks. A successful duplicate must not create another transcript response.
- Webhook processing must not wait for full transcription.

Pseudocode:

```python
raw = await request.body()

if not valid_meta_signature(
    app_secret=settings.meta_app_secret,
    raw_body=raw,
    signature_header=request.headers.get("X-Hub-Signature-256"),
):
    return Response(status_code=401)

payload = json.loads(raw)
events = parse_supported_messages(payload)

for event in events:
    enqueue_if_new(event)

return Response(status_code=200)
```

### 10.3 Unsupported events

For:

- Delivery statuses.
- Read statuses.
- Text messages.
- Images.
- Documents.
- Stickers.
- Calls.
- Unknown future event types.

The receiver should not crash.

Recommended handling:

- Status events: ignore after validation.
- Text `help` or `privacy`: respond using explicit command handling.
- Other text: return usage help, subject to rate limiting.
- Unsupported media: one concise message.
- Unknown event schema: record a de-identified error code, not the payload.

---

## 11. Idempotency and duplicate handling

Meta may retry webhooks, and network failures can leave send status uncertain.

Use the inbound WhatsApp message ID as the logical idempotency source.

POC choices:

- In-memory bounded TTL set.
- Accept that a process restart can permit one duplicate.

Private-beta choice:

- Short-lived SQLite job table with a unique message key.
- Insert atomically before processing.
- Delete content-bearing fields after completion.
- Keep a de-identified completion key briefly to suppress retries.
- Expire all rows automatically.

Possible schema:

```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    message_key TEXT NOT NULL UNIQUE,
    sender_key TEXT NOT NULL,
    sender_address TEXT,
    media_id TEXT,
    mime_type TEXT,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    error_code TEXT
);
```

Privacy note:

A durable queue requires enough information to resume and reply after a restart. That may require temporarily storing the sender address and media ID. Protect the database with strict filesystem permissions, keep retention short, exclude it from backups, and clear those fields immediately after completion.

A pure in-memory queue minimizes persistence but loses pending jobs during a restart. That is acceptable for the POC if explicitly documented.

Recommended state transitions:

```text
received
queued
downloading
transcribing
sending
completed
failed_retryable
failed_permanent
expired
```

Do not create an elaborate distributed state machine. One SQLite transaction and one worker are enough for a private beta.

---

## 12. Job execution model

### 12.1 Proof of concept

A FastAPI `BackgroundTasks` task or an internal `asyncio.Queue` can prove the flow, but it is not durable. Heavy model inference should not block the event loop.

Safer POC options:

- Run transcription in a dedicated worker thread/process.
- Keep webhook handling fast.
- Limit concurrency to one.
- Load the transcription model once, not per message.

### 12.2 Private beta

Preferred minimal design:

- Web service receives and validates events.
- SQLite stores short-lived job state.
- Separate systemd worker polls/claims jobs.
- One worker process.
- One active transcription at a time.
- Stale-job recovery on worker startup.
- No Redis/Celery until there is measured need.

SQLite is appropriate here because the expected concurrency is low and it requires no separate database server. If the existing application already has a reliable database or queue, reuse it rather than adding another.

### 12.3 Worker rules

- Claim a job atomically.
- Increment attempt count.
- Set timeouts on every network request.
- Download media immediately.
- Validate type and limits.
- Transcribe locally.
- Send response.
- Delete content.
- Mark completion.
- On any exception, delete temporary content in a `finally` block.
- Retry only failures likely to be transient.
- Do not retry invalid media or policy violations.
- Use bounded exponential backoff.
- Cap attempts.
- Do not send duplicate user-visible error messages.

---

## 13. Media retrieval and audio validation

Expected flow:

1. Receive Meta media ID.
2. Request a download URL through the official Media API.
3. Download with the required bearer authorization.
4. Stream to a private temporary file.
5. Enforce a byte limit while streaming.
6. Inspect MIME/container/codec.
7. Determine duration.
8. Reject unsupported or excessive media.
9. Pass accepted audio to the existing transcription adapter.
10. Delete it in all outcomes.

Do not:

- Trust a filename supplied by the sender.
- Use the sender's filename as a path.
- Download an unbounded body.
- Follow arbitrary redirects outside expected Meta hosts without review.
- Save media under the web root.
- Put media URLs in logs.
- Keep media in a persistent uploads directory.
- rely only on a client-provided MIME type.

Suggested temporary path:

```text
/run/watranscribe/jobs/<random-job-id>/input.ogg
```

Use a random internal job ID. Do not include telephone numbers or message IDs in paths.

On systemd systems, `RuntimeDirectory=watranscribe` is preferable to a hand-created world-visible directory. Confirm that `/run` is memory-backed on the actual server and set mode `0700`.

Input limits should be intentionally lower than the platform maximum during beta. Start with a duration limit based on actual server speed, for example 5–10 minutes, then adjust after measurement. Do not hardcode a platform maximum from an old blog post. Verify current Meta media limits at implementation time.

Use FFmpeg/ffprobe only if already installed or justified:

- `ffprobe` for duration and stream metadata.
- `ffmpeg` for conversion only when the transcription engine cannot consume the native format.
- Use safe subprocess invocation with an argument list, never shell interpolation.
- Set process timeouts.
- Disable unnecessary protocol access where practical.
- Capture errors without logging content paths containing user identifiers.

---

## 14. Transcription integration

First audit the current engine.

Questions:

- Is it OpenAI Whisper, faster-whisper, whisper.cpp, browser-side WASM, or another engine?
- Does the site call a local API or execute transcription in the web request?
- Is the model loaded once?
- Is hardware acceleration available?
- What model size is used?
- What are actual transcription times for 30-second, 2-minute, 5-minute, and 10-minute Opus notes?
- Does the current function write intermediate files?
- Does it retain results?
- Does it perform language detection?
- Does it call an external service?
- Can it be called from a worker without importing the whole web UI?

Requirements:

- Reuse the current transcription logic.
- Separate content processing from presentation.
- Load the model once per worker lifecycle.
- Keep concurrency bounded.
- Make model choice configurable.
- Record only de-identified performance metrics.
- Do not include audio/transcript in exception objects sent to external systems.
- Return a clear failure if the model is unavailable.
- Never silently fall back to a hosted transcription API.

Benchmark before choosing limits.

Suggested benchmark table:

| Clip | Duration | CPU/GPU | Model | Wall time | Peak RAM | Result quality |
|---|---:|---|---|---:|---:|---|
| Clean voice note | 30 s | | | | | |
| Clean voice note | 2 min | | | | | |
| Noisy vehicle/shop | 2 min | | | | | |
| Long voice note | 5 min | | | | | |
| Mixed language | 2 min | | | | | |

Given Logan's automotive context, include at least one noisy shop/vehicle sample. Generic clean-audio benchmarks may overstate real-world performance.

---

## 15. Reply formatting

Keep replies simple.

Suggested transcript:

```text
Transcript:

[transcribed text]
```

Optional footer for beta:

```text
Processed temporarily; audio and transcript were not retained by this bot.
```

Avoid adding the footer to every chunk if it makes long results annoying. A `privacy` command can provide the full disclosure.

### 15.1 Long transcripts

Do not assume a fixed WhatsApp text limit from memory. Verify the current API limit and implement a configurable conservative chunk size.

Chunking rules:

- Prefer paragraph boundaries.
- Then sentence boundaries.
- Fall back to safe character boundaries.
- Preserve order.
- Prefix chunks such as `Transcript 1/3`.
- Cap the total number of chunks.
- If the result is too large, offer a plain-text document only if that fits the privacy model and current API behavior.
- Delete any generated document after sending.
- Do not persist a transcript merely because sending failed.

### 15.2 User messages

`help`:

> Send or forward a WhatsApp voice note. The bot will transcribe it and return the text. This is a private beta and currently accepts limited audio lengths.

`privacy`:

> Voice notes pass through WhatsApp/Meta and are temporarily processed on the operator's server. Audio and transcript contents are deleted after processing and are not used for training, analytics, advertising, or resale. Limited de-identified operational metadata may be retained briefly to prevent duplicates and diagnose failures.

Unknown sender:

> This number is running a private beta and is not currently accepting additional users.

Unsupported media:

> This beta currently accepts WhatsApp voice notes and supported audio files only.

Too long:

> This recording exceeds the current beta limit. Try a shorter recording or split it into parts.

Busy:

> The transcription worker is currently busy. Your message is queued.

Failure:

> The transcription could not be completed. The temporary audio was deleted. Try again later.

Do not reveal stack traces, Meta error bodies, internal IDs, server paths, or model details in user-facing errors.

---

## 16. Allowlist and abuse controls

Private beta access should be explicit.

Store allowlisted numbers as HMAC values if possible:

```text
ALLOWLIST_HMACS=<one or more values>
```

At runtime:

1. Normalize the incoming address.
2. Compute its HMAC.
3. Compare against the allowlist.
4. Do not log the original address.

Initial limits:

- One active job per sender.
- One total active transcription worker.
- Conservative per-sender daily count.
- Conservative audio duration.
- Conservative byte limit.
- Maximum queued jobs.
- Timeout for media download.
- Timeout for transcription.
- Maximum response chunks.

Rate-limit unknown users as well, so repeated contact cannot trigger unlimited replies.

Do not add CAPTCHA, user accounts, or a dashboard to a private WhatsApp contact bot.

---

## 17. Secrets and configuration

Required configuration will likely include:

```text
META_APP_ID
META_APP_SECRET
META_ACCESS_TOKEN
META_WEBHOOK_VERIFY_TOKEN
META_PHONE_NUMBER_ID
META_WABA_ID
META_GRAPH_API_VERSION
IDENTIFIER_HMAC_SECRET
ALLOWED_SENDER_HMACS
MAX_AUDIO_BYTES
MAX_AUDIO_SECONDS
MAX_QUEUE_DEPTH
MAX_REPLY_CHARS
TRANSCRIPTION_MODEL
```

Rules:

- Never commit secrets.
- Never paste secrets into chat.
- Never print environment values during troubleshooting.
- Never put tokens in URLs.
- Avoid command forms that leave tokens in shell history.
- Use a root-readable environment file with mode `0600`, or systemd credentials if the current system supports and already uses them.
- Separate secret values from non-secret config.
- Pin the Graph API version in one configuration location.
- Record a review date for the pinned API version.
- Fail closed if required security configuration is missing.
- Do not start in production with placeholder secrets.
- Use distinct secrets for development and production.

Credential-rotation runbook:

1. Generate/revoke in Meta dashboard using current official instructions.
2. Update the server secret store.
3. Restart only the relevant service.
4. Run a test message.
5. Confirm the old token no longer works where practical.
6. Record rotation date without recording the value.

---

## 18. Deployment design

### 18.1 Reverse proxy

Reuse the existing reverse proxy. Do not replace Caddy with nginx or vice versa just for this feature.

Example Caddy-style concept:

```caddyfile
transcribe.flyboybyte.com {
    # Existing site routes remain unchanged.

    handle /api/whatsapp/webhook {
        reverse_proxy 127.0.0.1:8091
    }
}
```

This is illustrative only. Claude must inspect the actual config and avoid route conflicts.

Requirements:

- Public HTTPS only.
- Application listens on loopback.
- No new public port.
- Preserve raw request body.
- Avoid logging authorization headers.
- Consider suppressing or minimizing access logs for the webhook path.
- Ensure request body limits still permit webhook JSON but do not allow arbitrary large uploads to the webhook endpoint.
- Keep media downloads outbound from the worker; media is not uploaded directly to the public webhook.

### 18.2 systemd services

Possible split:

```text
watranscribe-web.service
watranscribe-worker.service
watranscribe-cleanup.timer
```

Illustrative web unit:

```ini
[Unit]
Description=WAtranscribe WhatsApp webhook
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=watranscribe
Group=watranscribe
WorkingDirectory=/opt/watranscribe
EnvironmentFile=/etc/watranscribe/watranscribe.env
ExecStart=/opt/watranscribe/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8091
Restart=on-failure
RestartSec=5

RuntimeDirectory=watranscribe
RuntimeDirectoryMode=0700
StateDirectory=watranscribe
StateDirectoryMode=0700
UMask=0077

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true
RestrictRealtime=true

ReadWritePaths=/run/watranscribe /var/lib/watranscribe

[Install]
WantedBy=multi-user.target
```

Do not blindly enable every hardening directive. Test model runtimes, FFmpeg, GPU access, and Python native extensions. `MemoryDenyWriteExecute=true`, aggressive syscall filters, private devices, or device restrictions can break machine-learning runtimes or GPU access. Add hardening iteratively and document exceptions.

### 18.3 Cleanup

Cleanup must happen in application `finally` blocks and through defense-in-depth:

- Remove job directory after every job.
- On worker startup, remove stale runtime directories older than the configured threshold.
- Use a timer to remove stale runtime content.
- Clear incomplete queue records after a defined maximum age.
- Exclude runtime and job DB content from backups.
- Verify cleanup with tests, not assumptions.

### 18.4 Backups

Back up:

- Source code.
- Non-secret deployment configuration.
- Documentation.
- Database schema/migrations.
- Model selection/configuration.
- Privacy-policy text.

Do not back up:

- Temporary audio.
- Transcript output.
- Media URLs.
- Webhook payloads.
- Short-lived queue database unless there is a specific recovery requirement.
- Secret files in ordinary backups unless the backup system is encrypted and intentionally designed for secrets.

---

## 19. Logging and observability

Use structured, minimal logs.

Permitted fields:

```text
timestamp
service
event
job_id_random
message_key_prefix (optional, short and de-identified)
status
audio_duration_bucket
audio_size_bucket
processing_ms
model
attempt
error_code
http_status
```

Do not log:

```text
phone number
contact name
full message ID
media ID
media URL
authorization header
app secret
access token
webhook body
audio path containing identifiers
transcript
summary
message text
```

Use error codes such as:

```text
WEBHOOK_BAD_SIGNATURE
WEBHOOK_PARSE_FAILED
EVENT_UNSUPPORTED
SENDER_NOT_ALLOWED
QUEUE_FULL
MEDIA_METADATA_FAILED
MEDIA_DOWNLOAD_TIMEOUT
MEDIA_TOO_LARGE
AUDIO_TOO_LONG
AUDIO_INVALID
TRANSCRIBE_TIMEOUT
TRANSCRIBE_FAILED
SEND_RATE_LIMITED
SEND_AUTH_FAILED
SEND_FAILED
CLEANUP_FAILED
```

Do not add Sentry, hosted log aggregation, analytics, or uptime probes that capture request bodies without a separate privacy decision.

A local health endpoint may report only:

- Process alive.
- Worker alive.
- Queue depth.
- Model loaded.
- Last successful job time.

Keep it bound to localhost or protected by the reverse proxy.

---

## 20. Test plan and acceptance criteria

### 20.1 Unit tests

Webhook verification:

- Correct token returns challenge.
- Incorrect token returns non-success.
- Missing values do not crash.
- Token is not logged.

Signature validation:

- Valid raw body/signature accepted.
- Modified body rejected.
- Missing signature rejected.
- Malformed signature rejected.
- Comparison is constant-time.

Parser:

- Audio message parsed.
- Voice-note metadata parsed if available.
- Status update ignored.
- Text command parsed.
- Unsupported media handled.
- Multiple entries/changes/messages handled without assuming one element.
- Unknown future fields ignored safely.

Idempotency:

- First event accepted.
- Duplicate event not re-enqueued.
- Duplicate after completion not re-sent.
- Stale key expires according to policy.
- Concurrent duplicate inserts result in one job.

Media:

- Streaming byte limit enforced.
- Invalid MIME rejected.
- Invalid container rejected.
- Duration limit enforced.
- Download timeout handled.
- Partial download deleted.
- Redirect behavior tested.

Transcription:

- Existing engine adapter returns structured output.
- Empty result handled.
- Model error mapped to safe code.
- Timeout handled.
- Cleanup occurs after success and failure.

Replies:

- Short transcript sent once.
- Long transcript chunked deterministically.
- Unicode preserved.
- Chunk count capped.
- User-facing errors contain no internals.

Privacy:

- Tests capture logs and assert no phone number, token, media ID, transcript fixture, or payload appears.
- Temporary directory is empty after every outcome.
- Database content-bearing fields are cleared after completion.
- Backup paths exclude runtime data.

### 20.2 Integration tests

Use sanitized recorded fixtures, never raw real-user payloads committed to Git.

Test:

- Webhook → queue.
- Queue → mocked media retrieval.
- Media → real transcription on a small synthetic/local fixture.
- Transcription → mocked send.
- Retry and duplicate flow.
- Service restart with queued job.
- Expired/invalid token.
- Meta send failure.
- Worker crash and recovery.
- Cleanup timer.

### 20.3 End-to-end tests with Meta test number

- Send a 10-second voice note.
- Forward an existing voice note.
- Send a noisy voice note.
- Send a non-English note if multilingual support matters.
- Send unsupported media.
- Send text `help`.
- Send text `privacy`.
- Trigger a duplicate webhook using a test fixture or controlled replay.
- Stop/restart worker during a job.
- Verify only one response.
- Verify runtime directory is empty.
- Search logs for the spoken transcript and sender number.
- Confirm no content is in backups.

### 20.4 Private-beta definition of done

All must be true:

- [ ] Exposed token was rotated/revoked.
- [ ] Repository contains no secrets.
- [ ] Webhook GET verification works.
- [ ] Invalid webhook signatures are rejected.
- [ ] Valid audio event is parsed.
- [ ] Duplicate events do not produce duplicate replies.
- [ ] Media downloads are bounded and timed out.
- [ ] Audio duration is bounded.
- [ ] Existing local transcription engine is reused.
- [ ] One voice note produces one readable transcript.
- [ ] Temporary audio is deleted after success.
- [ ] Temporary audio is deleted after failure.
- [ ] Transcript text is not persisted.
- [ ] Phone numbers and payloads are absent from logs.
- [ ] Sender allowlist works.
- [ ] Rate limiting works.
- [ ] Queue cannot grow without bound.
- [ ] Worker restart behavior is documented.
- [ ] Production secrets are stored outside Git.
- [ ] Service runs as an unprivileged user.
- [ ] Reverse proxy exposes no new public port.
- [ ] Runtime/job paths are excluded from backups.
- [ ] Privacy notice matches actual behavior.
- [ ] Summarization privacy is documented separately.
- [ ] Rollback has been tested.
- [ ] `PROJECT_STATE.md` and `RESUME_CHECKLIST.md` are current.

---

## 21. Failure behavior

Define failures before coding.

### Bad webhook signature

- Return 401 or 403.
- Do not parse/process.
- Log only error code and request timestamp.
- Do not log body/header.

### Meta retries duplicate event

- Return success.
- Do not enqueue or reply again.

### Media URL/retrieval failure

- Retry a limited number of times if transient.
- Do not log URL.
- Send one generic failure only after retries are exhausted.

### Audio too large/long

- Reject before transcription.
- Delete partial/full temp file.
- Send concise limit message.

### Transcription failure

- Delete audio.
- Clear transient transcript buffer.
- Mark safe error code.
- Send one generic failure.
- Do not send stack trace.

### Response send failure

This is a difficult privacy/reliability tradeoff.

- The transcript exists in memory after transcription.
- A transient send retry may require retaining it briefly.
- Prefer short in-memory retry.
- If durable retry requires persistence, explicitly decide whether to:
  - re-transcribe from temporarily retained audio,
  - temporarily encrypt/store transcript,
  - or fail and delete content.

For the privacy-first beta, recommended default:

- Attempt bounded immediate retries.
- If still unsuccessful, delete transcript and audio.
- Record a de-identified failure.
- Ask the user to resend later, if a failure message can be delivered.
- Do not persist transcript content solely to guarantee delivery.

### Worker crash

- Runtime cleanup on restart.
- Pending durable jobs return to queue if the beta uses SQLite.
- POC in-memory jobs may be lost; document this.
- Stale jobs must not loop forever.

### Token expiration/revocation

- Mark authentication failure.
- Stop retry storm.
- Alert Logan through local logs/manual monitoring.
- Do not expose token in diagnostic output.

---

## 22. Meta setup checklist

Use current official Meta documentation and the current dashboard. Do not follow stale screenshots blindly.

Development:

- [ ] Confirm app type/use case is appropriate for WhatsApp.
- [ ] Confirm WhatsApp product/use case is added.
- [ ] Record non-secret App ID.
- [ ] Record Phone Number ID.
- [ ] Record WABA ID.
- [ ] Rotate temporary token exposed in screenshot.
- [ ] Create a strong random webhook verify token.
- [ ] Store app secret safely.
- [ ] Set callback URL.
- [ ] Complete callback verification.
- [ ] Subscribe to the required WhatsApp message webhook field(s).
- [ ] Add/confirm development recipient as required by the dashboard.
- [ ] Send a test message.
- [ ] Receive a test webhook.
- [ ] Receive a real audio webhook.
- [ ] Retrieve media.
- [ ] Send transcript reply.

Before production:

- [ ] Obtain a dedicated number Logan controls.
- [ ] Confirm SMS or voice OTP availability.
- [ ] Decide whether the number must coexist with WhatsApp Business App; do not assume.
- [ ] Review current Meta number-registration requirements.
- [ ] Review current business-verification requirements for Logan's intended usage.
- [ ] Review display-name requirements.
- [ ] Create durable production authentication using Meta's current recommended method.
- [ ] Pin Graph API version.
- [ ] Configure payment only if the actual production use requires it.
- [ ] Confirm user-initiated reply behavior and any current conversation-window/template rules.
- [ ] Confirm current pricing.
- [ ] Confirm current media and message limits.
- [ ] Confirm app mode/publishing requirements for non-admin/test users.
- [ ] Perform end-to-end test from an allowlisted non-admin account.
- [ ] Document account ownership and recovery.

Do not let account administration block coding against the test number. Conversely, do not promise production availability until the dedicated number and account state are proven.

---

## 23. Security review checklist

Application:

- [ ] Raw-body signature validation.
- [ ] Constant-time comparisons.
- [ ] Strict timeouts.
- [ ] Bounded downloads.
- [ ] MIME/container validation.
- [ ] Safe subprocess invocation.
- [ ] No shell interpolation.
- [ ] No path traversal.
- [ ] Random job IDs.
- [ ] No debug mode.
- [ ] No verbose exception responses.
- [ ] Dependency versions pinned appropriately.
- [ ] Dependency vulnerabilities reviewed.
- [ ] Model downloads occur during controlled deployment, not on first user request.
- [ ] No external fallback.
- [ ] Queue bounded.
- [ ] Concurrency bounded.
- [ ] Rate limits.
- [ ] Idempotency.
- [ ] Cleanup in `finally`.

Host:

- [ ] Dedicated unprivileged user.
- [ ] Loopback application listener.
- [ ] Firewall exposes only intended ports.
- [ ] TLS valid.
- [ ] Root-owned secrets.
- [ ] Runtime directory mode `0700`.
- [ ] State directory mode `0700`.
- [ ] Service hardening tested.
- [ ] OS security updates planned.
- [ ] SSH access reviewed.
- [ ] Backups reviewed.
- [ ] Swap behavior considered if transcripts/audio can enter memory pages.
- [ ] Core dumps disabled or restricted for the service.
- [ ] Journal retention appropriate.
- [ ] Reverse-proxy logs reviewed.
- [ ] Disk-space limits/monitoring.

Privacy-hardening note:

Even with deletion, sensitive content may transiently exist in RAM, swap, filesystem buffers, journal output if misconfigured, or provider infrastructure. Do not make forensic-erasure promises. State operational deletion behavior accurately.

---

## 24. Decision log starter

Create `DECISIONS.md` using entries like:

```markdown
## D-001: Use direct Meta Cloud API

Date: 2026-08-06
Status: Accepted

Decision:
Use Meta's official WhatsApp Cloud API directly. Do not add Twilio initially.

Reasons:
- Meta is unavoidable for WhatsApp transport.
- Direct integration minimizes additional processors.
- Existing test number is already active.
- Twilio does not remove sender/business onboarding.
- Small private beta does not need multi-channel abstraction.

Consequences:
- Logan must handle Meta webhook, credentials, and number setup.
- Meta policy/API changes remain an operational dependency.
```

Suggested decisions:

- D-001 Direct Meta Cloud API.
- D-002 No unofficial WhatsApp Web automation for production.
- D-003 Reuse existing transcription engine.
- D-004 No content retention.
- D-005 No automatic external summarization.
- D-006 Private allowlisted beta first.
- D-007 SQLite only if durable queue is needed.
- D-008 One worker/concurrency one initially.
- D-009 No analytics or hosted error tracking.
- D-010 Project may be parked after planning without implementation.

---

## 25. Project-state document starter

Create `PROJECT_STATE.md`:

```markdown
# WAtranscribe Project State

Last updated:
Updated by:

## Current status
[Parked / Audit / POC / Private beta / Production]

## What works
- Existing website:
- Transcription:
- Summarization:
- Meta test number:
- Webhook verification:
- Incoming audio:
- Media download:
- Reply sending:

## Deployment
- Server:
- OS:
- Repo:
- Branch:
- Reverse proxy:
- Process manager:
- App service:
- Worker service:
- Runtime directory:
- State directory:

## Meta identifiers (NO SECRETS)
- App ID:
- WABA ID:
- Phone Number ID:
- Graph API version:
- Callback URL:

## Secrets
Stored at:
Rotation date:
Never include values here.

## Known issues

## Privacy status

## Next three tasks
1.
2.
3.

## Exact resume command/process

## Rollback
```

---

## 26. Parking protocol

If Logan decides to wait until returning to college, do this rather than leaving the project half-configured.

### 26.1 Secure

- Rotate/revoke exposed development token.
- Remove secrets from screenshots and shared notes where possible.
- Check Git history.
- Disable unfinished public webhook routes.
- Stop incomplete services.
- Remove temporary media and test databases.
- Confirm no lingering process is polling or retrying.
- Disable external monitoring that may capture content.

### 26.2 Preserve

- Commit all non-secret work.
- Tag the checkpoint, for example `whatsapp-plan-2026-08-06`.
- Export dependency lockfiles.
- Record runtime versions.
- Record model name/version and download source.
- Save non-secret Meta IDs.
- Save screenshots of dashboard state only after redacting tokens.
- Write exact dashboard navigation notes because Meta changes its UI.
- Record DNS and reverse-proxy state.
- Record whether the callback URL is active.

### 26.3 Make resumption cheap

Create `RESUME_CHECKLIST.md`:

```markdown
# Resume WhatsApp Bot

1. Read PROJECT_STATE.md and DECISIONS.md.
2. Confirm no credentials in screenshots/chat/Git.
3. Check current Meta Cloud API documentation and pinned API version.
4. Confirm Meta app and test number still exist.
5. Generate fresh development credential.
6. Start local/webhook service.
7. Run unit tests.
8. Send one test voice note.
9. Verify cleanup and logs.
10. Continue only from the next incomplete phase.
```

### 26.4 Do not preserve

- Access tokens.
- App secrets in ordinary notes.
- Real webhook payloads.
- Real audio.
- Real transcripts.
- Media URLs.
- Phone numbers in fixtures.
- Half-completed migration scripts without documentation.

A well-parked project should take under an hour to understand when resumed.

---

## 27. Suggested Claude workflow

### Step 1: Audit response

Claude should return:

```text
Verified facts
Unknowns
Risks
Recommended phase
Estimated effort
Files to inspect
No changes made
```

### Step 2: Plan response

After inspecting the repository:

```text
Minimal change set
Files to add
Files to modify
Dependencies
Configuration changes
Meta dashboard actions
Tests
Deployment
Rollback
Privacy impact
Estimate
```

### Step 3: Implementation, only after approval

For each batch:

- State the goal.
- Show the affected files.
- Make one coherent change.
- Add tests.
- Run tests.
- Report exact result.
- Update docs.
- Commit with a meaningful message.
- Stop at the phase gate.

### Step 4: Never hide uncertainty

When Meta dashboard behavior differs from documentation:

- State the exact discrepancy.
- Prefer current official docs and observed account behavior.
- Do not guess.
- Do not create a Twilio detour without showing why it solves the discrepancy.
- Capture a redacted screenshot or textual state for the runbook.

---

## 28. Questions Claude must answer before coding

1. Where is the current transcription function, and can it be called independently of the browser/upload route?
2. Does transcription happen locally on the VPS, in the browser, or through an external API?
3. Does summarization call an external provider?
4. What files are currently written during upload/transcription?
5. What gets logged?
6. What gets backed up?
7. How long does transcription take on this VPS?
8. What is the safest concurrency?
9. What reverse proxy already serves the domain?
10. Is the application already FastAPI/Flask/Node/etc.?
11. Is there an existing API route suitable for internal reuse?
12. Does the website need to remain available during deployment?
13. Is there already a service account/user?
14. Is `/run` available and memory-backed?
15. Is swap enabled?
16. Are core dumps enabled?
17. What is the current Meta Graph API version selected by the app?
18. Does the test-number webhook deliver actual audio messages to this app?
19. What exact production requirement is Meta currently blocking on?
20. Can the private beta use only Logan initially?
21. Does Logan want transcription only, or transcription plus an explicit summary command?
22. What duration limit feels useful given measured server performance?
23. Does Logan want the bot to respond to unknown users or silently ignore them?
24. Is a dedicated number already available?
25. Does Logan want to continue now, or only leave a clean plan?

---

## 29. Recommended immediate next action

Given Logan's concern that the project is more involved than expected, the best immediate action is **not** to build the production integration.

Recommended next step:

1. Spend one short session on Phase 0: rotate the exposed token and create the state/decision/resume documents.
2. Have Claude perform a read-only audit of the current repository and deployment.
3. Have Claude estimate the POC based on the actual code.
4. Decide whether the POC is worth one or two focused weekends.
5. Park the production-number and business-verification work until the POC proves the user experience.

This prevents Meta administration from consuming time before the technical value is proven.

The POC should answer one question:

> Does forwarding a voice note to a WhatsApp contact and getting a transcript back feel useful enough to justify the production setup?

If yes, continue. If not, the existing upload website remains functional and the project has not been overbuilt.

---

## 30. Master prompt Logan can paste to Claude

```text
You are taking over planning and possible implementation of my WAtranscribe WhatsApp integration.

Read CLAUDE_HANDOFF.md, PROJECT_STATE.md, DECISIONS.md, and RESUME_CHECKLIST.md before doing anything. The current site is transcribe.flyboybyte.com. It already transcribes downloaded WhatsApp Opus/OGG voice notes through a manual upload workflow. I created a Meta developer app, claimed a WhatsApp test number, and sent a test message. A development access token appeared in a screenshot, so treat it as exposed.

My priority is a privacy-conscious, FOSS-leaning design: Meta is accepted only as the unavoidable WhatsApp transport boundary. Do not add Twilio, Zapier, hosted analytics, hosted transcription, or unofficial WhatsApp Web automation unless you show a concrete reason and I approve it. Reuse the existing transcription engine and deployment. Do not rewrite the site.

I may choose to park this project until I am back in college. Planning and preservation are valid deliverables. Do not start implementation merely because you can.

First, perform a read-only audit. Do not change production, install packages, rotate credentials, edit Meta settings, or create services without approval. Inspect the repo and deployment and report:

1. Verified current architecture.
2. Where transcription and summarization occur.
3. Current data lifecycle, logs, temp files, and backups.
4. What can be reused for a WhatsApp adapter.
5. The smallest test-number POC.
6. Exact files that would change.
7. Privacy/security risks.
8. A realistic effort estimate.
9. A clean parking plan.
10. One recommended next decision.

Keep secrets out of chat and command output. If you discover credentials, stop and identify what must be rotated without printing them. Use small phases, tests, rollback instructions, and updated documentation. Do not overbuild.
```

---

## 31. Official references to re-check during implementation

Meta changes dashboard paths, API versions, requirements, limits, and pricing. Treat these as starting points and re-check them at implementation time.

- WhatsApp Business Platform overview:  
  https://developers.facebook.com/documentation/business-messaging/whatsapp/overview

- About the platform:  
  https://developers.facebook.com/documentation/business-messaging/whatsapp/about-the-platform

- Get started:  
  https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started

- Webhooks overview:  
  https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview

- Create a webhook endpoint and validate signatures:  
  https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/create-webhook-endpoint/

- Media API:  
  https://developers.facebook.com/documentation/business-messaging/whatsapp/reference/media/media-api

- Media download API:  
  https://developers.facebook.com/documentation/business-messaging/whatsapp/reference/media/media-download-api

- Business phone numbers:  
  https://developers.facebook.com/documentation/business-messaging/whatsapp/business-phone-numbers/phone-numbers

- Sending service messages:  
  https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/send-messages

- Twilio WhatsApp self-sign-up, for comparison only:  
  https://www.twilio.com/docs/whatsapp/self-sign-up

- Twilio WhatsApp Business Account requirements, for comparison only:  
  https://www.twilio.com/docs/whatsapp/tutorial/whatsapp-business-account

- FastAPI background tasks:  
  https://fastapi.tiangolo.com/tutorial/background-tasks/

- FastAPI lifespan/model initialization:  
  https://fastapi.tiangolo.com/advanced/events/

- Python SQLite documentation:  
  https://docs.python.org/3/library/sqlite3.html

- Caddy automatic HTTPS:  
  https://caddyserver.com/docs/automatic-https

The official Meta documentation is the source of truth for Meta behavior. Twilio documentation is useful only to evaluate Twilio's layer and requirements. Avoid copying implementation details from random tutorials without checking them against official docs.

---

## 32. Final recommendation

Do not make the first milestone “production WhatsApp bot.”

Make the first milestone:

> One real voice note sent to Meta's test number returns one transcript from the existing local engine, with validated webhooks, no duplicate reply, and verified deletion.

Then choose deliberately:

- Park it.
- Keep it as a personal/private bot.
- Complete a dedicated-number private beta.
- Expand publicly.

The project is not technically exotic. The time cost comes from integration edges, Meta account administration, failure handling, and truthful privacy engineering. The way to keep it manageable is to isolate those concerns, prove the smallest end-to-end path, and stop at explicit gates.
