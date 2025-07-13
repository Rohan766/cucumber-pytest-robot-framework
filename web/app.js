// Configuration
const API_BASE_URL = 'http://localhost:8000';

// State management
let currentProjects = [];
let currentExecutions = [];
let currentFrameworks = [];

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    loadDashboard();
    loadProjects();
    loadFrameworks();
    loadExecutions();
    
    // Set up auto-refresh for dashboard
    setInterval(loadDashboard, 30000); // Refresh every 30 seconds
    setInterval(loadExecutions, 10000); // Refresh executions every 10 seconds
});

// Navigation functions
function showSection(sectionId) {
    // Hide all sections
    const sections = document.querySelectorAll('.content-section');
    sections.forEach(section => section.classList.remove('active'));
    
    // Show selected section
    document.getElementById(sectionId).classList.add('active');
    
    // Update sidebar
    const sidebarItems = document.querySelectorAll('.sidebar-item');
    sidebarItems.forEach(item => item.classList.remove('active'));
    event.target.classList.add('active');
    
    // Load section-specific data
    switch(sectionId) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'projects':
            loadProjects();
            break;
        case 'executions':
            loadExecutions();
            break;
        case 'logs':
            loadExecutionsList();
            break;
        case 'frameworks':
            loadFrameworks();
            break;
    }
}

// API helper functions
async function apiRequest(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`API request failed: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Request Error:', error);
        showNotification('Error connecting to API', 'error');
        throw error;
    }
}

// Dashboard functions
async function loadDashboard() {
    try {
        const stats = await apiRequest('/statistics/dashboard');
        
        // Update statistics cards
        document.getElementById('totalExecutions').textContent = stats.statistics.total_executions || 0;
        document.getElementById('completedExecutions').textContent = stats.statistics.completed_executions || 0;
        document.getElementById('failedExecutions').textContent = stats.statistics.failed_executions || 0;
        document.getElementById('runningExecutions').textContent = stats.statistics.running_executions || 0;
        
        // Load recent executions
        const executions = await apiRequest('/executions?limit=10');
        updateRecentExecutionsTable(executions);
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

function updateRecentExecutionsTable(executions) {
    const tbody = document.getElementById('recentExecutionsTable');
    tbody.innerHTML = '';
    
    executions.forEach(execution => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${execution.execution_name}</td>
            <td><span class="framework-badge framework-${execution.framework_name}">${execution.framework_name}</span></td>
            <td><span class="status-badge status-${execution.status}">${execution.status}</span></td>
            <td>${execution.duration_seconds ? `${execution.duration_seconds}s` : '-'}</td>
            <td>
                <small class="text-muted">
                    ${execution.total_tests} total |
                    <span class="text-success">${execution.passed_tests} passed</span> |
                    <span class="text-danger">${execution.failed_tests} failed</span>
                </small>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="viewExecutionDetails(${execution.id})">
                    <i class="fas fa-eye"></i>
                </button>
                ${execution.status === 'running' ? `
                    <button class="btn btn-sm btn-outline-danger" onclick="cancelExecution(${execution.id})">
                        <i class="fas fa-stop"></i>
                    </button>
                ` : ''}
            </td>
        `;
        tbody.appendChild(row);
    });
}

function refreshDashboard() {
    loadDashboard();
    showNotification('Dashboard refreshed', 'success');
}

// Projects functions
async function loadProjects() {
    try {
        const projects = await apiRequest('/projects');
        currentProjects = projects;
        updateProjectsContainer(projects);
        updateProjectSelects(projects);
    } catch (error) {
        console.error('Error loading projects:', error);
    }
}

function updateProjectsContainer(projects) {
    const container = document.getElementById('projectsContainer');
    container.innerHTML = '';
    
    projects.forEach(project => {
        const projectCard = document.createElement('div');
        projectCard.className = 'col-md-4 mb-3';
        projectCard.innerHTML = `
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">${project.name}</h5>
                    <p class="card-text">${project.description || 'No description'}</p>
                    <div class="mb-2">
                        <span class="badge bg-primary">${project.source_type}</span>
                    </div>
                    <div class="d-flex justify-content-between">
                        <button class="btn btn-sm btn-primary" onclick="analyzeProject(${project.id})">
                            <i class="fas fa-search"></i> Analyze
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteProject(${project.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(projectCard);
    });
}

function updateProjectSelects(projects) {
    const selects = document.querySelectorAll('#executionProjectSelect, #logExecutionSelect');
    selects.forEach(select => {
        // Clear existing options except the first one
        while (select.children.length > 1) {
            select.removeChild(select.lastChild);
        }
        
        projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project.id;
            option.textContent = project.name;
            select.appendChild(option);
        });
    });
}

function showCreateProjectModal() {
    const modal = new bootstrap.Modal(document.getElementById('createProjectModal'));
    modal.show();
}

function toggleSourceFields() {
    const sourceType = document.getElementById('sourceType').value;
    const githubField = document.getElementById('githubUrlField');
    const localField = document.getElementById('localPathField');
    
    if (sourceType === 'github') {
        githubField.style.display = 'block';
        localField.style.display = 'none';
        document.getElementById('githubUrl').required = true;
        document.getElementById('localPath').required = false;
    } else {
        githubField.style.display = 'none';
        localField.style.display = 'block';
        document.getElementById('githubUrl').required = false;
        document.getElementById('localPath').required = true;
    }
}

async function createProject() {
    try {
        const formData = {
            name: document.getElementById('projectName').value,
            description: document.getElementById('projectDescription').value,
            source_type: document.getElementById('sourceType').value,
            source_url: document.getElementById('githubUrl').value || null,
            local_path: document.getElementById('localPath').value || null
        };
        
        await apiRequest('/projects', {
            method: 'POST',
            body: JSON.stringify(formData)
        });
        
        showNotification('Project created successfully', 'success');
        bootstrap.Modal.getInstance(document.getElementById('createProjectModal')).hide();
        document.getElementById('createProjectForm').reset();
        loadProjects();
        
    } catch (error) {
        console.error('Error creating project:', error);
        showNotification('Error creating project', 'error');
    }
}

async function analyzeProject(projectId) {
    try {
        const analysis = await apiRequest(`/projects/${projectId}/analyze`, {
            method: 'POST'
        });
        
        showNotification(`Analysis complete: Found ${analysis.detected_frameworks.join(', ')} frameworks`, 'success');
        
    } catch (error) {
        console.error('Error analyzing project:', error);
        showNotification('Error analyzing project', 'error');
    }
}

async function deleteProject(projectId) {
    if (confirm('Are you sure you want to delete this project?')) {
        try {
            await apiRequest(`/projects/${projectId}`, {
                method: 'DELETE'
            });
            
            showNotification('Project deleted successfully', 'success');
            loadProjects();
            
        } catch (error) {
            console.error('Error deleting project:', error);
            showNotification('Error deleting project', 'error');
        }
    }
}

// Executions functions
async function loadExecutions() {
    try {
        const executions = await apiRequest('/executions?limit=50');
        currentExecutions = executions;
        updateExecutionsTable(executions);
    } catch (error) {
        console.error('Error loading executions:', error);
    }
}

function updateExecutionsTable(executions) {
    const tbody = document.getElementById('executionsTable');
    tbody.innerHTML = '';
    
    executions.forEach(execution => {
        const row = document.createElement('tr');
        const startTime = execution.start_time ? new Date(execution.start_time).toLocaleString() : '-';
        const passRate = execution.total_tests > 0 ? 
            Math.round((execution.passed_tests / execution.total_tests) * 100) : 0;
        
        row.innerHTML = `
            <td>${execution.id}</td>
            <td>${execution.execution_name}</td>
            <td><span class="framework-badge framework-${execution.framework_name}">${execution.framework_name}</span></td>
            <td><span class="status-badge status-${execution.status}">${execution.status}</span></td>
            <td>${startTime}</td>
            <td>${execution.duration_seconds ? `${execution.duration_seconds}s` : '-'}</td>
            <td>
                <div class="progress" style="height: 10px;">
                    <div class="progress-bar bg-success" style="width: ${passRate}%"></div>
                </div>
                <small class="text-muted">
                    ${execution.passed_tests}/${execution.total_tests} passed (${passRate}%)
                </small>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="viewExecutionDetails(${execution.id})">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn btn-sm btn-outline-info" onclick="viewExecutionLogs(${execution.id})">
                    <i class="fas fa-file-alt"></i>
                </button>
                ${execution.status === 'running' ? `
                    <button class="btn btn-sm btn-outline-danger" onclick="cancelExecution(${execution.id})">
                        <i class="fas fa-stop"></i>
                    </button>
                ` : ''}
            </td>
        `;
        tbody.appendChild(row);
    });
}

function showStartExecutionModal() {
    const modal = new bootstrap.Modal(document.getElementById('startExecutionModal'));
    modal.show();
}

async function startExecution() {
    try {
        const formData = {
            project_id: parseInt(document.getElementById('executionProjectSelect').value),
            framework_name: document.getElementById('executionFramework').value,
            execution_name: document.getElementById('executionName').value,
            test_path: document.getElementById('testPath').value || null,
            additional_args: document.getElementById('additionalArgs').value ? 
                document.getElementById('additionalArgs').value.split(' ') : null
        };
        
        const result = await apiRequest('/executions', {
            method: 'POST',
            body: JSON.stringify(formData)
        });
        
        showNotification(`Execution started: ${result.execution_id}`, 'success');
        bootstrap.Modal.getInstance(document.getElementById('startExecutionModal')).hide();
        document.getElementById('startExecutionForm').reset();
        loadExecutions();
        
    } catch (error) {
        console.error('Error starting execution:', error);
        showNotification('Error starting execution', 'error');
    }
}

async function cancelExecution(executionId) {
    if (confirm('Are you sure you want to cancel this execution?')) {
        try {
            await apiRequest(`/executions/${executionId}/cancel`, {
                method: 'POST'
            });
            
            showNotification('Execution cancelled', 'success');
            loadExecutions();
            
        } catch (error) {
            console.error('Error cancelling execution:', error);
            showNotification('Error cancelling execution', 'error');
        }
    }
}

async function viewExecutionDetails(executionId) {
    try {
        const execution = await apiRequest(`/executions/${executionId}`);
        const results = await apiRequest(`/executions/${executionId}/results`);
        
        // Create a detailed view modal or navigate to a details page
        alert(`Execution Details:\n\nName: ${execution.execution_name}\nStatus: ${execution.status}\nTests: ${execution.total_tests}\nPassed: ${execution.passed_tests}\nFailed: ${execution.failed_tests}`);
        
    } catch (error) {
        console.error('Error viewing execution details:', error);
        showNotification('Error loading execution details', 'error');
    }
}

// Logs functions
async function loadExecutionsList() {
    try {
        const executions = await apiRequest('/executions?limit=100');
        const select = document.getElementById('logExecutionSelect');
        
        // Clear existing options except the first one
        while (select.children.length > 1) {
            select.removeChild(select.lastChild);
        }
        
        executions.forEach(execution => {
            const option = document.createElement('option');
            option.value = execution.id;
            option.textContent = `${execution.execution_name} (${execution.framework_name})`;
            select.appendChild(option);
        });
        
    } catch (error) {
        console.error('Error loading executions list:', error);
    }
}

async function loadLogs() {
    const executionId = document.getElementById('logExecutionSelect').value;
    
    if (!executionId) {
        showNotification('Please select an execution', 'warning');
        return;
    }
    
    try {
        const logs = await apiRequest(`/executions/${executionId}/logs?limit=200`);
        updateLogContainer(logs);
        
    } catch (error) {
        console.error('Error loading logs:', error);
        showNotification('Error loading logs', 'error');
    }
}

function updateLogContainer(logs) {
    const container = document.getElementById('logContainer');
    container.innerHTML = '';
    
    if (logs.length === 0) {
        container.innerHTML = '<div class="text-center text-muted">No logs found</div>';
        return;
    }
    
    logs.reverse().forEach(log => {
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        
        const timestamp = new Date(log.timestamp).toLocaleString();
        logEntry.innerHTML = `
            <div class="log-timestamp">${timestamp}</div>
            <div class="log-level-${log.log_level}">[${log.log_type.toUpperCase()}] ${log.message}</div>
            ${log.file_path ? `<div class="text-muted small">File: ${log.file_path}:${log.line_number || ''}</div>` : ''}
        `;
        
        container.appendChild(logEntry);
    });
    
    // Auto-scroll to bottom
    container.scrollTop = container.scrollHeight;
}

function viewExecutionLogs(executionId) {
    // Switch to logs section and load the execution
    showSection('logs');
    document.getElementById('logExecutionSelect').value = executionId;
    loadLogs();
}

// Frameworks functions
async function loadFrameworks() {
    try {
        const frameworks = await apiRequest('/frameworks');
        currentFrameworks = frameworks;
        updateFrameworksContainer(frameworks);
    } catch (error) {
        console.error('Error loading frameworks:', error);
    }
}

function updateFrameworksContainer(frameworks) {
    const container = document.getElementById('frameworksContainer');
    container.innerHTML = '';
    
    frameworks.forEach(framework => {
        const frameworkCard = document.createElement('div');
        frameworkCard.className = 'col-md-4 mb-3';
        frameworkCard.innerHTML = `
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">
                        <span class="framework-badge framework-${framework.name}">${framework.name}</span>
                    </h5>
                    <p class="card-text">
                        <strong>Version:</strong> ${framework.version}<br>
                        <strong>File Patterns:</strong> ${framework.file_patterns.join(', ')}
                    </p>
                    <div class="mt-2">
                        <code class="small">${framework.command_template}</code>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(frameworkCard);
    });
}

// Utility functions
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

// Format time helper
function formatDuration(seconds) {
    if (!seconds) return '-';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

// Export functions for global access
window.showSection = showSection;
window.refreshDashboard = refreshDashboard;
window.showCreateProjectModal = showCreateProjectModal;
window.toggleSourceFields = toggleSourceFields;
window.createProject = createProject;
window.analyzeProject = analyzeProject;
window.deleteProject = deleteProject;
window.showStartExecutionModal = showStartExecutionModal;
window.startExecution = startExecution;
window.cancelExecution = cancelExecution;
window.viewExecutionDetails = viewExecutionDetails;
window.viewExecutionLogs = viewExecutionLogs;
window.loadLogs = loadLogs; 