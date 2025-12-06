# Lululemon Wholesale Scraper

An automated web scraper for Lululemon wholesale catalog with a user-friendly web interface.

## Features

- 🔐 Secure login with Lululemon wholesale credentials
- 📊 Real-time scraping progress with user-friendly status updates
- 📧 Email notifications upon completion
- 📅 Scheduled scraping (daily, weekly, monthly)
- 📈 Scraping history and analytics
- 📥 Excel export with product images and details
- ⏸️ Start/stop scraping controls
- 🎨 Modern, responsive dashboard

## Technology Stack

- **Frontend**: Flask, Flask-SocketIO, HTML/CSS/JavaScript
- **Backend**: Python, Selenium, Playwright, BeautifulSoup4
- **Database**: SQLite
- **Automation**: Chromium, Chrome WebDriver

## Quick Start with Docker (Recommended)

### Prerequisites
- Docker & Docker Compose
- 4GB+ free disk space

### Installation

1. **Clone or download the project**
   ```bash
   cd /path/to/scrappin
   ```

2. **Build and start**
   ```bash
   docker-compose build
   docker-compose up -d
   ```

3. **Access the application**
   - Open `http://localhost:5000` in your browser
   - Log in with your admin credentials
   - Add your Lululemon wholesale credentials in Settings

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

## Manual Installation (Development)

### Prerequisites
- Python 3.10+
- Chrome browser
- Node.js (for Playwright)

### Backend Setup

1. **Install Python dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Install Playwright browsers**
   ```bash
   playwright install chromium
   ```

### Frontend Setup

1. **Install Python dependencies**
   ```bash
   cd frontend
   pip install -r requirements.txt
   ```

2. **Initialize database**
   ```bash
   python app.py
   ```
   The database will be created automatically at `frontend/instance/scraper.db`

3. **Add credentials** (via web interface or CLI)
   ```bash
   cd ../backend
   python add_credentials.py
   ```
   Or add them through Settings page after logging in.

### Running Locally

```bash
cd frontend
python app.py
```

Access at `http://localhost:5000`

## Usage

### Web Interface

1. **Login**: Use your admin credentials
2. **Add Credentials**: Go to Settings → Lululemon Credentials
3. **Start Scraping**: Click "Start Scraping" on dashboard
4. **Monitor Progress**: Watch real-time updates with user-friendly messages
5. **Download Results**: Excel file saved to `backend/data/results/`

### Features

#### Dashboard
- Start/stop scraping with one click
- Real-time progress bar with loading animation
- User-friendly status messages with emojis
- Quick access to latest Excel report

#### Settings
- **Credentials**: Manage Lululemon login
- **Email**: Configure SMTP for notifications
- **Schedule**: Set up automated scraping

#### History
- View all past scraping sessions
- Track success/failure rates
- Download archived reports
- Analyze scraping duration and products count

## Project Structure

```
scrappin/
├── backend/                    # Backend scraping logic
│   ├── data/                   # Scraped data storage
│   │   ├── results/            # Excel output files
│   │   ├── categories/         # Category HTML files
│   │   ├── men/                # Men's products
│   │   ├── women/              # Women's products
│   │   ├── accessories/        # Accessories products
│   │   └── supplies/           # Supplies products
│   ├── logs/                   # Application logs
│   ├── login_and_save_cookies.py       # Authentication
│   ├── extract_product_links.py        # Link extraction
│   ├── download_by_category.py         # Page downloading
│   ├── extract_to_excel.py             # Excel generation
│   ├── run_pipeline.py                 # Pipeline orchestration
│   └── db_credentials.py               # Database credential fetching
│
├── frontend/                   # Frontend web application
│   ├── instance/               # Database storage
│   ├── static/                 # CSS, JS, images
│   ├── templates/              # HTML templates
│   ├── app.py                  # Main Flask application
│   ├── auth.py                 # Authentication
│   ├── database.py             # Database models
│   └── email_service.py        # Email notifications
│
├── Dockerfile                  # Docker container config
├── docker-compose.yml          # Docker Compose config
├── DEPLOYMENT.md               # Deployment guide
└── README.md                   # This file
```

## Data Persistence

### Docker Volumes
- `frontend/instance/` - Database and user data
- `backend/data/` - Scraped HTML and Excel files
- `backend/logs/` - Application logs

### Output Files
- **Excel Reports**: `backend/data/results/all_products_YYYYMMDD_HHMMSS.xlsx`
- **Logs**: `backend/logs/scraper_YYYYMMDD_HHMMSS.log`

## Configuration

### Environment Variables

Create a `.env` file:
```bash
SECRET_KEY=your-super-secret-key-here
FLASK_ENV=production
```

### Database Models

- **User**: Admin accounts
- **LululemonCredentials**: Wholesale login credentials
- **ScrapingHistory**: Session tracking
- **Schedule**: Automated scraping jobs
- **EmailSettings**: SMTP configuration
- **EmailRecipient**: Notification recipients

## Security

- Passwords are hashed with Werkzeug
- Credentials stored in encrypted SQLite database
- Session management with Flask-Login
- CSRF protection (recommended: add Flask-WTF)
- Secret key for session encryption

## Troubleshooting

### Scraping Won't Start
- Check Lululemon credentials in Settings
- Verify Chrome/Chromium is installed
- Check logs: `backend/logs/scraper_*.log`

### Database Issues
- Ensure `frontend/instance/` directory exists
- Check file permissions
- Verify SQLite installation

### Docker Issues
- See [DEPLOYMENT.md](DEPLOYMENT.md) troubleshooting section
- Check logs: `docker-compose logs`
- Rebuild: `docker-compose build --no-cache`

## Development

### Adding New Features

1. **Backend**: Add scripts to `backend/` directory
2. **Frontend**: Update routes in `frontend/app.py`
3. **Database**: Add models to `frontend/database.py`
4. **UI**: Update templates in `frontend/templates/`

### Code Style
- Follow PEP 8 for Python
- Use meaningful variable names
- Comment complex logic
- Keep functions focused and small

## Roadmap

- [ ] Multi-user support with role-based access
- [ ] API for external integrations
- [ ] Advanced filtering and search
- [ ] Export to multiple formats (CSV, JSON)
- [ ] Webhooks for real-time notifications
- [ ] Dashboard analytics and charts

## License

Proprietary - All rights reserved

## Support

For issues or questions:
1. Check documentation: [DEPLOYMENT.md](DEPLOYMENT.md)
2. Review logs: `backend/logs/` or `docker-compose logs`
3. Verify configuration: Settings page
4. Contact system administrator

## Credits

Built with:
- [Flask](https://flask.palletsprojects.com/)
- [Selenium](https://www.selenium.dev/)
- [Playwright](https://playwright.dev/)
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)
- [OpenPyXL](https://openpyxl.readthedocs.io/)
