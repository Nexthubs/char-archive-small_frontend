# Database Structure (Inferred)

No migrations or DDL are present in the repo. The schema below is inferred from SQL usage in the backend code and should be validated against your actual dump.

## Datastores

- **Postgres**: main archive database (configured as `char_archive`)
- **MySQL**: a small frontend message table used by `backend/frontend-msg.py`

## Postgres: Core Patterns

- **Versioned definition tables** store card definitions plus the original raw card bytes.
  - Queries typically `ORDER BY added DESC LIMIT 1`, indicating multiple versions per card.
  - `definition` is JSON (card data in parsed form).
  - `raw` is compressed bytes of the original card data (zlib).
  - `metadata` is JSON and includes safety moderation and token counts.
- **Node tables** store scraped platform metadata (often in a JSON `data`/`node` column).
- **Images** are referenced by `image_hash` and live in the hashed file tree documented in `FILE_STRUCTURE.md`.
- **Hidden flag**: safety tooling sets a `hidden` boolean on "meta" tables (see safety handlers); some def tables double as meta tables.

## Postgres: Tables and Fields Referenced in Code

### Chub

- `chub_character`
  - Primary key: `id`
  - Fields referenced: `id`, `author`, `name`, `data` (JSON), `ratings` (JSON), `chats` (JSON), `added`, `updated`, `hidden`
- `chub_character_def`
  - Primary key: `id` (paired with `full_path` for lookups)
  - Fields referenced: `id`, `author`, `full_path`, `definition` (JSON), `raw` (bytea), `image_hash`, `metadata` (JSON), `added`
- `chub_lorebook`
  - Primary key: `id`
  - Fields referenced: `id`, `author`, `name`, `data` (JSON), `added`, `updated`, `hidden`
- `chub_lorebook_def`
  - Primary key: `id` (paired with `full_path` for lookups)
  - Fields referenced: `id`, `author`, `full_path`, `definition` (JSON), `raw` (bytea), `image_hash`, `metadata` (JSON), `added`
- `chub_user`
  - Primary key: likely `username`
  - Fields referenced: `username`, `data` (JSON, includes `bio`), `image_hash`, `added`, `updated`

### Generic

- `generic_character_def`
  - Primary key: `card_data_hash`
  - Fields referenced: `card_data_hash`, `name`, `definition` (JSON), `raw` (bytea), `image_hash`, `metadata` (JSON), `summary`, `tagline`, `source`, `source_url`, `added`, `hidden`

### Webring

- `webring_character_def`
  - Primary key: `card_data_hash`
  - Fields referenced: `card_data_hash`, `author`, `name`, `definition` (JSON), `raw` (bytea), `image_hash`, `metadata` (JSON), `summary`, `tagline`, `added`, `hidden`

### Booru

- `booru_character_def`
  - Primary key: `id`
  - Fields referenced: `id`, `author`, `name`, `definition` (JSON), `raw` (bytea), `image_hash`, `metadata` (JSON), `summary`, `tagline`, `comments`, `created`, `added`, `hidden`

### Nyaime

- `nyaime_character`
  - Primary key: `id`
  - Fields referenced: `id`, `author`, `name`, `node` (JSON), `added`, `updated`, `hidden`
- `nyaime_character_def`
  - Primary key: `id`
  - Fields referenced: `id`, `author`, `definition` (JSON), `raw` (bytea), `image_hash`, `metadata` (JSON), `added`
- `nyaime_user`
  - Primary key: likely `name`
  - Fields referenced: `name`, `bio`, `is_guest`, `updated`, `added`

### Risuai

- `risuai_character`
  - Primary key: `id`
  - Fields referenced: `id`, `author`, `name`, `node` (JSON), `hidden`
- `risuai_character_def`
  - Primary key: `id`
  - Fields referenced: `id`, `author`, `definition` (JSON), `raw` (bytea), `image_hash`, `metadata` (JSON), `added`
- `risuai_user`
  - Primary key: likely `username`
  - Fields referenced: `username`, `description`, `updated`, `added`

### Character Tavern

- `char_tavern_character`
  - Primary key: `path`
  - Fields referenced: `path`, `author`, `name`, `data` (JSON), `reviews` (JSON), `hidden`
- `char_tavern_character_def`
  - Primary key: `path`
  - Fields referenced: `path`, `definition` (JSON), `raw` (bytea), `image_hash`, `metadata` (JSON), `added`
- `char_tavern_user`
  - Primary key: likely `username`
  - Fields referenced: `username`, `bio`, `image_hash`, `added`, `updated`

### Other Tables

- `embedding_summaries`
  - Fields referenced: `id` (string, doc hash), `summary`
- `aicg_chronicles`
  - Fields referenced: `url`, `text`, `timestamp`

## MySQL: Frontend Message

From `backend/frontend-msg.py`:

- `message`
  - `id` (auto-increment PK)
  - `title`
  - `message`
  - `msg_type`
  - `active` (boolean)

## Notes for Re-Implementing

- Many routes expect JSON shape in `definition` and `data`/`node` fields. The exact JSON structures come from the scraped sources.
- Versioning is per-card: selecting the latest by `added` is standard for definitions and images.
- The moderation pipeline expects a `metadata.safety` JSON object and a `hidden` flag on the meta table.
