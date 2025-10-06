#!/bin/bash
set -e

echo "🚀 Starting TusaBot deployment..."

cd /opt/tusabot

if [ ! -d ".git" ]; then
    echo "Error: Not a git repository!"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "Error: .env file not found!"
    exit 1
fi

source .env

echo "📥 Pulling latest changes..."
git pull origin main

if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🗄️ Running database migrations..."
export PGPASSWORD="${DB_PASSWORD}"
psql -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} -f migrations/001_initial_schema.sql || true

echo "📦 Building web application..."
cd project
npm install -g serve
npm install
npm run build
cd ..

echo "⚙️ Installing systemd services..."
sudo cp systemd/tusabot.service /etc/systemd/system/
sudo cp systemd/tusabot-api.service /etc/systemd/system/
sudo cp systemd/tusabot-web.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable tusabot tusabot-api tusabot-web

echo "▶️ Restarting services..."
sudo systemctl restart tusabot tusabot-api tusabot-web

echo "🌐 Configuring Nginx..."
sudo cp nginx/tusabot.conf /etc/nginx/sites-available/tusabot
sudo ln -sf /etc/nginx/sites-available/tusabot /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

if sudo nginx -t; then
    sudo systemctl reload nginx
fi

echo "✅ Checking service status..."
sudo systemctl status tusabot --no-pager | head -10
sudo systemctl status tusabot-api --no-pager | head -10
sudo systemctl status tusabot-web --no-pager | head -10

echo "🎉 Deployment completed!"
echo "Web: http://5.129.250.86"
echo "API: http://5.129.250.86/health"