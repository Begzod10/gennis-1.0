#!/bin/bash

# Set paths
FLASK_ADMIN_PATH=$(python3 -c "import flask_admin; print(flask_admin.__path__[0])")
DEST_STATIC_DIR="/home/classroom/test_gennis/backend/static"

echo "Copying Flask-Admin static files..."
echo "From: $FLASK_ADMIN_PATH/static"
echo "To:   $DEST_STATIC_DIR"

# Make sure destination exists
mkdir -p "$DEST_STATIC_DIR"

# Copy static folder contents
cp -r "$FLASK_ADMIN_PATH/static/"* "$DEST_STATIC_DIR/"

echo "✅ Done. Flask-Admin static files copied successfully."
echo "Test your admin panel at: http://test.gennis.uz/admin/"
