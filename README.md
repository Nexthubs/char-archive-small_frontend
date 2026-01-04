# Character Archive Frontend

A Flask-based web application for searching and downloading character cards from the Character Archive. Features a modern Tailwind CSS interface with full-text search, character previews, and card downloads.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.1-green.svg)

## Features

- **Full-text search** across all character sources (Chub, JanitorAI, RisuAI, Character Tavern, Booru, Webring, Generic)
- **Character card previews** with lazy-loaded images
- **Detailed character modal** showing tags, description, and first message
- **Card downloads** in PNG format with embedded character data
- **Source filtering** to search specific platforms
- **Responsive design** with dark theme and purple gradient accents
- **Pagination** with customizable results per page

## Architecture

### Backend (app.py)

Flask API with the following endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves the main HTML page |
| `/api/search` | GET | Search characters across all sources |
| `/api/character/<source>/<id>` | GET | Get detailed character info |
| `/api/card/<source>/<id>` | GET | Download character card (PNG) |
| `/image/<hash>` | GET | Serve character image by hash |
| `/api/stats` | GET | Get database statistics |

### Frontend (templates/index.html)

Single-page application using:
- **Tailwind CSS** (via CDN) for styling
- **Vanilla JavaScript** for interactivity
- Responsive grid layout (2-6 columns based on screen size)
- Modal animations and hover effects
- Custom text cleaning for character card formatting

## Prerequisites

- Docker Engine (20.10+)
- Docker Compose (v2.0+)
- PostgreSQL database with Character Archive data
- Image archive at `../archive/hashed-data/`

## Quick Start

### 1. Set Up Environment Variables

Create a `.env` file or set environment variables:

```bash
DB_HOST=postgres              # PostgreSQL host
DB_PORT=5432                  # PostgreSQL port
DB_NAME=char_archive          # Database name
DB_USER=char_archive          # Database user
DB_PASSWORD=your_password     # Database password
ARCHIVE_PATH=/archive         # Path to archive images
```

### 2. Run with Docker Compose

Add this service to your `docker-compose.yml`:

```yaml
services:
  frontend:
    build:
      context: ./small_front
      dockerfile: Dockerfile
    environment:
      DB_HOST: postgres
      DB_PORT: "5432"
      DB_NAME: char_archive
      DB_USER: char_archive
      DB_PASSWORD: your_password_here
      ARCHIVE_PATH: /archive
    volumes:
      - ./archive:/archive:ro
    ports:
      - "8080:5000"
    depends_on:
      - postgres
    networks:
      - char_archive_network
```

Start the services:

```bash
docker compose up -d frontend
```

### 3. Access the Frontend

Open your browser and navigate to:
- Local: `http://localhost:8080`
- Tailscale: `http://100.108.69.91:8080` (if configured)

## Development

### Local Development Setup

1. Clone the repository:
```bash
git clone https://github.com/sproutingnerd/char-archive-small_frontend.git
cd char-archive-small_frontend/small_front
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables:
```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=char_archive
export DB_USER=char_archive
export DB_PASSWORD=your_password
export ARCHIVE_PATH=/path/to/archive
```

4. Run the Flask app:
```bash
python app.py
```

The app will be available at `http://localhost:5000`

### Rebuild After Changes

```bash
docker compose build frontend && docker compose up -d frontend
```

### View Logs

```bash
docker compose logs -f frontend
```

## API Usage

### Search Characters

```bash
curl "http://localhost:8080/api/search?q=test&source=chub&page=1&per_page=24"
```

**Parameters:**
- `q` (required): Search query
- `source` (optional): Filter by source (chub, generic, booru, webring, char_tavern, risuai, nyaime, all)
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Results per page (default: 24)

**Response:**
```json
{
  "results": [
    {
      "id": "123456",
      "author": "username",
      "name": "Character Name",
      "image_hash": "abc123...",
      "added": "2024-12-01T00:00:00+00:00",
      "source": "chub"
    }
  ],
  "total": 1000,
  "page": 1,
  "per_page": 24,
  "pages": 42
}
```

### Get Character Details

```bash
curl "http://localhost:8080/api/character/chub/123456"
```

### Download Character Card

```bash
curl "http://localhost:8080/api/card/chub/123456" -o character.png
```

### Get Database Stats

```bash
curl "http://localhost:8080/api/stats"
```

## Database Schema

The frontend queries these tables per platform:

| Source | Table | Searchable Columns |
|--------|-------|-------------------|
| chub | chub_character_def | name, author |
| generic | generic_character_def | name |
| booru | booru_character_def | name, author |
| webring | webring_character_def | name, author |
| char_tavern | char_tavern_character_def | path |
| risuai | risuai_character_def | author |
| nyaime | nyaime_character_def | author |

Each table follows the pattern:
- `{platform}_character` - Scraped metadata with JSON data
- `{platform}_character_def` - Card definitions with:
  - `definition` (JSONB): Character data
  - `raw` (bytea): zlib-compressed original card
  - `image_hash`: MD5 hash for image lookup
  - `metadata` (JSON): Safety ratings and token info

## Image Storage

Images are stored in `archive/hashed-data/` using MD5 hash sharding:

**Path format:** `/{h[0]}/{h[1]}/{h[2]}/{h[3:]}`

**Example:**
- Hash: `54db4830ceab552d4824dd5b016f4b06`
- Path: `/5/4/d/b4830ceab552d4824dd5b016f4b06`

## Troubleshooting

### Search returns no results
- Check database connection in logs
- Verify PostgreSQL is running and healthy
- Test database directly: `docker compose exec postgres psql -U char_archive -d char_archive`

### Images not loading
- Verify archive volume is mounted correctly
- Check image hash exists in `archive/hashed-data/`
- Verify file permissions on archive folder

### Container keeps restarting
- Check logs: `docker compose logs frontend`
- Ensure PostgreSQL is healthy before frontend starts
- Verify all environment variables are set correctly

### Database connection errors
- Ensure `DB_HOST` matches PostgreSQL service name in docker-compose
- Check database credentials
- Verify PostgreSQL port is accessible

## Project Structure

```
char-archive-small_frontend/
├── README.md                      # This file
├── docker-compose.yml             # Production Docker Compose config
├── docker-compose.import.yml      # Docker Compose with DB import
├── init-db.sh                     # Database initialization script
├── docs/                          # Documentation
│   ├── MIGRATION.md               # Server migration guide
│   ├── setup-guide.md             # Complete Docker setup
│   ├── frontend-guide.md          # API and architecture details
│   ├── DATABASE_STRUCTURE.md      # Full database schema
│   └── FILE_STRUCTURE.md          # Image storage layout
└── small_front/                   # Frontend application
    ├── app.py                     # Flask API backend
    ├── templates/
    │   └── index.html             # Tailwind CSS frontend
    ├── requirements.txt           # Python dependencies
    └── Dockerfile                 # Container configuration
```

## Dependencies

- **Flask** 3.1.0 - Web framework
- **psycopg2-binary** 2.9.10 - PostgreSQL adapter
- **Pillow** 11.0.0 - Image processing
- **gunicorn** 23.0.0 - Production WSGI server

See `requirements.txt` for complete list.

## Related Documentation

- [Full Setup Guide](docs/setup-guide.md) - Complete Docker setup instructions
- [Frontend Architecture](docs/frontend-guide.md) - Detailed API and schema documentation
- [Database Structure](docs/DATABASE_STRUCTURE.md) - Complete database schema reference
- [File Structure](docs/FILE_STRUCTURE.md) - Image storage and file organization
- [Migration Guide](docs/MIGRATION.md) - Server migration instructions

## License

MIT License - see LICENSE file for details

## Credits

Part of the Character Archive preservation project. Original server and scraper source code:
- [char-archive-server](https://git.evulid.cc/cyberes/char-archive-server)
- [char-archive-scraper](https://git.evulid.cc/cyberes/char-archive-scraper)

## Contributing

This is an archive preservation project that shut down in January 2026. The code is provided as-is for historical reference and self-hosting purposes.

For issues or questions, please open an issue on GitHub.
