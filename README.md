<<<<<<< HEAD
# Test Execution System

A comprehensive multi-framework test execution system that supports **Cucumber**, **pytest**, and **Robot Framework** with centralized logging, database storage, and web-based management interface.

## 🚀 Features

### Multi-Framework Support
- **pytest** - Python testing framework
- **Cucumber** - Behavior-driven development
- **Robot Framework** - Generic automation framework

### Core Capabilities
- ✅ **Automated Test Execution** - Run tests from local directories or GitHub repositories
- ✅ **Real-time Logging** - Stream logs in real-time with different log levels
- ✅ **Database Storage** - Store all execution results, logs, and metrics
- ✅ **Web Interface** - Modern dashboard for test management
- ✅ **REST API** - Complete API for integration with CI/CD pipelines
- ✅ **GitHub Integration** - Clone and run tests from GitHub repositories
- ✅ **Concurrent Execution** - Run multiple test suites simultaneously
- ✅ **Detailed Reporting** - Generate comprehensive test reports

### Advanced Features
- 🔄 **Auto-detection** - Automatically detect test frameworks in projects
- 📊 **Statistics Dashboard** - View execution metrics and trends
- 🔍 **Log Analysis** - Parse and categorize logs by type and level
- 📱 **Responsive UI** - Modern, mobile-friendly web interface
- 🐳 **Docker Support** - Easy deployment with Docker containers
- 🔐 **Security** - Built-in authentication and authorization

## 📋 Architecture

The system follows a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web Interface                            │
├─────────────────────────────────────────────────────────────────┤
│                        REST API Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  Test Execution Engine  │  GitHub Integration  │  Log Manager  │
├─────────────────────────────────────────────────────────────────┤
│                     Database Layer                              │
└─────────────────────────────────────────────────────────────────┘
```

### Components

1. **Test Execution Engine** (`test_executor.py`)
   - Manages test execution lifecycle
   - Supports pytest, Cucumber, and Robot Framework
   - Handles concurrent executions
   - Parses test results and generates reports

2. **GitHub Integration** (`github_integration.py`)
   - Clones repositories from GitHub
   - Detects test frameworks automatically
   - Manages project workspaces
   - Handles authentication with GitHub API

3. **API Server** (`api_server.py`)
   - FastAPI-based REST API
   - Handles project management
   - Manages test executions
   - Provides real-time log streaming

4. **Web Interface** (`web/`)
   - Modern HTML/CSS/JavaScript interface
   - Dashboard with execution statistics
   - Real-time log viewing
   - Project and execution management

5. **Database Layer** (`database_schema.sql`)
   - PostgreSQL schema
   - Stores projects, executions, logs, and results
   - Optimized for performance with proper indexing

## 🛠️ Installation

### Prerequisites
- Python 3.11+
- PostgreSQL 12+
- Git
- Node.js (for Cucumber, if using)
- Ruby (for Cucumber, if using)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd test-execution-system
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run setup script**
   ```bash
   python setup.py
   ```

4. **Configure environment**
   ```bash
   # Edit .env file with your settings
   nano .env
   ```

5. **Start the application**
   ```bash
   # Development
   python api_server.py
   
   # Production
   ./start.sh
   ```

### Docker Deployment

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f web
```

## 📖 Usage

### Web Interface

1. Open `http://localhost:8000` in your browser
2. Navigate through the dashboard to:
   - Create and manage projects
   - Start test executions
   - View real-time logs
   - Monitor execution statistics

### API Usage

#### Create a Project
```bash
curl -X POST "http://localhost:8000/projects" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Test Project",
    "description": "Sample project description",
    "source_type": "github",
    "source_url": "https://github.com/user/repo"
  }'
```

#### Start Test Execution
```bash
curl -X POST "http://localhost:8000/executions" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "framework_name": "pytest",
    "execution_name": "Smoke Tests",
    "test_path": "tests/",
    "additional_args": ["-v", "--tb=short"]
  }'
```

#### Get Execution Status
```bash
curl "http://localhost:8000/executions/1"
```

#### Get Execution Logs
```bash
curl "http://localhost:8000/executions/1/logs"
```

### Framework-Specific Usage

#### pytest
```bash
# Project structure
project/
├── tests/
│   ├── test_example.py
│   ├── test_api.py
│   └── conftest.py
├── pytest.ini
└── requirements.txt
```

#### Cucumber
```bash
# Project structure
project/
├── features/
│   ├── example.feature
│   └── step_definitions/
│       └── steps.rb
├── cucumber.yml
└── Gemfile
```

#### Robot Framework
```bash
# Project structure
project/
├── robot_tests/
│   ├── example.robot
│   ├── keywords.robot
│   └── variables.robot
├── robot.cfg
└── requirements.txt
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | localhost | Database host |
| `DB_PORT` | 5432 | Database port |
| `DB_NAME` | test_execution_db | Database name |
| `DB_USER` | postgres | Database user |
| `DB_PASSWORD` | password | Database password |
| `GITHUB_TOKEN` | - | GitHub API token |
| `WORKSPACE_DIR` | /tmp/test_workspaces | Project workspace directory |
| `LOG_DIR` | /tmp/test_logs | Log storage directory |
| `REPORTS_DIR` | /tmp/test_reports | Report storage directory |
| `SERVER_HOST` | 0.0.0.0 | API server host |
| `SERVER_PORT` | 8000 | API server port |
| `MAX_CONCURRENT_EXECUTIONS` | 5 | Maximum concurrent executions |
| `EXECUTION_TIMEOUT` | 3600 | Execution timeout (seconds) |

### Database Schema

The system uses PostgreSQL with the following main tables:

- `projects` - Project information
- `frameworks` - Available test frameworks
- `test_executions` - Test execution records
- `test_logs` - Execution logs
- `test_results` - Individual test results
- `test_artifacts` - Generated artifacts (reports, screenshots)

## 📊 API Reference

### Endpoints

#### Projects
- `GET /projects` - List all projects
- `POST /projects` - Create a new project
- `GET /projects/{id}` - Get project details
- `DELETE /projects/{id}` - Delete a project
- `POST /projects/{id}/analyze` - Analyze project for test frameworks

#### Executions
- `GET /executions` - List test executions
- `POST /executions` - Start a new execution
- `GET /executions/{id}` - Get execution details
- `POST /executions/{id}/cancel` - Cancel execution
- `GET /executions/{id}/logs` - Get execution logs
- `GET /executions/{id}/results` - Get test results

#### Frameworks
- `GET /frameworks` - List available frameworks

#### Statistics
- `GET /statistics/dashboard` - Get dashboard statistics

### Response Format

```json
{
  "id": 1,
  "execution_name": "Smoke Tests",
  "framework_name": "pytest",
  "status": "completed",
  "start_time": "2024-01-01T10:00:00Z",
  "end_time": "2024-01-01T10:05:00Z",
  "duration_seconds": 300,
  "total_tests": 25,
  "passed_tests": 23,
  "failed_tests": 2,
  "skipped_tests": 0
}
```

## 🚀 Deployment

### Development
```bash
# Start development server
python api_server.py

# Access at http://localhost:8000
```

### Production with Docker
```bash
# Build and start
docker-compose up -d

# Scale services
docker-compose up -d --scale web=3

# View logs
docker-compose logs -f
```

### Production with systemd
```bash
# Copy service file
sudo cp test-execution-system.service /etc/systemd/system/

# Enable and start
sudo systemctl enable test-execution-system
sudo systemctl start test-execution-system

# Check status
sudo systemctl status test-execution-system
```

## 🔍 Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Logs
```bash
# Application logs
tail -f /tmp/test_logs/app.log

# Database logs
docker-compose logs -f db

# Web server logs
docker-compose logs -f web
```

### Metrics
The system provides built-in metrics through the statistics endpoint:
- Total executions
- Success/failure rates
- Average execution duration
- Framework usage statistics

## 🔒 Security

### Authentication
- API key authentication
- JWT token support
- Role-based access control

### Network Security
- CORS configuration
- Rate limiting
- Input validation

### Data Protection
- Database encryption
- Secure credential storage
- Audit logging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Development Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run linting
flake8 .
black .
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support, please:
1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed information
4. Contact the development team

## 🗺️ Roadmap

### Version 2.0
- [ ] Kubernetes deployment support
- [ ] Advanced scheduling features
- [ ] Notification system (email, Slack)
- [ ] Advanced reporting and analytics
- [ ] Plugin system for custom frameworks
- [ ] CI/CD pipeline integration templates

### Version 2.1
- [ ] Performance optimizations
- [ ] Enhanced security features
- [ ] Mobile app
- [ ] Advanced user management
- [ ] Test result comparison
- [ ] Automated test discovery

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- PostgreSQL for reliable database storage
- Bootstrap for the UI components
- All the testing framework maintainers

---

**Built with ❤️ for the testing community** 
