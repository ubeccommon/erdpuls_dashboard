#!/bin/bash
# Erdpuls Collective Threshold Model - Deployment Script
# Run as root or with sudo on 92.205.28.58

set -e  # Exit on error

echo "🌱 Erdpuls Collective Threshold Model - Deployment"
echo "=================================================="

# Variables
APP_DIR="/var/www/erdpuls-threshold"
DB_NAME="erdpuls_threshold"
DB_USER="erdpuls"
LOG_DIR="/var/log/erdpuls"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Create directories
echo -e "\n${GREEN}[1/8]${NC} Creating directories..."
mkdir -p $APP_DIR
mkdir -p $LOG_DIR
chown www-data:www-data $LOG_DIR

# Step 2: Copy application files
echo -e "\n${GREEN}[2/8]${NC} Copying application files..."
# (You'll upload the files manually or via git)
echo -e "${YELLOW}      → Upload your application files to $APP_DIR${NC}"

# Step 3: Set up Python virtual environment
echo -e "\n${GREEN}[3/8]${NC} Setting up Python virtual environment..."
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Step 4: Create PostgreSQL database and user
echo -e "\n${GREEN}[4/8]${NC} Setting up PostgreSQL..."
echo -e "${YELLOW}      → Enter a password for the 'erdpuls' database user:${NC}"
read -s DB_PASSWORD

sudo -u postgres psql <<EOF
-- Create user if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
        CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
    END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

echo "      Database '$DB_NAME' ready."

# Step 5: Initialize database schema
echo -e "\n${GREEN}[5/8]${NC} Initializing database schema..."
PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -d $DB_NAME -f $APP_DIR/schema.sql

# Step 6: Create environment file
echo -e "\n${GREEN}[6/8]${NC} Creating environment file..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

cat > $APP_DIR/.env <<EOF
FLASK_CONFIG=production
FLASK_DEBUG=false
SECRET_KEY=$SECRET_KEY
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME
EOF

chmod 600 $APP_DIR/.env
chown www-data:www-data $APP_DIR/.env
echo "      .env file created with secure permissions."

# Step 7: Set up systemd service
echo -e "\n${GREEN}[7/8]${NC} Setting up systemd service..."
cp $APP_DIR/deploy/erdpuls-threshold.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable erdpuls-threshold
systemctl start erdpuls-threshold

echo "      Service started. Check status with: systemctl status erdpuls-threshold"

# Step 8: Update Caddy configuration
echo -e "\n${GREEN}[8/8]${NC} Caddy configuration..."
echo -e "${YELLOW}      → Add the following to your Caddyfile:${NC}"
echo ""
cat $APP_DIR/deploy/caddy-site.conf
echo ""
echo -e "${YELLOW}      → Then reload Caddy: systemctl reload caddy${NC}"

# Done
echo ""
echo "=================================================="
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Add Caddy config and reload: systemctl reload caddy"
echo "  2. Test: https://erdpuls.ubec.network (proxied from localhost:8004)"
echo "  3. (Optional) Seed sample data: cd $APP_DIR && source venv/bin/activate && python seed_data.py"
echo ""
echo "Useful commands:"
echo "  - View logs:    journalctl -u erdpuls-threshold -f"
echo "  - Restart app:  systemctl restart erdpuls-threshold"
echo "  - App status:   systemctl status erdpuls-threshold"
echo ""
echo "🌱 The community holds each offering into being."
