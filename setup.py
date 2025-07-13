#!/usr/bin/env python3
"""
Setup script for Test Execution System
Initializes database, creates directories, and sets up the system
"""

import os
import sys
import subprocess
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging
from config import get_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        'psycopg2-binary',
        'fastapi',
        'uvicorn',
        'GitPython',
        'requests',
        'pydantic'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Missing required packages: {', '.join(missing_packages)}")
        print("Please install them using: pip install -r requirements.txt")
        return False
    
    return True

def check_external_tools():
    """Check if external test tools are installed"""
    tools = {
        'pytest': 'pip install pytest pytest-json-report',
        'cucumber': 'gem install cucumber',
        'robot': 'pip install robotframework'
    }
    
    missing_tools = []
    for tool, install_cmd in tools.items():
        try:
            subprocess.run([tool, '--version'], 
                         capture_output=True, 
                         check=True)
            print(f"✓ {tool} is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_tools.append((tool, install_cmd))
            print(f"✗ {tool} is not installed")
    
    if missing_tools:
        print("\nMissing test tools:")
        for tool, cmd in missing_tools:
            print(f"  {tool}: {cmd}")
        return False
    
    return True

def create_database():
    """Create database if it doesn't exist"""
    config = get_config()
    db_config = config.DB_CONFIG
    
    try:
        # Connect to PostgreSQL server (not the database)
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_config['database'],)
        )
        
        if cursor.fetchone():
            print(f"✓ Database '{db_config['database']}' already exists")
        else:
            # Create database
            cursor.execute(f"CREATE DATABASE {db_config['database']}")
            print(f"✓ Created database '{db_config['database']}'")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"✗ Database creation failed: {e}")
        return False

def initialize_database():
    """Initialize database with schema"""
    config = get_config()
    db_config = config.DB_CONFIG
    
    try:
        # Connect to the application database
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Read and execute schema
        with open('database_schema.sql', 'r') as f:
            schema_sql = f.read()
        
        cursor.execute(schema_sql)
        conn.commit()
        
        print("✓ Database schema initialized")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"✗ Database initialization failed: {e}")
        return False
    except FileNotFoundError:
        print("✗ database_schema.sql file not found")
        return False

def create_directories():
    """Create necessary directories"""
    config = get_config()
    config.create_directories()
    return True

def create_environment_file():
    """Create .env file template"""
    env_content = """# Test Execution System Environment Variables

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=test_execution_db
DB_USER=postgres
DB_PASSWORD=password

# GitHub Integration (Optional)
GITHUB_TOKEN=your_github_token_here

# File System Paths
WORKSPACE_DIR=/tmp/test_workspaces
LOG_DIR=/tmp/test_logs
REPORTS_DIR=/tmp/test_reports

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=false

# Security
SECRET_KEY=your-secret-key-change-this-in-production
CORS_ORIGINS=*

# Test Execution Settings
MAX_CONCURRENT_EXECUTIONS=5
EXECUTION_TIMEOUT=3600

# Logging
LOG_LEVEL=INFO

# Email Notifications (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_password
NOTIFICATION_EMAILS=admin@example.com,team@example.com

# Environment
ENVIRONMENT=development
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✓ Created .env file template")
        print("  Please update the values in .env file before running the application")
    else:
        print("✓ .env file already exists")
    
    return True

def create_systemd_service():
    """Create systemd service file for production deployment"""
    service_content = """[Unit]
Description=Test Execution System
After=network.target
Requires=postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/test-execution-system
Environment=PATH=/opt/test-execution-system/venv/bin
EnvironmentFile=/opt/test-execution-system/.env
ExecStart=/opt/test-execution-system/venv/bin/python api_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    if not os.path.exists('test-execution-system.service'):
        with open('test-execution-system.service', 'w') as f:
            f.write(service_content)
        print("✓ Created systemd service file")
        print("  Copy to /etc/systemd/system/ for production deployment")
    else:
        print("✓ systemd service file already exists")
    
    return True

def create_docker_files():
    """Create Docker configuration files"""
    
    # Dockerfile
    dockerfile_content = """FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    git \\
    curl \\
    postgresql-client \\
    && rm -rf /var/lib/apt/lists/*

# Install test frameworks
RUN pip install pytest pytest-json-report robotframework

# Install Ruby and Cucumber (if needed)
RUN apt-get update && apt-get install -y ruby ruby-dev build-essential \\
    && gem install cucumber \\
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /tmp/test_workspaces /tmp/test_logs /tmp/test_reports

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "api_server.py"]
"""
    
    # Docker Compose
    docker_compose_content = """version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: test_execution_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database_schema.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 30s
      timeout: 10s
      retries: 5

  web:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    environment:
      - DB_HOST=db
      - DB_PORT=5432
      - DB_NAME=test_execution_db
      - DB_USER=postgres
      - DB_PASSWORD=password
      - WORKSPACE_DIR=/tmp/test_workspaces
      - LOG_DIR=/tmp/test_logs
      - REPORTS_DIR=/tmp/test_reports
    volumes:
      - ./web:/app/web
      - test_workspaces:/tmp/test_workspaces
      - test_logs:/tmp/test_logs
      - test_reports:/tmp/test_reports
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./web:/usr/share/nginx/html
    depends_on:
      - web
    restart: unless-stopped

volumes:
  postgres_data:
  test_workspaces:
  test_logs:
  test_reports:
"""
    
    # Nginx configuration
    nginx_content = """events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    upstream api {
        server web:8000;
    }
    
    server {
        listen 80;
        server_name localhost;
        
        # Serve static files
        location / {
            root /usr/share/nginx/html;
            index index.html;
            try_files $uri $uri/ /index.html;
        }
        
        # Proxy API requests
        location /api/ {
            proxy_pass http://api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # WebSocket support for log streaming
        location /ws/ {
            proxy_pass http://api/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }
    }
}
"""
    
    files = {
        'Dockerfile': dockerfile_content,
        'docker-compose.yml': docker_compose_content,
        'nginx.conf': nginx_content
    }
    
    for filename, content in files.items():
        if not os.path.exists(filename):
            with open(filename, 'w') as f:
                f.write(content)
            print(f"✓ Created {filename}")
        else:
            print(f"✓ {filename} already exists")
    
    return True

def create_startup_script():
    """Create startup script"""
    startup_content = """#!/bin/bash

# Test Execution System Startup Script

echo "Starting Test Execution System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | xargs)
fi

# Create directories
python3 -c "from config import get_config; get_config().create_directories()"

# Start the application
echo "Starting API server..."
python3 api_server.py
"""
    
    if not os.path.exists('start.sh'):
        with open('start.sh', 'w') as f:
            f.write(startup_content)
        os.chmod('start.sh', 0o755)
        print("✓ Created start.sh script")
    else:
        print("✓ start.sh script already exists")
    
    return True

def main():
    """Main setup function"""
    print("=" * 50)
    print("Test Execution System Setup")
    print("=" * 50)
    
    # Check dependencies
    print("\n1. Checking dependencies...")
    if not check_dependencies():
        sys.exit(1)
    
    # Check external tools
    print("\n2. Checking external test tools...")
    if not check_external_tools():
        print("Warning: Some test tools are missing. Install them to use all features.")
    
    # Create database
    print("\n3. Setting up database...")
    if not create_database():
        sys.exit(1)
    
    if not initialize_database():
        sys.exit(1)
    
    # Create directories
    print("\n4. Creating directories...")
    if not create_directories():
        sys.exit(1)
    
    # Create configuration files
    print("\n5. Creating configuration files...")
    if not create_environment_file():
        sys.exit(1)
    
    if not create_systemd_service():
        sys.exit(1)
    
    if not create_docker_files():
        sys.exit(1)
    
    if not create_startup_script():
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("Setup completed successfully!")
    print("=" * 50)
    
    print("\nNext steps:")
    print("1. Update the .env file with your configuration")
    print("2. Run the application:")
    print("   - Development: python api_server.py")
    print("   - Production: ./start.sh")
    print("   - Docker: docker-compose up -d")
    print("3. Open http://localhost:8000 in your browser")
    print("4. Check the web interface at web/index.html")
    
    print("\nDocumentation:")
    print("- API docs: http://localhost:8000/docs")
    print("- Web interface: http://localhost:8000")
    print("- Logs: Check the LOG_DIR directory")

if __name__ == "__main__":
    main() 