import os
from typing import Dict, Any

class Config:
    """Configuration settings for the Test Execution System"""
    
    # Database configuration
    DB_CONFIG = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "database": os.getenv("DB_NAME", "test_execution_db"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "password")
    }
    
    # GitHub integration
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    
    # File system paths
    WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", "/tmp/test_workspaces")
    LOG_DIR = os.getenv("LOG_DIR", "/tmp/test_logs")
    REPORTS_DIR = os.getenv("REPORTS_DIR", "/tmp/test_reports")
    
    # Server configuration
    SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Test execution settings
    MAX_CONCURRENT_EXECUTIONS = int(os.getenv("MAX_CONCURRENT_EXECUTIONS", "5"))
    EXECUTION_TIMEOUT = int(os.getenv("EXECUTION_TIMEOUT", "3600"))  # 1 hour
    
    # Framework specific settings
    PYTEST_DEFAULT_ARGS = [
        "--tb=short",
        "--junitxml={output_dir}/pytest_results.xml",
        "--json-report={output_dir}/pytest_results.json",
        "-v"
    ]
    
    CUCUMBER_DEFAULT_ARGS = [
        "--format", "json",
        "--out", "{output_dir}/cucumber_results.json",
        "--format", "pretty"
    ]
    
    ROBOT_DEFAULT_ARGS = [
        "--outputdir", "{output_dir}",
        "--output", "robot_output.xml",
        "--log", "robot_log.html",
        "--report", "robot_report.html"
    ]
    
    # Logging configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Email notifications (optional)
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    NOTIFICATION_EMAILS = os.getenv("NOTIFICATION_EMAILS", "").split(",")
    
    # Redis configuration (for future caching/queuing)
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    
    @classmethod
    def get_framework_config(cls, framework_name: str) -> Dict[str, Any]:
        """Get configuration for a specific framework"""
        configs = {
            "pytest": {
                "default_args": cls.PYTEST_DEFAULT_ARGS,
                "file_patterns": ["test_*.py", "*_test.py"],
                "command_template": "pytest {test_path} {args}"
            },
            "cucumber": {
                "default_args": cls.CUCUMBER_DEFAULT_ARGS,
                "file_patterns": ["*.feature"],
                "command_template": "cucumber {test_path} {args}"
            },
            "robot": {
                "default_args": cls.ROBOT_DEFAULT_ARGS,
                "file_patterns": ["*.robot", "*.txt"],
                "command_template": "robot {args} {test_path}"
            }
        }
        return configs.get(framework_name, {})
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration settings"""
        required_vars = [
            "DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"Missing required environment variables: {', '.join(missing_vars)}")
            return False
        
        return True
    
    @classmethod
    def create_directories(cls):
        """Create necessary directories"""
        directories = [
            cls.WORKSPACE_DIR,
            cls.LOG_DIR,
            cls.REPORTS_DIR
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")

# Environment-specific configurations
class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = "DEBUG"

class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = "INFO"
    
class TestingConfig(Config):
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    DB_CONFIG = {
        "host": "localhost",
        "port": 5432,
        "database": "test_execution_test_db",
        "user": "postgres",
        "password": "password"
    }

# Get configuration based on environment
def get_config():
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionConfig
    elif env == "testing":
        return TestingConfig
    else:
        return DevelopmentConfig 