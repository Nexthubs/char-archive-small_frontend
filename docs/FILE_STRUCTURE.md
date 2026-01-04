# File Storage Structure (Inferred)

This is based on paths and conventions referenced in the server code. The repo does not ship an on-disk layout; treat this as the expected structure.

## Storage Roots

- `/mnt/share/archive` (NFS share in the original setup)
- Fallback for images only: `/srv/chub-archive/archive`

## Archive File Tree (Crazy File Server)

The "crazy-file-server" (configured in `backend/crazyfs.yaml`) serves a raw file tree:

- Root: `/mnt/share/archive/files/`
- This is used for file browsing/downloads, separate from the API.
- The config lists restricted paths under the root:
  - `/historical`
  - `/third-party`
  - `/other`
  - `/articles`
  - `/logs`
  - `/takeout`

These paths are inferred from config and are likely top-level directories under `files/`.

## Image Store (Hashed)

Character and user images are stored separately from the raw files:

- Root: `/mnt/share/archive/hashed-data/`
- Fallback root: `/srv/chub-archive/archive/hashed-data`
- Path is sharded by the MD5 hash of the image (hash is stored in DB as `image_hash`):

```
/mnt/share/archive/hashed-data/
  <h0>/
    <h1>/
      <h2>/
        <h3...>
```

Where `h0`, `h1`, `h2` are the first three hex characters, and `h3...` is the remainder of the hash.

## Webring Icons

Webring icons are stored alongside the image root:

- `/mnt/share/archive/webring/icons/`
- Derived from `hashed-data` parent: `CARD_IMAGE_ROOT_DIR.parent / 'webring/icons'`
