# Erdpuls Collective Threshold Model - Deployment Guide

## Architecture

```
Internet → Caddy (80/443)
              │
              ├── living-labs.ubec.network  → localhost:8000
              ├── bioregional.ubec.network  → localhost:8001
              ├── api.ubec.network          → localhost:8002
              ├── iot.ubec.network          → localhost:8003
              ├── erdpuls.ubec.network      → localhost:8004 ✓
              └── mapservice.ubec.network   → localhost:8080
```

## Prerequisites

- Python 3.11+
- PostgreSQL with `ubec_erdpuls` database
- Caddy reverse proxy
- systemd

## Step 1: Upload & Extract

```bash
# From your local machine
scp erdpuls-threshold.zip kelpit@92.205.28.58:/tmp/

# On the server
ssh kelpit@92.205.28.58
cd /tmp
unzip erdpuls-threshold.zip
sudo mkdir -p /var/www/erdpuls-threshold
sudo mv erdpuls-threshold/* /var/www/erdpuls-threshold/
sudo chown -R www-data:www-data /var/www/erdpuls-threshold
```

## Step 2: Python Environment

```bash
cd /var/www/erdpuls-threshold
sudo -u www-data python3 -m venv venv
sudo -u www-data venv/bin/pip install -r requirements.txt
```

## Step 3: PostgreSQL Schema

The app uses the existing `ubec_erdpuls` database with a new schema `erdpuls_threshold`.

```bash
# Connect to the database
sudo -u postgres psql -d ubec_erdpuls

# Run the schema script
\i /var/www/erdpuls-threshold/schema.sql

# Grant permissions (use your app user)
GRANT USAGE ON SCHEMA erdpuls_threshold TO your_app_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA erdpuls_threshold TO your_app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA erdpuls_threshold TO your_app_user;

# Verify
\dn                          -- list schemas
\dt erdpuls_threshold.*      -- list tables

\q
```

## Step 4: Environment File

```bash
# Generate a secret key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Create .env file
sudo nano /var/www/erdpuls-threshold/.env
```

Contents:
```
DATABASE_URL=postgresql://your_user:your_password@localhost:5432/ubec_erdpuls
SECRET_KEY=paste_generated_key_here
DEBUG=false
```

```bash
sudo chmod 600 /var/www/erdpuls-threshold/.env
sudo chown www-data:www-data /var/www/erdpuls-threshold/.env
```

## Step 5: Systemd Service

```bash
# Create log directory
sudo mkdir -p /var/log/erdpuls
sudo chown www-data:www-data /var/log/erdpuls

# Install service
sudo cp /var/www/erdpuls-threshold/deploy/erdpuls-threshold.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable erdpuls-threshold
sudo systemctl start erdpuls-threshold

# Check status
sudo systemctl status erdpuls-threshold
```

## Step 6: Caddy Configuration

```bash
sudo nano /etc/caddy/Caddyfile
```

Add after `iot.ubec.network` block:

```
# Erdpuls Collective Threshold Model
erdpuls.ubec.network {
	reverse_proxy localhost:8004
	log {
		output file /var/log/caddy/erdpuls_access.log
	}
}
```

```bash
sudo systemctl reload caddy
```

## Step 8: Create Admin User

```bash
cd /var/www/erdpuls-threshold
sudo -u www-data venv/bin/python create_admin.py admin@example.com YourSecurePassword "Admin Name"
```

## Step 9: Test

```bash
# Test locally
curl http://localhost:8004/health

# Test via domain
curl https://erdpuls.ubec.network/health
```

Visit: https://erdpuls.ubec.network

API docs: https://erdpuls.ubec.network/api/docs

## Step 8: Seed Sample Data (Optional)

```bash
cd /var/www/erdpuls-threshold
sudo -u www-data venv/bin/python seed_data.py
```

## Useful Commands

| Command | Description |
|---------|-------------|
| `sudo systemctl status erdpuls-threshold` | Check app status |
| `sudo systemctl restart erdpuls-threshold` | Restart app |
| `sudo journalctl -u erdpuls-threshold -f` | View live logs |
| `sudo -u postgres psql -d ubec_erdpuls` | Connect to database |
| `SET search_path TO erdpuls_threshold;` | Switch to schema (in psql) |

## Troubleshooting

### App won't start
```bash
# Check logs
sudo journalctl -u erdpuls-threshold -n 50

# Test manually
cd /var/www/erdpuls-threshold
sudo -u www-data venv/bin/python -c "from app.main import app; print('OK')"
```

### Database connection issues
```bash
# Test connection
sudo -u www-data psql "postgresql://user:pass@localhost:5432/ubec_erdpuls" -c "SELECT 1"
```

### Permission issues
```bash
sudo chown -R www-data:www-data /var/www/erdpuls-threshold
sudo chmod 600 /var/www/erdpuls-threshold/.env
```
