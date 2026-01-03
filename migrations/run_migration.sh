#!/bin/bash

# Migration script for normalizing feedback table relationships
# This script performs a safe migration with backups and verification

# Configuration
DB_NAME="coachmeplay"
DB_USER="root"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Step 1: Create full database backup
echo "Creating full database backup..."
mysqldump -u "$DB_USER" "$DB_NAME" > "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}_full.sql"

if [ $? -ne 0 ]; then
    echo "Error: Database backup failed"
    exit 1
fi

# Step 2: Create specific table backup
echo "Creating feedback table backup..."
mysqldump -u "$DB_USER" "$DB_NAME" feedback > "$BACKUP_DIR/feedback_${TIMESTAMP}.sql"

if [ $? -ne 0 ]; then
    echo "Error: Feedback table backup failed"
    exit 1
fi

# Step 3: Run migration
echo "Running migration..."
mysql -u "$DB_USER" "$DB_NAME" < ./migrations/001_normalize_feedback_table.sql

if [ $? -ne 0 ]; then
    echo "Error: Migration failed"
    echo "Rolling back changes..."
    mysql -u "$DB_USER" "$DB_NAME" < "$BACKUP_DIR/feedback_${TIMESTAMP}.sql"
    echo "Rollback complete. Please check the database state."
    exit 1
fi

# Step 4: Verify migration
echo "Verifying migration..."
mysql -u "$DB_USER" "$DB_NAME" -e "
    SELECT 
        COUNT(*) as total_rows,
        COUNT(f.coach_id) as valid_coach_refs,
        COUNT(f.athlete_id) as valid_athlete_refs
    FROM feedback f
    JOIN coaches c ON f.coach_id = c.coach_id
    JOIN athletes a ON f.athlete_id = a.athlete_id;
"

if [ $? -ne 0 ]; then
    echo "Warning: Verification query failed. Please check the database state manually."
    exit 1
fi

echo "Migration completed successfully!"
echo "Backups saved in: $BACKUP_DIR"
echo ""
echo "To rollback, run:"
echo "mysql -u $DB_USER $DB_NAME < $BACKUP_DIR/feedback_${TIMESTAMP}.sql"