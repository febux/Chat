# Known Issues — FastAPIChat

Issues identified during code review. The items below were resolved in this pass;
they are retained as a record of what was fixed and where.

Severity legend: [HIGH] security/correctness, [MED] quality/maintainability,
[LOW] hygiene/cosmetic.

---

## [MED] #13 — Dynamic repository loading is fragile — RESOLVED

`src/backend/database/sqlalchemy/orm_manager/meta.py` uses `__getattr__` to
lazily load repositories by attribute name, so a typo or a missing repository
only failed at request time.

**Fix:** Added `OrmRepositoryManager.validate_repos()` in
`src/backend/database/sqlalchemy/orm_manager/manager.py`, which eagerly imports
and registers every repository module and raises `RuntimeError` at startup if
any fail to resolve. It is invoked from `src/backend/app/lifespan.py` during the
startup phase, so misconfiguration aborts the boot instead of surfacing as an
intermittent request-time `AttributeError`.

---

## [MED] #14 — Inconsistent return types in UserService — RESOLVED

`authenticate_user()` returned a clean `User` schema, but `get_by_id()` and
`get_by_email()` returned raw ORM models carrying `password_hash`.

**Fix:** `src/backend/app/services/user/service_v1.py` now funnels every
public method (`get_all`, `get_current_user_contacts`, `get_by_id`,
`get_by_email`, `authenticate_user`, `create`) through a single
`_to_user_schema()` boundary that maps the ORM model onto the public `User`
schema. No service method consumed by a route returns a raw ORM model, so
`password_hash` can no longer leak even on code paths that bypass
`response_model`. (`authenticate_user` reads `password_hash` from the repo for
verification but returns only the schema.)

---

## [MED] #15 — Email used as a URL path parameter — RESOLVED

`POST /contact/{user_email}` put an email directly in the URL path: no
`EmailStr` validation, `@` required URL-encoding, and it was logged in
plaintext.

**Fix:** The endpoint is now `POST /contact` accepting a JSON body via the new
`ContactRequest` schema (`src/backend/schemas/users/user_contact.py`), whose
`email` field is validated as `EmailStr`. Updated
`src/backend/app/api/public/v1/users/routes.py` and the route tests in
`src/backend/tests/api/test_user_routes.py` (added a `422`-on-invalid-email
case). Frontend callers must send `{"email": "..."}` instead of a path segment.

---

## [LOW] #19 — Duplicate / redundant crypto dependencies — RESOLVED

`pyproject.toml` pulled in overlapping crypto libraries.

**Fix (audit-driven):**
- `bcrypt==4.2.0` — **removed.** Zero imports anywhere; `utils/password.py`
  hashes with `passlib.hash.argon2` (backed by `argon2-cffi`, which is kept).
- `pyjwt>=2.8.0` — **removed.** The codebase standardizes on `python-jose` for
  all JWT encode/decode. PyJWT was used only for `from jwt import
  InvalidTokenError` in the two WebSocket managers; replaced with jose's
  `JWTError` (already imported there). See `nats_socketio_manager.py` and
  `redis_socketio_manager.py`.
- `python-jose`, `cryptography` (used directly by `utils/crypto.py` for AESGCM),
  `passlib`, and `argon2-cffi` (passlib's argon2 backend) — all **kept**, each
  has a verified direct/transitive import.

---

# Open issues — identified in a second review pass (performance & missing features)

Severity legend: [CRIT] security/correctness/data-integrity, [HI] performance or
logic bug with real user impact, [MED] quality/maintainability, [LOW] hygiene.
Items below need a decision or a code change. The three [CRIT] items (#20–#22),
the four [HI] items (#23–#26), the seven [MED] items (#27–#33), and the [LOW]
items (#34) have all been resolved in follow-up passes.

## [CRIT] #20 — No channel-membership authorization on message endpoints — RESOLVED

**Resolved:** Added `MessageService.is_channel_member()` (in `service_v1.py` and
the `MessageServiceMeta` protocol), backed by
`channel_member_repo.read_one(channel_id, user_id)`. Both `get_channel_messages`
and `send_message` now raise `403` when the caller is not a member of the channel
(`message/routes.py`). The placeholder Russian "опционально" comment is gone.

`src/backend/app/api/public/v1/message/routes.py:23,54` — `get_channel_messages`
and `send_message` authenticate the caller via JWT but never verify the caller is
a member of `channel_id` (the code comment literally says "опционально: проверить,
что current_user состоит в канале"). Any authenticated user can read every
channel's history and inject messages into any channel.
Fix: membership check via `channel_member_repo.read_one(channel_id=…, user_id=current_user.id)`, raise 403 if absent.

## [CRIT] #21 — `create_channel` trusts client-supplied `created_by` — RESOLVED

**Resolved:** Removed `created_by` from the `ChannelWithMembersCreate` request
schema (`schemas/channels/channel_create.py`); `create_channel` now sets it from
`current_user.id`, so a client can no longer forge it. (The DB column and the GET
response schema still expose `created_by` — that is correct and unchanged.)

`src/backend/app/api/public/v1/channel/routes.py:58-71` — `ChannelWithMembersCreate`
includes `created_by`, and the route passes `**channel_data.model_dump()` through
unchanged. `current_user` is fetched and ignored, so a client can forge any
`created_by` UUID.
Fix: drop `created_by` from the request schema; set it from `current_user.id`.

## [CRIT] #22 — `POST /channels/users` (DM get-or-create) is broken — RESOLVED

**Resolved:** The route now builds `member_ids = [current_user.id, *user_ids]`
(deduped, order-preserving) and uses it for both `find_channel_between_users` and
`create_channel_with_members`, so the caller is always a member of their own DM
and the lookup cannot return a channel the caller isn't in. The title is built
from the member set, removing the `user_ids[1]` IndexError on a single id. Also
fixed a latent `AttributeError`: `create_channel_with_members` already returns a
dict, so the create branch no longer calls `.to_dict()` on it.

`src/backend/app/api/public/v1/channel/routes.py:37-54`:
- `user_ids: list[UUID] = Body(min_length=1)` but the title builder indexes
  `user_ids[1]` → IndexError when one id is sent.
- `members=user_ids` omits `current_user.id`, so the creator is not a member of
  their own DM channel.
- `find_channel_between_users(user_ids)` does not include the caller, so it can
  return a channel the caller does not belong to.

## [HI] #23 — First-page message pagination is a performance disaster — RESOLVED

**Resolved:** Rewrote both `get_messages_between_users` and
`get_messages_for_channel` to pure cursor pagination: `ORDER BY created_at DESC,
id DESC LIMIT :n` then `reverse()` in Python. First page is now a single indexed
range query (no COUNT, no OFFSET); cursor pages are the PK lookup + one range
query. A stale/unknown cursor now returns `[]` instead of silently serving page 1.

`src/backend/app/repository/message/repository.py:126-191` (and `:20-97`). On the
first page (`before_id=None`) the code runs (1) a `COUNT(*)` over the whole
channel, (2) a `.offset(total_count - limit)` query to find a "boundary" row —
high OFFSET is O(N) in Postgres — then (3) the actual fetch: 3 round-trips + an
offset scan to load the latest 30 messages. Degrades linearly with channel size.
Every subsequent page also does an extra `read_one(id=before_id)` SELECT just to
get the timestamp.
Fix: `before_id is None` → `WHERE channel_id=:c ORDER BY created_at DESC, id DESC
LIMIT :n` then reverse in Python (one indexed query, no COUNT, no offset). The
composite index `ix_messages_channel_created_at_desc` already supports a backward
scan. Send `(created_at,id)` — or at least rely on the index — instead of an
extra lookup per page.

## [HI] #24 — `find_channel_between_users` over-matches — RESOLVED

**Resolved:** The query now restricts to candidate channels (those containing at
least one requested user via `user_id IN (...)`), then joins back to count the
candidate channel's *total* membership and requires `count == num_users`. This
guarantees an exact member-set match: {A,B,C} no longer matches a search for {A,B}.

`src/backend/app/repository/channel/repository.py:37-51` — `HAVING count(user_id)
== num_users` only counts members that are IN `user_ids`. A channel with members
{A,B,C} matches a search for {A,B} (2 of 3 match → count==2). Creating a DM
between A and B can thus return an unrelated group channel.
Fix: also assert the channel's total member count equals `num_users`.

## [HI] #25 — Centrifugo HTTP client is created per message; publish blocks the response — RESOLVED

**Resolved:** Added a process-wide lazy singleton client
(`get_centrifugo_http_client()`), reused across all publishes, and closed on
shutdown via `close_centrifugo_http_client()` wired into the app lifespan.
`publish_to_channel` now catches `httpx.HTTPError` and logs it instead of raising,
so a transient Centrifugo outage no longer turns a persisted message into a 500
(best-effort realtime delivery).

`src/backend/app/services/centrifugo/service_v1.py:60-73` — every
`publish_to_channel` opens a new `httpx.AsyncClient` (new conn + TLS/HTTP2
handshake), posts, closes. This is the message-send hot path. Plus
`res.raise_for_status()` means a transient Centrifugo outage turns every send
into a 500 even though the row is already persisted.
Fix: one long-lived client (built in `__init__`/lifespan, closed on shutdown);
publish via `BackgroundTasks` (fire-and-forget) or at minimum log-not-raise so
realtime delivery is decoupled from persistence.

## [HI] #26 — N+1 member inserts + extra SELECT per insert — RESOLVED

**Resolved:** Added a generic `bulk_create(items)` to `AbstractRepository`
(`session.add_all([...])` + single `flush()`, no per-row `refresh`).
`create_channel_with_members` now builds all member dicts and issues one
`bulk_create`, turning ~2N+ round-trips into one.

`src/backend/app/services/channel/service_v1.py:91-103` loops `await
channel_member_repo.create(...)` per member; `AbstractRepository.create`
(`meta.py:267-279`) does `flush([entity]) + refresh(entity)` = 2 round-trips each.
For N members: ~2N+ round-trips.
Fix: `session.add_all([...])` + a single `flush()`; skip the per-row `refresh`.

## [MED] #27 — Rate limiting configured but applied nowhere — RESOLVED

**Resolved:** Wired `@default_limiter.limit(...)` onto the hot endpoints:
`5/minute` on `/login` and `/register` (`app/api/public/v1/base/routes.py`),
`30/minute` on `send_message` (`app/api/public/v1/message/routes.py`). The
`register_user` signature gained the `request: Request` param slowapi requires.
Fixed a latent breakage in `middleware/rate_limit_middleware.py`: the module-level
`default_limiter` always used Redis storage, so the decorators hit Redis at
request time and broke all auth route tests in TESTING_MODE — it now selects
`memory://` storage when `settings.app.TESTING_MODE` is set (prod still uses Redis
for shared cross-worker counters).

`slowapi` + `fastapi-guard` are deps and `RATE_LIMIT_DURATION`/`RATE_LIMIT_REQUESTS`
exist in config, but `grep` over `app/api` finds zero usage. Message sending and
auth endpoints are unprotected against brute-force/spam.

## [MED] #28 — Soft-delete half-implemented — RESOLVED

**Resolved:** All three message-read queries (`get_messages_between_users`,
`get_messages_for_channel`) now AND `deleted_at IS NULL` onto their WHERE clause
(`repository/message/repository.py`), so soft-deleted rows never surface in
history. New `MessageRepository.soft_delete(id)` does an idempotent
`UPDATE ... WHERE deleted_at IS NULL`. `MessageService.delete_message()`
(`service_v1.py`) loads the row, checks `sender_id == user_id`, and soft-deletes
inside a transaction, returning False for not-found / already-deleted / not-owner
so the new `DELETE /messages/{id}` route can uniformly 403 (no id-enumeration
leak). The `deleted_at` column already existed in the model and the initial
migration, so no schema change was needed.

`src/backend/app/models/message.py:30` declares `deleted_at`, but no query filters
`deleted_at IS NULL` and there is no delete endpoint. "Deleted" messages are still
returned by `get_messages_for_channel`.

## [MED] #29 — DB config defaults point at RabbitMQ's port — RESOLVED

**Resolved:** `src/backend/config/env_config/db.py` — `PORT` and `EXTERNAL_PORT`
now default to `5432` (PostgreSQL) with matching `examples`/`description`; the
class docstring was corrected too.

`src/backend/config/env_config/db.py:65-76` — `PORT` defaults to `5672` and
`EXTERNAL_PORT` to `15672` (RabbitMQ), not PostgreSQL's 5432. A deploy that omits
`DATABASE_PORT` targets the wrong service or fails confusingly.

## [MED] #30 — `last_seen` Redis keys never expire — RESOLVED

**Resolved:** `set_user_ping` now writes `user:last_seen:<id>` with
`ex=LAST_SEEN_TTL_SECONDS` (30 days), matching the existing `user:status:<id>`
90s TTL on the same pipeline. `last_seen` survives long enough to power "was
online recently" but no longer grows Redis without bound.

`src/backend/app/services/user/service_v1.py:159` — `set_user_ping` sets
`user:last_seen:<id>` with no TTL (while `user:status:<id>` correctly gets 90s).
Every user who ever pinged accumulates a permanent key → unbounded Redis growth.

## [MED] #31 — `UserRepository.get_all` default returns the whole table — RESOLVED

**Resolved:** `limit` now defaults to `100` and the cap is always applied
(`query.limit(limit)` runs unconditionally). The `if limit > 0` guard that let
an omitted arg select the whole table is removed.

`src/backend/app/repository/user/repository.py:25` — `limit: int = 0` with
`if limit > 0: apply` means omitting `limit` selects every user row. The service
always passes a limit today, but this is a latent DoS footgun.

## [MED] #32 — `AbstractRepository.execute()` runs EXPLAIN by default — RESOLVED

**Resolved:** `query_plan` now defaults to `None`; the EXPLAIN branch (and the
`module_name` derivation it needs) is only entered when a caller explicitly
passes `query_plan`. A plain `self.execute(query)` is now a single round-trip.
The `case _: pass` fallthrough is gone since the `if query_plan is not None`
guard makes it unreachable.

`src/backend/app/repository/meta.py:69-102` — `query_plan` defaults to `"explain"`,
so any call to `self.execute()` fires a second `EXPLAIN <query>` round-trip per
query. Currently unused (repos call `self.session.execute` directly) but a
landmine. Flip the default to `None` or remove the method.

## [MED] #33 — CORS `*` on the Socket.IO server with cookie auth — RESOLVED

**Resolved:** Both `nats_socketio_manager.py` and `redis_socketio_manager.py`
now pass `cors_allowed_origins=settings.app.CORS_ORIGINS` instead of the literal
`["*"]`, so the allowed origins are the same set the HTTP CORS middleware uses.

`src/backend/core/websocket/nats_socketio_manager.py:44` —
`cors_allowed_origins=["*"]` combined with cookie-based WS auth is a cross-site
WebSocket risk. Restrict to the frontend origin outside dev.

## [LOW] #34 — Pool/misleading-comment hygiene — RESOLVED

**Resolved:** All six hygiene items fixed:

- `session_manager.py:50` — `pool_use_lifo` is now `True` (LIFO keeps fewer
  connections warm; the recommended setting for async pools). The old comment
  claimed "use LIFO" while the value was `False`.
- `session_manager.py:126` — `asyncio.shield(session.close())` in the `finally`
  block replaced with a plain `await session.close()`. The `import asyncio` is
  gone (it was the only use).
- `channel_member.py:33` — `joined_at` default switched from the deprecated
  naive `datetime.utcnow` to `lambda: datetime.now(UTC)` (timezone-aware, on a
  `DateTime(timezone=True)` column).
- `message.py` — the `ix_messages_channel_created_at_desc` index is now
  genuinely DESC on `created_at` (`column("created_at").desc()`), so it serves
  the `ORDER BY created_at DESC, id DESC` read path with a forward scan and the
  name is no longer misleading. A new migration
  (`migrations/versions/2026-06-18-00-00-7f3a9c2e1b4d_messages_index_desc.py`,
  chains after `e908fde3f956`) drops and recreates the index DESC, keeping model
  and DB in sync.
- `message/routes.py` — `has_more` no longer uses the `len == limit`
  off-by-one. The route now fetches `limit + 1` rows and sets
  `has_more = len > limit`, dropping the oldest peek-ahead row so the client
  gets exactly `limit` and never gets a trailing empty page. The same fix was
  applied to the sibling `MessageRepository.get_messages_between_users_paginated`.
- `users/routes.py` — `GET /users` description/docstring corrected: it returns
  the current user's contacts, not "all users except current".

Original notes:
- `session_manager.py:49` — `pool_use_lifo=False` with a comment saying "use LIFO";
  LIFO (`True`) is the recommended setting for async pools (keeps fewer conns warm).
- `session_manager.py:125` — `asyncio.shield(session.close())` in `finally` is
  unusual; a plain `await session.close()` is the standard pattern.
- `channel_member.py:33` — `default=datetime.utcnow` is deprecated naive-UTC on a
  `DateTime(timezone=True)` column; use `datetime.now(UTC)`.
- `message.py:47` — index named `…_desc` is not actually DESC; make it DESC or
  rename, to match the "latest first" access path.
- `message/routes.py:50` — `has_more = len == limit` reports "more" when exactly
  `limit` rows remain → empty next page.
- `users/routes.py:24` — `GET /users` described as "all users except current" but
  returns the current user's contacts.

## Missing features (typical chat expectations, none implemented)
- Message edit / delete endpoints (model has `deleted_at` but no API)
- Read receipts / unread counts per channel
- Leave channel / remove member / list members endpoints
- Pagination on `get_user_channels` and `get_all_channel_members` (unbounded today)
- Last-message preview in the channel list
- User search by username (contacts are add-by-email only)
- Token refresh/rotation + logout (blacklist) — only a long-lived access cookie
- Password change/reset + email verification
- File/media attachments (content is JSONB, no upload flow)
- Per-channel message search (global `q` exists, channel-scoped does not)
- Mentions / push notifications
