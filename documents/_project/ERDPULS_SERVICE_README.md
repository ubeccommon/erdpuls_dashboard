# Erdpuls Müllrose - Systemd Service Installation Guide

## Service File: `erdpuls_ubec.service`

This systemd service file manages the Erdpuls Collective Threshold Model platform.

## Architecture

```
Internet → Caddy (80/443)
              │
              ├── living-labs.ubec.network  → localhost:8000
              ├── bioregional.ubec.network  → localhost:8001
              ├── api.ubec.network          → localhost:8002
              ├── iot.ubec.network          → localhost:8003
              ├── erdpuls.ubec.network      → localhost:8004 ← This service
              └── mapservice.ubec.network   → localhost:8080
```

## Quick Installation

```bash
# 1. Copy service file to systemd
sudo cp erdpuls_ubec.service /etc/systemd/system/

# 2. Reload systemd daemon
sudo systemctl daemon-reload

# 3. Enable service to start on boot
sudo systemctl enable erdpuls_ubec

# 4. Start the service
sudo systemctl start erdpuls_ubec

# 5. Verify it's running
sudo systemctl status erdpuls_ubec
```

## Prerequisites

Before starting the service, ensure:

1. **Python virtual environment exists:**
   ```bash
   cd /home/kelpit/UBEC_ERDPULS
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Environment file is configured:**
   ```bash
   nano /home/kelpit/UBEC_ERDPULS/.env
   ```
   
   Required variables:
   ```
   DATABASE_URL=postgresql://ubecpuls:<password>@localhost:5432/ubec_erdpuls
   SECRET_KEY=<generated-secret>
   DEBUG=false
   BASE_URL=https://erdpuls.ubec.network
   SMTP_HOST=mail.ubec.network
   SMTP_PORT=465
   SMTP_USER=erdpuls@ubec.network
   SMTP_PASSWORD=<password>
   SMTP_USE_TLS=false
   SMTP_FROM_EMAIL=noreply@ubec.network
   SMTP_FROM_NAME=Erdpuls Müllrose
   ```

3. **Secure the .env file:**
   ```bash
   chmod 600 /home/kelpit/UBEC_ERDPULS/.env
   ```

## Common Commands

| Command | Description |
|---------|-------------|
| `sudo systemctl start erdpuls_ubec` | Start the service |
| `sudo systemctl stop erdpuls_ubec` | Stop the service |
| `sudo systemctl restart erdpuls_ubec` | Restart the service |
| `sudo systemctl status erdpuls_ubec` | Check service status |
| `sudo systemctl enable erdpuls_ubec` | Enable auto-start on boot |
| `sudo systemctl disable erdpuls_ubec` | Disable auto-start |
| `sudo journalctl -u erdpuls_ubec -f` | View live logs |
| `sudo journalctl -u erdpuls_ubec -n 100` | View last 100 log lines |
| `sudo journalctl -u erdpuls_ubec --since today` | View today's logs |

## Migrating from `erdpuls-threshold` Service

If you're migrating from the old service name:

```bash
# 1. Stop old service
sudo systemctl stop erdpuls-threshold

# 2. Disable old service
sudo systemctl disable erdpuls-threshold

# 3. Install new service
sudo cp erdpuls_ubec.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable erdpuls_ubec
sudo systemctl start erdpuls_ubec

# 4. Remove old service file (optional)
sudo rm /etc/systemd/system/erdpuls-threshold.service
sudo systemctl daemon-reload
```

## Service Configuration Details

### Current Configuration

| Setting | Value |
|---------|-------|
| User | `kelpit` |
| Working Directory | `/home/kelpit/UBEC_ERDPULS` |
| Environment File | `/home/kelpit/UBEC_ERDPULS/.env` |
| Port | `8004` |
| Workers | `2` |

### Changing the Port

Edit the service file and modify the `--port` parameter:
```bash
sudo systemctl edit erdpuls_ubec --full
```

### Increasing Workers

For higher traffic, increase the `--workers` parameter in the service file.

## Troubleshooting

### Service won't start

1. **Check logs:**
   ```bash
   sudo journalctl -u erdpuls_ubec -n 50
   ```

2. **Test manually:**
   ```bash
   cd /home/kelpit/UBEC_ERDPULS
   source venv/bin/activate
   python -c "from app.main import app; print('OK')"
   ```

3. **Test uvicorn directly:**
   ```bash
   cd /home/kelpit/UBEC_ERDPULS
   venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8004
   ```

4. **Check environment file:**
   ```bash
   cat /home/kelpit/UBEC_ERDPULS/.env
   ```

### Database connection issues

```bash
# Test database connection
psql "postgresql://ubecpuls:<password>@localhost:5432/ubec_erdpuls" -c "SELECT 1"
```

### Port already in use

```bash
# Check what's using port 8004
sudo lsof -i :8004

# Kill the process if needed
sudo kill -9 <PID>
```

## Security Features

The service file includes security hardening options:

- **NoNewPrivileges=true** - Prevents privilege escalation
- **PrivateTmp=true** - Isolated /tmp directory

## Caddy Configuration

Ensure Caddy is configured to proxy to this service:

```caddyfile
erdpuls.ubec.network {
    reverse_proxy localhost:8004
    log {
        output file /var/log/caddy/erdpuls_access.log
    }
}
```

Reload Caddy after changes:
```bash
sudo systemctl reload caddy
```

## Test the Service

```bash
# Test locally
curl http://localhost:8004/health

# Test via domain (after Caddy is configured)
curl https://erdpuls.ubec.network/health
```

---

© Michel Garand | Lizenz: CC BY-SA 4.0 | https://creativecommons.org/licenses/by-sa/4.0/deed.de
