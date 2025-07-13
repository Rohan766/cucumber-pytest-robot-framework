from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import os
import json
import tempfile
import shutil
from datetime import datetime
import logging

# Import our custom modules
from test_executor import TestExecutionManager, TestStatus
from github_integration import GitHubIntegration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Test Execution System",
    description="Multi-framework test execution system supporting Cucumber, pytest, and Robot Framework",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "test_execution_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "password")
}

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", "/tmp/test_workspaces")

# Initialize managers
execution_manager = TestExecutionManager(DB_CONFIG)
github_integration = GitHubIntegration(GITHUB_TOKEN)

# Pydantic models
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    source_type: str  # "local" or "github"
    source_url: Optional[str] = None
    local_path: Optional[str] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    source_type: str
    source_url: Optional[str]
    local_path: Optional[str]
    created_at: datetime
    updated_at: datetime

class ExecutionRequest(BaseModel):
    project_id: int
    framework_name: str
    execution_name: str
    test_path: Optional[str] = None
    additional_args: Optional[List[str]] = None

class ExecutionResponse(BaseModel):
    id: int
    project_id: int
    framework_name: str
    execution_name: str
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    exit_code: Optional[int]

class LogEntry(BaseModel):
    id: int
    execution_id: int
    log_type: str
    log_level: str
    message: str
    timestamp: datetime
    file_path: Optional[str]
    line_number: Optional[int]
    test_case: Optional[str]

# Create workspace directory
os.makedirs(WORKSPACE_DIR, exist_ok=True)

# API Endpoints

@app.get("/")
async def root():
    return {"message": "Test Execution System API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

# Project Management Endpoints

@app.post("/projects", response_model=ProjectResponse)
async def create_project(project: ProjectCreate):
    """Create a new project"""
    try:
        # Validate project data
        if project.source_type == "github" and not project.source_url:
            raise HTTPException(status_code=400, detail="GitHub URL is required for GitHub projects")
        
        if project.source_type == "local" and not project.local_path:
            raise HTTPException(status_code=400, detail="Local path is required for local projects")
        
        # For GitHub projects, validate the repository
        if project.source_type == "github":
            if not github_integration.validate_repo_url(project.source_url):
                raise HTTPException(status_code=400, detail="Invalid or inaccessible GitHub repository")
        
        # Insert project into database
        if not execution_manager.db_manager.connect():
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        query = """
            INSERT INTO projects (name, description, source_type, source_url, local_path)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, name, description, source_type, source_url, local_path, created_at, updated_at
        """
        params = (project.name, project.description, project.source_type, 
                 project.source_url, project.local_path)
        
        result = execution_manager.db_manager.execute_query(query, params)
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create project")
        
        return ProjectResponse(**dict(result))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        execution_manager.db_manager.disconnect()

@app.get("/projects", response_model=List[ProjectResponse])
async def list_projects():
    """List all projects"""
    try:
        if not execution_manager.db_manager.connect():
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        query = "SELECT * FROM projects ORDER BY created_at DESC"
        results = execution_manager.db_manager.execute_query(query, fetch=True)
        
        return [ProjectResponse(**dict(row)) for row in results] if results else []
        
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        execution_manager.db_manager.disconnect()

@app.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int):
    """Get a specific project"""
    try:
        if not execution_manager.db_manager.connect():
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        query = "SELECT * FROM projects WHERE id = %s"
        result = execution_manager.db_manager.execute_query(query, (project_id,), fetch=True)
        
        if not result:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return ProjectResponse(**dict(result[0]))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        execution_manager.db_manager.disconnect()

@app.delete("/projects/{project_id}")
async def delete_project(project_id: int):
    """Delete a project"""
    try:
        if not execution_manager.db_manager.connect():
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        # Check if project exists
        check_query = "SELECT * FROM projects WHERE id = %s"
        result = execution_manager.db_manager.execute_query(check_query, (project_id,), fetch=True)
        
        if not result:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Delete project
        delete_query = "DELETE FROM projects WHERE id = %s"
        execution_manager.db_manager.execute_query(delete_query, (project_id,))
        
        return {"message": "Project deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        execution_manager.db_manager.disconnect()

# Project Analysis Endpoints

@app.post("/projects/{project_id}/analyze")
async def analyze_project(project_id: int):
    """Analyze a project to detect test frameworks and test directories"""
    try:
        if not execution_manager.db_manager.connect():
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        # Get project details
        query = "SELECT * FROM projects WHERE id = %s"
        result = execution_manager.db_manager.execute_query(query, (project_id,), fetch=True)
        
        if not result:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project = dict(result[0])
        workspace_path = os.path.join(WORKSPACE_DIR, f"project_{project_id}")
        
        # Prepare project workspace
        if project["source_type"] == "github":
            # Clone repository
            if not github_integration.clone_repository(project["source_url"], workspace_path):
                raise HTTPException(status_code=500, detail="Failed to clone repository")
        elif project["source_type"] == "local":
            # Copy local files to workspace
            if os.path.exists(project["local_path"]):
                shutil.copytree(project["local_path"], workspace_path, dirs_exist_ok=True)
            else:
                raise HTTPException(status_code=400, detail="Local path does not exist")
        
        # Analyze project
        frameworks = github_integration.detect_test_frameworks(workspace_path)
        test_directories = github_integration.get_test_directories(workspace_path)
        
        # Get repository info (for GitHub projects)
        repo_info = {}
        if project["source_type"] == "github":
            repo_info = github_integration.get_repository_info(project["source_url"])
        
        return {
            "project_id": project_id,
            "detected_frameworks": frameworks,
            "test_directories": test_directories,
            "repository_info": repo_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing project: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        execution_manager.db_manager.disconnect()

# Test Execution Endpoints

@app.post("/executions", response_model=Dict[str, Any])
async def start_execution(execution_request: ExecutionRequest):
    """Start a new test execution"""
    try:
        if not execution_manager.db_manager.connect():
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        # Get project details
        query = "SELECT * FROM projects WHERE id = %s"
        result = execution_manager.db_manager.execute_query(query, (execution_request.project_id,), fetch=True)
        
        if not result:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project = dict(result[0])
        workspace_path = os.path.join(WORKSPACE_DIR, f"project_{execution_request.project_id}")
        
        # Prepare project workspace
        if project["source_type"] == "github":
            # Clone or update repository
            if os.path.exists(workspace_path):
                github_integration.pull_latest_changes(workspace_path)
            else:
                if not github_integration.clone_repository(project["source_url"], workspace_path):
                    raise HTTPException(status_code=500, detail="Failed to clone repository")
        elif project["source_type"] == "local":
            # Copy local files to workspace
            if os.path.exists(project["local_path"]):
                shutil.copytree(project["local_path"], workspace_path, dirs_exist_ok=True)
            else:
                raise HTTPException(status_code=400, detail="Local path does not exist")
        
        # Determine test path
        test_path = workspace_path
        if execution_request.test_path:
            test_path = os.path.join(workspace_path, execution_request.test_path)
        
        # Start execution
        execution_id = execution_manager.start_execution(
            project_id=execution_request.project_id,
            framework_name=execution_request.framework_name,
            execution_name=execution_request.execution_name,
            project_path=test_path,
            additional_args=execution_request.additional_args
        )
        
        return {
            "execution_id": execution_id,
            "message": "Test execution started successfully",
            "status": "running"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting execution: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        execution_manager.db_manager.disconnect()

@app.get("/executions", response_model=List[ExecutionResponse])
async def list_executions(project_id: Optional[int] = None, limit: int = 50):
    """List test executions"""
    try:
        if not execution_manager.db_manager.connect():
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        if project_id:
            query = """
                SELECT te.*, f.name as framework_name 
                FROM test_executions te
                JOIN frameworks f ON te.framework_id = f.id
                WHERE te.project_id = %s
                ORDER BY te.start_time DESC
                LIMIT %s
            """
            params = (project_id, limit)
        else:
            query = """
                SELECT te.*, f.name as framework_name 
                FROM test_executions te
                JOIN frameworks f ON te.framework_id = f.id
                ORDER BY te.start_time DESC
                LIMIT %s
            """
            params = (limit,)
        
        results = execution_manager.db_manager.execute_query(query, params, fetch=True)
        
        executions = []
        for row in results:
            execution = dict(row)
            executions.append(ExecutionResponse(
                id=execution["id"],
                project_id=execution["project_id"],
                framework_name=execution["framework_name"],
                execution_name=execution["execution_name"],
                status=execution["status"],
                start_time=execution["start_time"],
                end_time=execution["end_time"],
                duration_seconds=execution["duration_seconds"],
                total_tests=execution["total_tests"],
                passed_tests=execution["passed_tests"],
                failed_tests=execution["failed_tests"],
                skipped_tests=execution["skipped_tests"],
                exit_code=execution["exit_code"]
            ))
        
        return executions
        
    except Exception as e:
        logger.error(f"Error listing executions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        execution_manager.db_manager.disconnect()

@app.get("/executions/{execution_id}", response_model=ExecutionResponse)
async def get_execution(execution_id: int):
    """Get a specific execution"""
    try:
        execution_data = execution_manager.get_execution_status(execution_id)
        
        if "error" in execution_data:
            raise HTTPException(status_code=404, detail=execution_data["error"])
        
        return ExecutionResponse(
            id=execution_data["id"],
            project_id=execution_data["project_id"],
            framework_name=execution_data["framework_name"],
            execution_name=execution_data["execution_name"],
            status=execution_data["status"],
            start_time=execution_data["start_time"],
            end_time=execution_data["end_time"],
            duration_seconds=execution_data["duration_seconds"],
            total_tests=execution_data["total_tests"],
            passed_tests=execution_data["passed_tests"],
            failed_tests=execution_data["failed_tests"],
            skipped_tests=execution_data["skipped_tests"],
            exit_code=execution_data["exit_code"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: int):
    """Cancel a running execution"""
    try:
        success = execution_manager.cancel_execution(execution_id)
        
        if success:
            return {"message": "Execution cancelled successfully"}
        else:
            raise HTTPException(status_code=400, detail="Execution not found or not running")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling execution: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Log Management Endpoints

@app.get("/executions/{execution_id}/logs", response_model=List[LogEntry])
async def get_execution_logs(execution_id: int, log_type: Optional[str] = None, limit: int = 100):
    """Get logs for a specific execution"""
    try:
        if not execution_manager.db_manager.connect():
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        if log_type:
            query = """
                SELECT * FROM test_logs 
                WHERE execution_id = %s AND log_type = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """
            params = (execution_id, log_type, limit)
        else:
            query = """
                SELECT * FROM test_logs 
                WHERE execution_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """
            params = (execution_id, limit)
        
        results = execution_manager.db_manager.execute_query(query, params, fetch=True)
        
        return [LogEntry(**dict(row)) for row in results] if results else []
        
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        execution_manager.db_manager.disconnect()

@app.get("/executions/{execution_id}/logs/stream")
async def stream_execution_logs(execution_id: int):
    """Stream logs for a specific execution (Server-Sent Events)"""
    async def generate():
        try:
            if not execution_manager.db_manager.connect():
                yield "data: {\"error\": \"Database connection failed\"}\n\n"
                return
            
            last_log_id = 0
            
            while True:
                query = """
                    SELECT * FROM test_logs 
                    WHERE execution_id = %s AND id > %s
                    ORDER BY id ASC
                    LIMIT 10
                """
                params = (execution_id, last_log_id)
                
                results = execution_manager.db_manager.execute_query(query, params, fetch=True)
                
                if results:
                    for row in results:
                        log_entry = LogEntry(**dict(row))
                        yield f"data: {log_entry.json()}\n\n"
                        last_log_id = log_entry.id
                
                # Check if execution is still running
                execution_query = "SELECT status FROM test_executions WHERE id = %s"
                execution_result = execution_manager.db_manager.execute_query(
                    execution_query, (execution_id,), fetch=True
                )
                
                if execution_result and execution_result[0]["status"] not in ["running", "pending"]:
                    break
                
                # Wait before next poll
                import asyncio
                await asyncio.sleep(1)
                
        except Exception as e:
            yield f"data: {{\"error\": \"Error streaming logs: {str(e)}\"}}\n\n"
        finally:
            execution_manager.db_manager.disconnect()
    
    return StreamingResponse(generate(), media_type="text/plain")

# Test Results Endpoints

@app.get("/executions/{execution_id}/results")
async def get_execution_results(execution_id: int):
    """Get detailed test results for an execution"""
    try:
        if not execution_manager.db_manager.connect():
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        query = """
            SELECT * FROM test_results 
            WHERE execution_id = %s
            ORDER BY test_suite, test_case
        """
        results = execution_manager.db_manager.execute_query(query, (execution_id,), fetch=True)
        
        return [dict(row) for row in results] if results else []
        
    except Exception as e:
        logger.error(f"Error getting test results: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        execution_manager.db_manager.disconnect()

# Framework Management Endpoints

@app.get("/frameworks")
async def list_frameworks():
    """List available test frameworks"""
    try:
        if not execution_manager.db_manager.connect():
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        query = "SELECT * FROM frameworks ORDER BY name"
        results = execution_manager.db_manager.execute_query(query, fetch=True)
        
        return [dict(row) for row in results] if results else []
        
    except Exception as e:
        logger.error(f"Error listing frameworks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        execution_manager.db_manager.disconnect()

# Statistics Endpoints

@app.get("/statistics/dashboard")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        if not execution_manager.db_manager.connect():
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        # Get execution statistics
        stats_query = """
            SELECT 
                COUNT(*) as total_executions,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_executions,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_executions,
                COUNT(CASE WHEN status = 'running' THEN 1 END) as running_executions,
                AVG(duration_seconds) as avg_duration_seconds,
                SUM(total_tests) as total_tests_run,
                SUM(passed_tests) as total_tests_passed,
                SUM(failed_tests) as total_tests_failed
            FROM test_executions
            WHERE start_time >= NOW() - INTERVAL '30 days'
        """
        
        stats_result = execution_manager.db_manager.execute_query(stats_query, fetch=True)
        stats = dict(stats_result[0]) if stats_result else {}
        
        # Get framework usage
        framework_query = """
            SELECT f.name, COUNT(*) as execution_count
            FROM test_executions te
            JOIN frameworks f ON te.framework_id = f.id
            WHERE te.start_time >= NOW() - INTERVAL '30 days'
            GROUP BY f.name
            ORDER BY execution_count DESC
        """
        
        framework_results = execution_manager.db_manager.execute_query(framework_query, fetch=True)
        framework_usage = [dict(row) for row in framework_results] if framework_results else []
        
        return {
            "statistics": stats,
            "framework_usage": framework_usage
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        execution_manager.db_manager.disconnect()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 