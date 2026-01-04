# Deployment Guide for NearlyFreeSpeech

This guide covers deploying the Anti-Oedipus reader application to a standard Apache server on NearlyFreeSpeech.

## Prerequisites

- NearlyFreeSpeech account with SSH access
- Python 3.x installed on the server
- Apache with mod_wsgi enabled

## Server Setup

### 1. Upload Files

Upload all project files to your NearlyFreeSpeech server, excluding:
- `.env` file (create this on the server)
- `venv/` directory (create this on the server)
- `__pycache__/` directories
- `faiss_index.bin` and `faiss_metadata.pkl` (build these on the server, see Step 4)

### 2. Create Virtual Environment

SSH into your server and navigate to your project directory:

```bash
cd /path/to/your/project
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Create .env File

Create a `.env` file in the project root with your configuration:

```bash
nano .env
```

Add the following (replace with your actual values):

```env
OPENAI_API_KEY=sk-your-server-api-key-here
APP_PASSWORD=your-secure-password-here
FLASK_SECRET_KEY=generate-a-random-secret-key-here
FLASK_ENV=production
```

**Security Notes:**
- Never commit `.env` to git (already in `.gitignore`)
- Use a strong, random `FLASK_SECRET_KEY` (you can generate one with: `python -c "import secrets; print(secrets.token_hex(32))"`)
- Keep your `.env` file permissions restricted: `chmod 600 .env`

### 4. Build FAISS Index

Before running the application, you must build the FAISS index for the RAG system:

```bash
# Activate venv if not already active
source venv/bin/activate

# Build FAISS index (requires OPENAI_API_KEY in .env)
python build_faiss_index.py Anti-Oedipus.md

# Or with explicit API key:
python build_faiss_index.py Anti-Oedipus.md your-api-key-here
```

This creates:
- `faiss_index.bin`: Precomputed FAISS vector index (binary file, ~5-6 MB)
- `faiss_metadata.pkl`: Chunks and metadata (pickle file, ~8 MB)

**Note**: This step only needs to be run once (or when the markdown file changes). It may take a few minutes to generate embeddings.

### 5. Set File Permissions

```bash
# Make WSGI file executable
chmod 755 app.wsgi

# Restrict .env file permissions
chmod 600 .env

# Ensure project directory has correct ownership
chown -R your-username:your-group .
```

## Apache Configuration

### 1. Create Apache Virtual Host Configuration

Create or edit your Apache virtual host configuration file (typically in `/etc/apache2/sites-available/` or similar):

```apache
<VirtualHost *:80>
    ServerName your-domain.com
    ServerAlias www.your-domain.com
    
    # WSGI Configuration
    WSGIDaemonProcess anti-oedipus python-home=/path/to/your/project/venv python-path=/path/to/your/project
    WSGIProcessGroup anti-oedipus
    WSGIScriptAlias / /path/to/your/project/app.wsgi
    
    # Static files
    Alias /static /path/to/your/project/static
    <Directory /path/to/your/project/static>
        Require all granted
    </Directory>
    
    # Project directory
    <Directory /path/to/your/project>
        WSGIProcessGroup anti-oedipus
        WSGIApplicationGroup %{GLOBAL}
        Require all granted
    </Directory>
    
    # Logging
    ErrorLog ${APACHE_LOG_DIR}/anti-oedipus-error.log
    CustomLog ${APACHE_LOG_DIR}/anti-oedipus-access.log combined
</VirtualHost>
```

### 2. Enable mod_wsgi

```bash
sudo a2enmod wsgi
sudo systemctl restart apache2
```

### 3. Enable Your Site

```bash
sudo a2ensite your-site-config-file
sudo systemctl reload apache2
```

## SSL/HTTPS Setup (Recommended)

For production, you should use HTTPS. On NearlyFreeSpeech, you can use Let's Encrypt:

```bash
# Install certbot if not already installed
sudo apt-get install certbot python3-certbot-apache

# Obtain certificate
sudo certbot --apache -d your-domain.com -d www.your-domain.com
```

After SSL is set up, update your Apache config to redirect HTTP to HTTPS and ensure `FLASK_ENV=production` in your `.env` file (which enables secure cookies).

## Security Checklist

- [ ] `.env` file is not in git (check `.gitignore`)
- [ ] `.env` file has restricted permissions (`chmod 600`)
- [ ] `FLASK_SECRET_KEY` is set to a strong random value
- [ ] `FLASK_ENV=production` is set in `.env` (enables secure cookies)
- [ ] SSL/HTTPS is configured
- [ ] Apache is configured to serve static files efficiently
- [ ] Log files are monitored for security issues

## Troubleshooting

### Check Apache Error Logs

```bash
sudo tail -f /var/log/apache2/anti-oedipus-error.log
```

### Check WSGI Process

```bash
ps aux | grep wsgi
```

### Test WSGI File Directly

```bash
cd /path/to/your/project
source venv/bin/activate
python app.wsgi
```

### Common Issues

1. **Import Errors**: Ensure virtual environment is activated and all dependencies are installed
2. **Permission Errors**: Check file ownership and permissions
3. **Module Not Found**: Verify Python path in Apache configuration
4. **Session Issues**: Ensure `FLASK_SECRET_KEY` is set and cookies are working

## Maintenance

### Updating the Application

1. Pull latest changes from git
2. Activate virtual environment: `source venv/bin/activate`
3. Update dependencies if needed: `pip install -r requirements.txt`
4. Restart Apache: `sudo systemctl restart apache2`

### Monitoring

- Monitor error logs regularly
- Check disk space (FAISS index files are ~13-14 MB total)
- Monitor API usage if using server API key
- Rebuild FAISS index if `Anti-Oedipus.md` is updated

