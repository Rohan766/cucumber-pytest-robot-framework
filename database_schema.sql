-- Database Schema for Test Execution System

-- Projects table
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN ('local', 'github')),
    source_url TEXT,
    local_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Testing frameworks table
CREATE TABLE frameworks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    version VARCHAR(50),
    command_template TEXT NOT NULL,
    file_patterns TEXT[], -- Array of file patterns to identify test files
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Test executions table
CREATE TABLE test_executions (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    framework_id INTEGER REFERENCES frameworks(id),
    execution_name VARCHAR(255),
    status VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    total_tests INTEGER DEFAULT 0,
    passed_tests INTEGER DEFAULT 0,
    failed_tests INTEGER DEFAULT 0,
    skipped_tests INTEGER DEFAULT 0,
    execution_command TEXT,
    exit_code INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Test logs table
CREATE TABLE test_logs (
    id SERIAL PRIMARY KEY,
    execution_id INTEGER REFERENCES test_executions(id),
    log_type VARCHAR(50) NOT NULL CHECK (log_type IN ('stdout', 'stderr', 'output', 'error', 'info', 'warning')),
    log_level VARCHAR(20) DEFAULT 'info',
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_path TEXT,
    line_number INTEGER,
    test_case VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Test results table (detailed test case results)
CREATE TABLE test_results (
    id SERIAL PRIMARY KEY,
    execution_id INTEGER REFERENCES test_executions(id),
    test_case VARCHAR(255) NOT NULL,
    test_suite VARCHAR(255),
    status VARCHAR(50) NOT NULL CHECK (status IN ('passed', 'failed', 'skipped', 'error')),
    duration_seconds DECIMAL(10, 3),
    error_message TEXT,
    failure_details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Test artifacts table (reports, screenshots, etc.)
CREATE TABLE test_artifacts (
    id SERIAL PRIMARY KEY,
    execution_id INTEGER REFERENCES test_executions(id),
    artifact_type VARCHAR(50) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    mime_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default frameworks
INSERT INTO frameworks (name, version, command_template, file_patterns) VALUES 
('pytest', '7.0+', 'pytest {test_path} --tb=short --junitxml={output_dir}/pytest_results.xml -v', ARRAY['test_*.py', '*_test.py']),
('cucumber', '8.0+', 'cucumber {test_path} --format json --out {output_dir}/cucumber_results.json', ARRAY['*.feature']),
('robot', '6.0+', 'robot --outputdir {output_dir} --output robot_output.xml --log robot_log.html --report robot_report.html {test_path}', ARRAY['*.robot', '*.txt']);

-- Create indexes for better performance
CREATE INDEX idx_test_executions_project_id ON test_executions(project_id);
CREATE INDEX idx_test_executions_status ON test_executions(status);
CREATE INDEX idx_test_executions_start_time ON test_executions(start_time);
CREATE INDEX idx_test_logs_execution_id ON test_logs(execution_id);
CREATE INDEX idx_test_logs_log_type ON test_logs(log_type);
CREATE INDEX idx_test_logs_timestamp ON test_logs(timestamp);
CREATE INDEX idx_test_results_execution_id ON test_results(execution_id);
CREATE INDEX idx_test_results_status ON test_results(status);

-- Views for reporting
CREATE VIEW execution_summary AS
SELECT 
    te.id,
    te.execution_name,
    p.name as project_name,
    f.name as framework_name,
    te.status,
    te.start_time,
    te.end_time,
    te.duration_seconds,
    te.total_tests,
    te.passed_tests,
    te.failed_tests,
    te.skipped_tests,
    CASE 
        WHEN te.total_tests > 0 THEN 
            ROUND((te.passed_tests::decimal / te.total_tests::decimal) * 100, 2)
        ELSE 0 
    END as pass_rate
FROM test_executions te
JOIN projects p ON te.project_id = p.id
JOIN frameworks f ON te.framework_id = f.id;

CREATE VIEW recent_executions AS
SELECT * FROM execution_summary 
ORDER BY start_time DESC 
LIMIT 50; 