import os
from flask import Flask, render_template, request, jsonify, send_file, abort
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path

app = Flask(__name__)
CORS(app)

# Configuration
DB_HOST = os.environ.get('DB_HOST', 'postgres')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'char_archive')
DB_USER = os.environ.get('DB_USER', 'char_archive')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'CharArch1ve_Db_2026!')
ARCHIVE_PATH = Path(os.environ.get('ARCHIVE_PATH', '/archive'))
HASHED_DATA_PATH = ARCHIVE_PATH / 'hashed-data'

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor
    )

def get_image_path(image_hash):
    """Convert image hash to file path."""
    if not image_hash or len(image_hash) < 4:
        return None
    h = image_hash.lower()
    return HASHED_DATA_PATH / h[0] / h[1] / h[2] / h[3:]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search')
def search():
    query = request.args.get('q', '').strip()
    source = request.args.get('source', 'all')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 24))
    offset = (page - 1) * per_page

    if not query:
        return jsonify({'results': [], 'total': 0, 'page': page})

    results = []
    total = 0

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Search pattern
        search_pattern = f'%{query}%'

        # Define source tables with their search configurations
        # Each source specifies columns to select and which columns to search
        sources = {
            'chub': {
                'table': 'chub_character_def',
                'columns': "id::text, author, name, image_hash, added, 'chub' as source, COALESCE(LEFT(definition->'data'->>'description', 150), '') as tagline",
                'search_cols': ['name', 'author']
            },
            'generic': {
                'table': 'generic_character_def',
                'columns': "card_data_hash as id, '' as author, name, image_hash, added, 'generic' as source, COALESCE(LEFT(definition->'data'->>'description', 150), COALESCE(LEFT(tagline, 150), '')) as tagline",
                'search_cols': ['name']
            },
            'booru': {
                'table': 'booru_character_def',
                'columns': "id::text, author, name, image_hash, added, 'booru' as source, COALESCE(LEFT(definition->'data'->>'description', 150), '') as tagline",
                'search_cols': ['name', 'author']
            },
            'webring': {
                'table': 'webring_character_def',
                'columns': "card_data_hash as id, author, name, image_hash, added, 'webring' as source, COALESCE(LEFT(definition->'data'->>'description', 150), COALESCE(LEFT(tagline, 150), '')) as tagline",
                'search_cols': ['name', 'author']
            },
            'char_tavern': {
                'table': 'char_tavern_character_def',
                'columns': "path as id, '' as author, path as name, image_hash, added, 'char_tavern' as source, COALESCE(LEFT(definition->'data'->>'description', 150), '') as tagline",
                'search_cols': ['path']
            },
            'risuai': {
                'table': 'risuai_character_def',
                'columns': "id::text, author, author as name, image_hash, added, 'risuai' as source, COALESCE(LEFT(definition->'data'->>'description', 150), '') as tagline",
                'search_cols': ['author']
            },
            'nyaime': {
                'table': 'nyaime_character_def',
                'columns': "id::text, author, author as name, image_hash, added, 'nyaime' as source, COALESCE(LEFT(definition->'data'->>'description', 150), '') as tagline",
                'search_cols': ['author']
            }
        }

        if source != 'all':
            sources = {source: sources[source]} if source in sources else {}

        # Build union query for searching across tables
        union_parts = []
        params = []

        for src_name, src_info in sources.items():
            # Build WHERE clause based on searchable columns for this table
            where_conditions = ' OR '.join([f"{col} ILIKE %s" for col in src_info['search_cols']])
            union_parts.append(f"""
                SELECT {src_info['columns']}
                FROM {src_info['table']}
                WHERE {where_conditions}
            """)
            params.extend([search_pattern] * len(src_info['search_cols']))

        if not union_parts:
            return jsonify({'results': [], 'total': 0, 'page': page})

        # Count total results
        count_query = f"""
            SELECT COUNT(*) as total FROM (
                {' UNION ALL '.join(union_parts)}
            ) combined
        """
        cur.execute(count_query, params)
        total = cur.fetchone()['total']

        # Get paginated results
        results_query = f"""
            SELECT * FROM (
                {' UNION ALL '.join(union_parts)}
            ) combined
            ORDER BY added DESC
            LIMIT %s OFFSET %s
        """
        cur.execute(results_query, params + [per_page, offset])
        results = cur.fetchall()

        cur.close()
        conn.close()

        # Convert to list of dicts
        results = [dict(r) for r in results]

    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({'error': str(e)}), 500

    return jsonify({
        'results': results,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    })

@app.route('/api/character/<source>/<path:char_id>')
def get_character(source, char_id):
    """Get detailed character information."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        table_map = {
            'chub': ('chub_character_def', 'id', 'id = %s'),
            'generic': ('generic_character_def', 'card_data_hash', 'card_data_hash = %s'),
            'booru': ('booru_character_def', 'id', 'id = %s'),
            'webring': ('webring_character_def', 'card_data_hash', 'card_data_hash = %s'),
            'char_tavern': ('char_tavern_character_def', 'path', 'path = %s'),
            'risuai': ('risuai_character_def', 'id', 'id = %s'),
            'nyaime': ('nyaime_character_def', 'id', 'id = %s')
        }

        if source not in table_map:
            return jsonify({'error': 'Invalid source'}), 400

        table, id_col, where = table_map[source]

        cur.execute(f"""
            SELECT * FROM {table}
            WHERE {where}
            ORDER BY added DESC
            LIMIT 1
        """, (char_id,))

        result = cur.fetchone()
        cur.close()
        conn.close()

        if not result:
            return jsonify({'error': 'Character not found'}), 404

        # Convert to dict and handle special fields
        char_data = dict(result)

        # Remove raw bytes from response (too large)
        if 'raw' in char_data:
            char_data['has_raw'] = True
            del char_data['raw']

        return jsonify(char_data)

    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({'error': str(e)}), 500

def embed_chara_in_png(png_data, chara_json):
    """Embed character data into PNG as a tEXt chunk with keyword 'chara'."""
    import struct
    import base64
    import zlib as zlib_mod

    # Base64 encode the character JSON
    chara_b64 = base64.b64encode(chara_json.encode('utf-8'))

    # Create tEXt chunk: keyword + null separator + text
    keyword = b'chara'
    text_data = keyword + b'\x00' + chara_b64

    # Calculate CRC for the chunk (includes type + data)
    chunk_type = b'tEXt'
    crc = zlib_mod.crc32(chunk_type + text_data) & 0xffffffff

    # Build the chunk: length (4 bytes) + type (4 bytes) + data + crc (4 bytes)
    chunk = struct.pack('>I', len(text_data)) + chunk_type + text_data + struct.pack('>I', crc)

    # Find the position to insert (before IEND chunk)
    # IEND is the last 12 bytes: length(4) + 'IEND'(4) + crc(4)
    iend_pos = png_data.rfind(b'IEND')
    if iend_pos == -1:
        raise ValueError("Invalid PNG: no IEND chunk found")

    # IEND chunk starts 4 bytes before 'IEND' (the length field)
    insert_pos = iend_pos - 4

    # Insert our tEXt chunk before IEND
    new_png = png_data[:insert_pos] + chunk + png_data[insert_pos:]

    return new_png

@app.route('/api/card/<source>/<path:char_id>')
def download_card(source, char_id):
    """Download character as PNG card with embedded data."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        table_map = {
            'chub': ('chub_character_def', 'id = %s', 'name'),
            'generic': ('generic_character_def', 'card_data_hash = %s', 'name'),
            'booru': ('booru_character_def', 'id = %s', 'name'),
            'webring': ('webring_character_def', 'card_data_hash = %s', 'name'),
            'char_tavern': ('char_tavern_character_def', 'path = %s', 'path'),
            'risuai': ('risuai_character_def', 'id = %s', 'id'),
            'nyaime': ('nyaime_character_def', 'id = %s', 'id')
        }

        if source not in table_map:
            return jsonify({'error': 'Invalid source'}), 400

        table, where, name_col = table_map[source]

        cur.execute(f"""
            SELECT {name_col}, raw, image_hash, definition FROM {table}
            WHERE {where}
            ORDER BY added DESC
            LIMIT 1
        """, (char_id,))

        result = cur.fetchone()
        cur.close()
        conn.close()

        if not result:
            return jsonify({'error': 'Character not found'}), 404

        import zlib
        import io
        import json

        raw_data = result['raw']
        image_hash = result['image_hash']
        definition = result['definition']
        name = result[name_col] or char_id

        # Sanitize filename
        safe_name = "".join(c for c in str(name) if c.isalnum() or c in ' -_').strip() or 'character'

        # Decompress raw if needed
        if raw_data:
            try:
                raw_data = zlib.decompress(raw_data)
            except:
                pass

        # Check if raw_data is already a valid PNG with embedded data
        if raw_data and raw_data[:8] == b'\x89PNG\r\n\x1a\n':
            # It's already a PNG, return as-is
            return send_file(
                io.BytesIO(raw_data),
                mimetype='image/png',
                as_attachment=True,
                download_name=f"{safe_name}.png"
            )

        # Otherwise, we need to create a PNG card by embedding the definition into the image
        # Get the image file
        image_path = get_image_path(image_hash)
        if not image_path or not image_path.exists():
            return jsonify({'error': 'Image not found'}), 404

        # Read the original image
        with open(image_path, 'rb') as f:
            png_data = f.read()

        # Verify it's a PNG
        if png_data[:8] != b'\x89PNG\r\n\x1a\n':
            return jsonify({'error': 'Image is not a valid PNG'}), 500

        # Get character JSON - prefer raw (decompressed) if it's JSON, otherwise use definition
        if raw_data:
            try:
                # Check if raw_data is valid JSON
                json.loads(raw_data.decode('utf-8'))
                chara_json = raw_data.decode('utf-8')
            except:
                chara_json = json.dumps(definition, ensure_ascii=False)
        else:
            chara_json = json.dumps(definition, ensure_ascii=False)

        # Embed the character data into the PNG
        card_png = embed_chara_in_png(png_data, chara_json)

        return send_file(
            io.BytesIO(card_png),
            mimetype='image/png',
            as_attachment=True,
            download_name=f"{safe_name}.png"
        )

    except Exception as e:
        print(f"Download error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/card/<source>/<path:char_id>/json')
def download_card_json(source, char_id):
    """Download character definition as JSON."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        table_map = {
            'chub': ('chub_character_def', 'id = %s', 'name'),
            'generic': ('generic_character_def', 'card_data_hash = %s', 'name'),
            'booru': ('booru_character_def', 'id = %s', 'name'),
            'webring': ('webring_character_def', 'card_data_hash = %s', 'name'),
            'char_tavern': ('char_tavern_character_def', 'path = %s', 'path'),
            'risuai': ('risuai_character_def', 'id = %s', 'id'),
            'nyaime': ('nyaime_character_def', 'id = %s', 'id')
        }

        if source not in table_map:
            return jsonify({'error': 'Invalid source'}), 400

        table, where, name_col = table_map[source]

        cur.execute(f"""
            SELECT {name_col}, definition FROM {table}
            WHERE {where}
            ORDER BY added DESC
            LIMIT 1
        """, (char_id,))

        result = cur.fetchone()
        cur.close()
        conn.close()

        if not result:
            return jsonify({'error': 'Character not found'}), 404

        import io
        import json

        name = result[name_col] or char_id
        definition = result['definition']

        # Sanitize filename
        safe_name = "".join(c for c in str(name) if c.isalnum() or c in ' -_').strip() or 'character'

        # Convert definition to JSON string
        json_data = json.dumps(definition, indent=2, ensure_ascii=False)

        return send_file(
            io.BytesIO(json_data.encode('utf-8')),
            mimetype='application/json',
            as_attachment=True,
            download_name=f"{safe_name}.json"
        )

    except Exception as e:
        print(f"JSON download error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/image/<image_hash>')
def serve_image(image_hash):
    """Serve character image by hash."""
    image_path = get_image_path(image_hash)

    if not image_path or not image_path.exists():
        abort(404)

    return send_file(image_path, mimetype='image/png')

@app.route('/api/stats')
def stats():
    """Get database statistics."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        stats = {}
        tables = [
            ('chub', 'chub_character_def'),
            ('generic', 'generic_character_def'),
            ('booru', 'booru_character_def'),
            ('webring', 'webring_character_def'),
            ('char_tavern', 'char_tavern_character_def'),
            ('risuai', 'risuai_character_def'),
            ('nyaime', 'nyaime_character_def')
        ]

        total = 0
        for name, table in tables:
            cur.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cur.fetchone()['count']
            stats[name] = count
            total += count

        stats['total'] = total

        cur.close()
        conn.close()

        return jsonify(stats)

    except Exception as e:
        print(f"Stats error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
