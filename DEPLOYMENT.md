# Lululemon Wholesale Scraper - Docker Deployment Guide

## Quick Start

### Prerequisites
- Docker Engine 20.10 or higher
- Docker Compose 2.0 or higher
- At least 4GB of free disk space
- Internet connection for pulling images

### 1. Clone/Upload Project
Upload the entire project folder to your server or ensure you're in the project directory:
```bash
cd /path/to/scrappin
```

### 2. Configure Environment (Optional)
Create a `.env` file in the root directory for custom configuration:
```bash
SECRET_KEY=your-super-secret-key-here-change-this-in-production
FLASK_ENV=production
```

**Note:** If you don't create a `.env` file, default values from `docker-compose.yml` will be used.

### 3. Build and Start
```bash
# Build the Docker image
docker-compose build

# Start the container
docker-compose up -d
```

The application will be available at `http://localhost:5000`

### 4. Initial Setup
On first run, you'll need to:
1. Open `http://localhost:5000` in your browser
2. Log in with your credentials
3. Go to Settings → Credentials
4. Add your Lululemon wholesale credentials

**Note:** The credentials are stored in the database (`frontend/instance/scraper.db`) which is persisted via Docker volume.

## Management Commands

### View Logs
```bash
# Follow logs in real-time
docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100
```

### Stop Application
```bash
docker-compose down
```

### Restart Application
```bash
docker-compose restart
```

### Update Application
```bash
# Pull latest changes
git pull  # or upload new files

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

## Data Persistence

The following directories are persisted via Docker volumes:

- **`frontend/instance/`** - SQLite database (users, settings, history)
- **`backend/data/`** - Scraped HTML files and Excel reports
- **`backend/logs/`** - Application logs

These directories will survive container restarts and rebuilds.

## Accessing the Application

### Default Port
- Application: `http://localhost:5000`

### Change Port
Edit `docker-compose.yml`:
```yaml
ports:
  - "8080:5000"  # Change 8080 to your desired port
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

## Production Deployment

### Security Best Practices

1. **Change SECRET_KEY**: Never use the default secret key in production
   ```bash
   # Generate a secure random key
   python3 -c 'import secrets; print(secrets.token_hex(32))'
   ```
   Add to `.env` file or set in `docker-compose.yml`

2. **Use HTTPS**: Put application behind a reverse proxy (Nginx/Caddy)

3. **Firewall Rules**: Only expose necessary ports

4. **Regular Backups**: Backup the volumes regularly
   ```bash
   # Backup database
   docker cp lululemon-scraper:/app/frontend/instance/scraper.db ./backup_$(date +%Y%m%d).db
   ```

### Reverse Proxy Example (Nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for real-time updates
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs for errors
docker-compose logs

# Verify Docker is running
docker ps
```

### Database Issues
```bash
# Access container shell
docker exec -it lululemon-scraper bash

# Check database file
ls -la /app/frontend/instance/scraper.db
```

### Permission Issues
```bash
# Fix volume permissions
sudo chown -R $USER:$USER frontend/instance backend/data backend/logs
```

### Out of Disk Space
```bash
# Clean up old data
docker system prune -a

# Remove old Excel files
rm -rf backend/data/results/*.xlsx

# Remove old HTML files
rm -rf backend/data/men/*.html backend/data/women/*.html
```

### Chrome/Playwright Issues
```bash
# Rebuild without cache
docker-compose build --no-cache
```

## Development Mode

To run in development mode with live code changes:

1. Modify `docker-compose.yml`:
```yaml
volumes:
  - ./frontend:/app/frontend
  - ./backend:/app/backend
environment:
  - FLASK_ENV=development
```

2. Restart:
```bash
docker-compose down
docker-compose up
```

## Resource Limits

To limit container resources, add to `docker-compose.yml`:

```yaml
services:
  lululemon-scraper:
    # ... existing config ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## Health Monitoring

The container includes a health check that runs every 30 seconds. Check status:

```bash
docker inspect lululemon-scraper | grep -A 10 "Health"
```

## Support

For issues or questions:
1. Check logs: `docker-compose logs`
2. Verify database exists: `ls -la frontend/instance/`
3. Ensure ports are not in use: `netstat -tulpn | grep 5000`
4. Rebuild from scratch: `docker-compose down -v && docker-compose build --no-cache && docker-compose up -d`
