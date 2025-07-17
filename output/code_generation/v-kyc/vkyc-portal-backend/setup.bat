@echo off
echo 🚀 Setting up VKYC Portal Backend...

REM Check if Node.js is installed
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js is not installed. Please install Node.js 16+ first.
    pause
    exit /b 1
)

echo ✅ Node.js version: 
node --version

REM Check if npm is installed
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ npm is not installed. Please install npm first.
    pause
    exit /b 1
)

echo ✅ npm version:
npm --version

REM Install dependencies
echo 📦 Installing dependencies...
npm install

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file from template...
    copy env.example .env
    echo ⚠️  Please edit .env file with your actual configuration before starting the server.
) else (
    echo ✅ .env file already exists.
)

REM Create database directory if it doesn't exist
if not exist database (
    echo 📁 Creating database directory...
    mkdir database
)

REM Initialize database
echo 🗄️  Initializing database...
npm run init-db

echo.
echo 🎉 Setup completed successfully!
echo.
echo Next steps:
echo 1. Edit .env file with your SFTP server configuration
echo 2. Run 'npm run dev' to start the development server
echo 3. The server will be available at http://localhost:3001
echo.
echo Default users:
echo - Username: leader1, Password: password (Team Leader)
echo - Username: manager1, Password: password (Process Manager)
echo.
pause 