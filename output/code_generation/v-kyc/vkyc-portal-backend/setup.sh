#!/bin/bash

echo "🚀 Setting up VKYC Portal Backend..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ first."
    exit 1
fi

echo "✅ Node.js version: $(node --version)"

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

echo "✅ npm version: $(npm --version)"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env file with your actual configuration before starting the server."
else
    echo "✅ .env file already exists."
fi

# Create database directory if it doesn't exist
if [ ! -d database ]; then
    echo "📁 Creating database directory..."
    mkdir database
fi

# Initialize database
echo "🗄️  Initializing database..."
npm run init-db

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your SFTP server configuration"
echo "2. Run 'npm run dev' to start the development server"
echo "3. The server will be available at http://localhost:3001"
echo ""
echo "Default users:"
echo "- Username: leader1, Password: password (Team Leader)"
echo "- Username: manager1, Password: password (Process Manager)" 