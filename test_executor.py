import os
import sys
import json
import subprocess
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import xml.etree.ElementTree as ET
import psycopg2
from psycopg2.extras import DictCursor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class LogType(Enum):
    STDOUT = "stdout"
    STDERR = "stderr"
    OUTPUT = "output"
    ERROR = "error"
    INFO = "info"
    WARNING = "warning"

@dataclass
class TestExecution:
    id: Optional[int] = None
    project_id: int = None
    framework_id: int = None
    execution_name: str = None
    status: TestStatus = TestStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    execution_command: str = None
    exit_code: Optional[int] = None

@dataclass
class TestResult:
    execution_id: int
    test_case: str
    test_suite: str
    status: str
    duration_seconds: float
    error_message: Optional[str] = None
    failure_details: Optional[str] = None

class DatabaseManager:
    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
        self.connection = None
        
    def connect(self):
        try:
            self.connection = psycopg2.connect(**self.db_config)
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def disconnect(self):
        if self.connection:
            self.connection.close()
    
    def execute_query(self, query: str, params: tuple = None, fetch: bool = False):
        cursor = self.connection.cursor(cursor_factory=DictCursor)
        try:
            cursor.execute(query, params)
            if fetch:
                return cursor.fetchall()
            self.connection.commit()
            return cursor.fetchone() if cursor.rowcount > 0 else None
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            self.connection.rollback()
            raise
        finally:
            cursor.close()

class LogManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
    def log_message(self, execution_id: int, log_type: LogType, message: str, 
                   log_level: str = "info", file_path: str = None, 
                   line_number: int = None, test_case: str = None):
        query = """
            INSERT INTO test_logs (execution_id, log_type, log_level, message, 
                                 file_path, line_number, test_case)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (execution_id, log_type.value, log_level, message, 
                 file_path, line_number, test_case)
        
        try:
            self.db_manager.execute_query(query, params)
        except Exception as e:
            logger.error(f"Failed to log message: {e}")

class BaseFrameworkExecutor:
    def __init__(self, db_manager: DatabaseManager, log_manager: LogManager):
        self.db_manager = db_manager
        self.log_manager = log_manager
        self.framework_name = None
        
    def execute_tests(self, project_path: str, output_dir: str, 
                     execution_id: int, additional_args: List[str] = None) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement execute_tests")
    
    def parse_results(self, output_dir: str, execution_id: int) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement parse_results")

class PytestExecutor(BaseFrameworkExecutor):
    def __init__(self, db_manager: DatabaseManager, log_manager: LogManager):
        super().__init__(db_manager, log_manager)
        self.framework_name = "pytest"
        
    def execute_tests(self, project_path: str, output_dir: str, 
                     execution_id: int, additional_args: List[str] = None) -> Dict[str, Any]:
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Build command
        junit_xml = os.path.join(output_dir, "pytest_results.xml")
        json_report = os.path.join(output_dir, "pytest_results.json")
        
        cmd = [
            "pytest", 
            project_path,
            "--tb=short",
            f"--junitxml={junit_xml}",
            f"--json-report={json_report}",
            "-v"
        ]
        
        if additional_args:
            cmd.extend(additional_args)
            
        self.log_manager.log_message(execution_id, LogType.INFO, f"Executing: {' '.join(cmd)}")
        
        # Execute tests
        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_path)
            end_time = time.time()
            
            # Log stdout and stderr
            if result.stdout:
                self.log_manager.log_message(execution_id, LogType.STDOUT, result.stdout)
            if result.stderr:
                self.log_manager.log_message(execution_id, LogType.STDERR, result.stderr)
                
            # Parse results
            test_results = self.parse_results(output_dir, execution_id)
            
            return {
                "exit_code": result.returncode,
                "duration": end_time - start_time,
                "results": test_results
            }
            
        except Exception as e:
            self.log_manager.log_message(execution_id, LogType.ERROR, str(e))
            raise
    
    def parse_results(self, output_dir: str, execution_id: int) -> Dict[str, Any]:
        junit_xml = os.path.join(output_dir, "pytest_results.xml")
        json_report = os.path.join(output_dir, "pytest_results.json")
        
        results = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "test_cases": []}
        
        # Parse JUnit XML
        if os.path.exists(junit_xml):
            try:
                tree = ET.parse(junit_xml)
                root = tree.getroot()
                
                for testcase in root.findall(".//testcase"):
                    test_name = testcase.get("name")
                    class_name = testcase.get("classname")
                    time_taken = float(testcase.get("time", 0))
                    
                    status = "passed"
                    error_message = None
                    failure_details = None
                    
                    if testcase.find("failure") is not None:
                        status = "failed"
                        failure_elem = testcase.find("failure")
                        error_message = failure_elem.get("message")
                        failure_details = failure_elem.text
                    elif testcase.find("error") is not None:
                        status = "error"
                        error_elem = testcase.find("error")
                        error_message = error_elem.get("message")
                        failure_details = error_elem.text
                    elif testcase.find("skipped") is not None:
                        status = "skipped"
                    
                    # Save test result to database
                    test_result = TestResult(
                        execution_id=execution_id,
                        test_case=test_name,
                        test_suite=class_name,
                        status=status,
                        duration_seconds=time_taken,
                        error_message=error_message,
                        failure_details=failure_details
                    )
                    
                    self.save_test_result(test_result)
                    results["test_cases"].append(test_result)
                    results["total"] += 1
                    
                    if status == "passed":
                        results["passed"] += 1
                    elif status in ["failed", "error"]:
                        results["failed"] += 1
                    elif status == "skipped":
                        results["skipped"] += 1
                        
            except Exception as e:
                self.log_manager.log_message(execution_id, LogType.ERROR, f"Failed to parse JUnit XML: {e}")
        
        return results
    
    def save_test_result(self, test_result: TestResult):
        query = """
            INSERT INTO test_results (execution_id, test_case, test_suite, status, 
                                    duration_seconds, error_message, failure_details)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            test_result.execution_id,
            test_result.test_case,
            test_result.test_suite,
            test_result.status,
            test_result.duration_seconds,
            test_result.error_message,
            test_result.failure_details
        )
        
        self.db_manager.execute_query(query, params)

class CucumberExecutor(BaseFrameworkExecutor):
    def __init__(self, db_manager: DatabaseManager, log_manager: LogManager):
        super().__init__(db_manager, log_manager)
        self.framework_name = "cucumber"
        
    def execute_tests(self, project_path: str, output_dir: str, 
                     execution_id: int, additional_args: List[str] = None) -> Dict[str, Any]:
        
        os.makedirs(output_dir, exist_ok=True)
        
        json_report = os.path.join(output_dir, "cucumber_results.json")
        
        cmd = [
            "cucumber",
            project_path,
            "--format", "json",
            "--out", json_report,
            "--format", "pretty"
        ]
        
        if additional_args:
            cmd.extend(additional_args)
            
        self.log_manager.log_message(execution_id, LogType.INFO, f"Executing: {' '.join(cmd)}")
        
        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_path)
            end_time = time.time()
            
            if result.stdout:
                self.log_manager.log_message(execution_id, LogType.STDOUT, result.stdout)
            if result.stderr:
                self.log_manager.log_message(execution_id, LogType.STDERR, result.stderr)
                
            test_results = self.parse_results(output_dir, execution_id)
            
            return {
                "exit_code": result.returncode,
                "duration": end_time - start_time,
                "results": test_results
            }
            
        except Exception as e:
            self.log_manager.log_message(execution_id, LogType.ERROR, str(e))
            raise
    
    def parse_results(self, output_dir: str, execution_id: int) -> Dict[str, Any]:
        json_report = os.path.join(output_dir, "cucumber_results.json")
        results = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "test_cases": []}
        
        if os.path.exists(json_report):
            try:
                with open(json_report, 'r') as f:
                    cucumber_data = json.load(f)
                
                for feature in cucumber_data:
                    feature_name = feature.get("name", "Unknown Feature")
                    
                    for element in feature.get("elements", []):
                        scenario_name = element.get("name", "Unknown Scenario")
                        
                        # Calculate scenario duration and status
                        scenario_duration = 0
                        scenario_status = "passed"
                        error_message = None
                        
                        for step in element.get("steps", []):
                            step_result = step.get("result", {})
                            step_duration = step_result.get("duration", 0) / 1000000000  # Convert from nanoseconds
                            scenario_duration += step_duration
                            
                            if step_result.get("status") == "failed":
                                scenario_status = "failed"
                                error_message = step_result.get("error_message")
                            elif step_result.get("status") == "skipped" and scenario_status == "passed":
                                scenario_status = "skipped"
                        
                        # Save test result
                        test_result = TestResult(
                            execution_id=execution_id,
                            test_case=scenario_name,
                            test_suite=feature_name,
                            status=scenario_status,
                            duration_seconds=scenario_duration,
                            error_message=error_message
                        )
                        
                        self.save_test_result(test_result)
                        results["test_cases"].append(test_result)
                        results["total"] += 1
                        
                        if scenario_status == "passed":
                            results["passed"] += 1
                        elif scenario_status == "failed":
                            results["failed"] += 1
                        elif scenario_status == "skipped":
                            results["skipped"] += 1
                            
            except Exception as e:
                self.log_manager.log_message(execution_id, LogType.ERROR, f"Failed to parse Cucumber JSON: {e}")
        
        return results
    
    def save_test_result(self, test_result: TestResult):
        query = """
            INSERT INTO test_results (execution_id, test_case, test_suite, status, 
                                    duration_seconds, error_message, failure_details)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            test_result.execution_id,
            test_result.test_case,
            test_result.test_suite,
            test_result.status,
            test_result.duration_seconds,
            test_result.error_message,
            test_result.failure_details
        )
        
        self.db_manager.execute_query(query, params)

class RobotFrameworkExecutor(BaseFrameworkExecutor):
    def __init__(self, db_manager: DatabaseManager, log_manager: LogManager):
        super().__init__(db_manager, log_manager)
        self.framework_name = "robot"
        
    def execute_tests(self, project_path: str, output_dir: str, 
                     execution_id: int, additional_args: List[str] = None) -> Dict[str, Any]:
        
        os.makedirs(output_dir, exist_ok=True)
        
        cmd = [
            "robot",
            "--outputdir", output_dir,
            "--output", "robot_output.xml",
            "--log", "robot_log.html",
            "--report", "robot_report.html",
            project_path
        ]
        
        if additional_args:
            cmd.extend(additional_args)
            
        self.log_manager.log_message(execution_id, LogType.INFO, f"Executing: {' '.join(cmd)}")
        
        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_path)
            end_time = time.time()
            
            if result.stdout:
                self.log_manager.log_message(execution_id, LogType.STDOUT, result.stdout)
            if result.stderr:
                self.log_manager.log_message(execution_id, LogType.STDERR, result.stderr)
                
            test_results = self.parse_results(output_dir, execution_id)
            
            return {
                "exit_code": result.returncode,
                "duration": end_time - start_time,
                "results": test_results
            }
            
        except Exception as e:
            self.log_manager.log_message(execution_id, LogType.ERROR, str(e))
            raise
    
    def parse_results(self, output_dir: str, execution_id: int) -> Dict[str, Any]:
        output_xml = os.path.join(output_dir, "robot_output.xml")
        results = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "test_cases": []}
        
        if os.path.exists(output_xml):
            try:
                tree = ET.parse(output_xml)
                root = tree.getroot()
                
                for test in root.findall(".//test"):
                    test_name = test.get("name")
                    
                    # Find the suite this test belongs to
                    suite = test.find("../")
                    suite_name = suite.get("name") if suite is not None else "Unknown Suite"
                    
                    # Get test status and timing
                    status_elem = test.find("status")
                    if status_elem is not None:
                        status = status_elem.get("status", "").lower()
                        start_time = status_elem.get("starttime")
                        end_time = status_elem.get("endtime")
                        
                        # Calculate duration (Robot Framework times are in format: 20210101 10:00:00.000)
                        duration = 0
                        if start_time and end_time:
                            try:
                                start_dt = datetime.strptime(start_time, "%Y%m%d %H:%M:%S.%f")
                                end_dt = datetime.strptime(end_time, "%Y%m%d %H:%M:%S.%f")
                                duration = (end_dt - start_dt).total_seconds()
                            except:
                                pass
                        
                        # Get error message if test failed
                        error_message = None
                        failure_details = None
                        if status == "fail":
                            msg_elem = test.find("msg")
                            if msg_elem is not None:
                                error_message = msg_elem.text
                                failure_details = msg_elem.text
                        
                        # Save test result
                        test_result = TestResult(
                            execution_id=execution_id,
                            test_case=test_name,
                            test_suite=suite_name,
                            status=status,
                            duration_seconds=duration,
                            error_message=error_message,
                            failure_details=failure_details
                        )
                        
                        self.save_test_result(test_result)
                        results["test_cases"].append(test_result)
                        results["total"] += 1
                        
                        if status == "pass":
                            results["passed"] += 1
                        elif status == "fail":
                            results["failed"] += 1
                        else:
                            results["skipped"] += 1
                            
            except Exception as e:
                self.log_manager.log_message(execution_id, LogType.ERROR, f"Failed to parse Robot output XML: {e}")
        
        return results
    
    def save_test_result(self, test_result: TestResult):
        query = """
            INSERT INTO test_results (execution_id, test_case, test_suite, status, 
                                    duration_seconds, error_message, failure_details)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            test_result.execution_id,
            test_result.test_case,
            test_result.test_suite,
            test_result.status,
            test_result.duration_seconds,
            test_result.error_message,
            test_result.failure_details
        )
        
        self.db_manager.execute_query(query, params)

class TestExecutionManager:
    def __init__(self, db_config: Dict[str, str]):
        self.db_manager = DatabaseManager(db_config)
        self.log_manager = LogManager(self.db_manager)
        
        # Initialize framework executors
        self.executors = {
            "pytest": PytestExecutor(self.db_manager, self.log_manager),
            "cucumber": CucumberExecutor(self.db_manager, self.log_manager),
            "robot": RobotFrameworkExecutor(self.db_manager, self.log_manager)
        }
        
        self.running_executions = {}
        
    def start_execution(self, project_id: int, framework_name: str, 
                       execution_name: str, project_path: str, 
                       additional_args: List[str] = None) -> int:
        
        if not self.db_manager.connect():
            raise Exception("Failed to connect to database")
        
        # Get framework ID
        framework_query = "SELECT id FROM frameworks WHERE name = %s"
        framework_result = self.db_manager.execute_query(framework_query, (framework_name,), fetch=True)
        
        if not framework_result:
            raise Exception(f"Framework '{framework_name}' not found")
        
        framework_id = framework_result[0]["id"]
        
        # Create execution record
        execution = TestExecution(
            project_id=project_id,
            framework_id=framework_id,
            execution_name=execution_name,
            status=TestStatus.PENDING,
            start_time=datetime.now()
        )
        
        # Insert execution record
        insert_query = """
            INSERT INTO test_executions (project_id, framework_id, execution_name, 
                                       status, start_time)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (execution.project_id, execution.framework_id, execution.execution_name,
                 execution.status.value, execution.start_time)
        
        result = self.db_manager.execute_query(insert_query, params)
        execution_id = result["id"]
        
        # Start execution in background thread
        thread = threading.Thread(
            target=self._run_execution,
            args=(execution_id, framework_name, project_path, additional_args)
        )
        thread.start()
        
        self.running_executions[execution_id] = {
            "thread": thread,
            "status": TestStatus.RUNNING
        }
        
        return execution_id
    
    def _run_execution(self, execution_id: int, framework_name: str, 
                      project_path: str, additional_args: List[str] = None):
        
        output_dir = os.path.join("/tmp/test_outputs", str(execution_id))
        
        try:
            # Update status to running
            self._update_execution_status(execution_id, TestStatus.RUNNING)
            
            # Get executor for framework
            executor = self.executors.get(framework_name)
            if not executor:
                raise Exception(f"No executor found for framework: {framework_name}")
            
            # Execute tests
            result = executor.execute_tests(project_path, output_dir, execution_id, additional_args)
            
            # Update execution record with results
            self._update_execution_results(execution_id, result)
            
            # Update status to completed
            self._update_execution_status(execution_id, TestStatus.COMPLETED)
            
        except Exception as e:
            self.log_manager.log_message(execution_id, LogType.ERROR, f"Execution failed: {str(e)}")
            self._update_execution_status(execution_id, TestStatus.FAILED)
        
        finally:
            # Clean up
            if execution_id in self.running_executions:
                del self.running_executions[execution_id]
            self.db_manager.disconnect()
    
    def _update_execution_status(self, execution_id: int, status: TestStatus):
        update_query = """
            UPDATE test_executions 
            SET status = %s, updated_at = %s
            WHERE id = %s
        """
        params = (status.value, datetime.now(), execution_id)
        self.db_manager.execute_query(update_query, params)
    
    def _update_execution_results(self, execution_id: int, result: Dict[str, Any]):
        test_results = result.get("results", {})
        
        update_query = """
            UPDATE test_executions 
            SET end_time = %s, duration_seconds = %s, total_tests = %s, 
                passed_tests = %s, failed_tests = %s, skipped_tests = %s,
                exit_code = %s, updated_at = %s
            WHERE id = %s
        """
        params = (
            datetime.now(),
            int(result.get("duration", 0)),
            test_results.get("total", 0),
            test_results.get("passed", 0),
            test_results.get("failed", 0),
            test_results.get("skipped", 0),
            result.get("exit_code", 0),
            datetime.now(),
            execution_id
        )
        self.db_manager.execute_query(update_query, params)
    
    def get_execution_status(self, execution_id: int) -> Dict[str, Any]:
        if not self.db_manager.connect():
            return {"error": "Database connection failed"}
        
        query = """
            SELECT te.*, p.name as project_name, f.name as framework_name
            FROM test_executions te
            JOIN projects p ON te.project_id = p.id
            JOIN frameworks f ON te.framework_id = f.id
            WHERE te.id = %s
        """
        
        result = self.db_manager.execute_query(query, (execution_id,), fetch=True)
        
        if result:
            execution = dict(result[0])
            execution["is_running"] = execution_id in self.running_executions
            return execution
        
        return {"error": "Execution not found"}
    
    def cancel_execution(self, execution_id: int) -> bool:
        if execution_id in self.running_executions:
            # Note: This is a simplified cancellation - in production you'd want
            # to properly terminate the subprocess
            self.running_executions[execution_id]["status"] = TestStatus.CANCELLED
            self._update_execution_status(execution_id, TestStatus.CANCELLED)
            return True
        return False 