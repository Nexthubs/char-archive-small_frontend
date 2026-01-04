#!/bin/bash
set -e

echo "Checking if database needs to be restored..."

# Check if database is empty (no tables)
TABLE_COUNT=$(psql -U char_archive -d char_archive -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')

if [ "$TABLE_COUNT" = "0" ] || [ -z "$TABLE_COUNT" ]; then
    echo "Database is empty, restoring from dump..."

    if [ -f /docker-entrypoint-initdb.d/database.dump ]; then
        echo "Starting database restore (this may take a while for large dumps)..."
        pg_restore -U char_archive -d char_archive -v /docker-entrypoint-initdb.d/database.dump 2>&1 || {
            echo "pg_restore failed, trying psql..."
            psql -U char_archive -d char_archive < /docker-entrypoint-initdb.d/database.dump
        }
        echo "Database restore completed!"
    else
        echo "No database dump found at /docker-entrypoint-initdb.d/database.dump"
    fi
else
    echo "Database already has $TABLE_COUNT tables, skipping restore."
fi
