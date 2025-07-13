// K6 Load Test for Test Execution System
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const responseTrend = new Trend('response_time');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp up to 10 users
    { duration: '5m', target: 10 },   // Stay at 10 users
    { duration: '2m', target: 50 },   // Ramp up to 50 users
    { duration: '5m', target: 50 },   // Stay at 50 users
    { duration: '2m', target: 100 },  // Ramp up to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests must complete below 500ms
    http_req_failed: ['rate<0.1'],    // Error rate must be below 10%
    errors: ['rate<0.1'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Test data
const testProjects = [
  {
    name: 'Load Test Project 1',
    description: 'Performance testing project',
    source_type: 'local',
    local_path: '/tmp/test_project'
  },
  {
    name: 'Load Test Project 2',
    description: 'Performance testing project',
    source_type: 'github',
    source_url: 'https://github.com/example/test-repo'
  }
];

const testExecutions = [
  {
    framework_name: 'pytest',
    execution_name: 'Load Test Execution',
    test_path: 'tests/',
    additional_args: ['-v']
  },
  {
    framework_name: 'robot',
    execution_name: 'Robot Load Test',
    test_path: 'robot_tests/',
    additional_args: ['--include', 'smoke']
  }
];

export function setup() {
  // Setup test data
  console.log('Setting up test data...');
  
  // Health check
  const healthResponse = http.get(`${BASE_URL}/health`);
  check(healthResponse, {
    'Health check passes': (r) => r.status === 200,
  });
  
  // Create test projects
  const projects = [];
  for (const project of testProjects) {
    const response = http.post(`${BASE_URL}/projects`, JSON.stringify(project), {
      headers: { 'Content-Type': 'application/json' },
    });
    
    if (response.status === 200 || response.status === 201) {
      projects.push(response.json());
    }
  }
  
  return { projects };
}

export default function(data) {
  const { projects } = data;
  
  // Test scenarios with different weights
  const scenario = Math.random();
  
  if (scenario < 0.3) {
    // 30% - Health check and basic info endpoints
    testHealthAndInfo();
  } else if (scenario < 0.6) {
    // 30% - Project management operations
    testProjectOperations(projects);
  } else if (scenario < 0.8) {
    // 20% - Execution operations
    testExecutionOperations(projects);
  } else {
    // 20% - Dashboard and statistics
    testDashboardOperations();
  }
  
  sleep(1);
}

function testHealthAndInfo() {
  const requests = [
    { name: 'Health Check', url: `${BASE_URL}/health` },
    { name: 'Get Frameworks', url: `${BASE_URL}/frameworks` },
    { name: 'Dashboard Stats', url: `${BASE_URL}/statistics/dashboard` },
  ];
  
  for (const req of requests) {
    const response = http.get(req.url);
    
    check(response, {
      [`${req.name} - Status 200`]: (r) => r.status === 200,
      [`${req.name} - Response time < 200ms`]: (r) => r.timings.duration < 200,
    });
    
    errorRate.add(response.status !== 200);
    responseTrend.add(response.timings.duration);
  }
}

function testProjectOperations(projects) {
  // List projects
  let response = http.get(`${BASE_URL}/projects`);
  check(response, {
    'List projects - Status 200': (r) => r.status === 200,
    'List projects - Has projects': (r) => r.json().length > 0,
  });
  
  errorRate.add(response.status !== 200);
  responseTrend.add(response.timings.duration);
  
  if (projects.length > 0) {
    const project = projects[Math.floor(Math.random() * projects.length)];
    
    // Get specific project
    response = http.get(`${BASE_URL}/projects/${project.id}`);
    check(response, {
      'Get project - Status 200': (r) => r.status === 200,
      'Get project - Correct ID': (r) => r.json().id === project.id,
    });
    
    errorRate.add(response.status !== 200);
    responseTrend.add(response.timings.duration);
    
    // Analyze project (this might be slower)
    response = http.post(`${BASE_URL}/projects/${project.id}/analyze`);
    check(response, {
      'Analyze project - Success': (r) => r.status === 200 || r.status === 202,
    });
    
    errorRate.add(response.status >= 400);
    responseTrend.add(response.timings.duration);
  }
}

function testExecutionOperations(projects) {
  // List executions
  let response = http.get(`${BASE_URL}/executions?limit=20`);
  check(response, {
    'List executions - Status 200': (r) => r.status === 200,
  });
  
  errorRate.add(response.status !== 200);
  responseTrend.add(response.timings.duration);
  
  if (projects.length > 0) {
    const project = projects[Math.floor(Math.random() * projects.length)];
    const execution = testExecutions[Math.floor(Math.random() * testExecutions.length)];
    
    // Create execution request
    const executionRequest = {
      ...execution,
      project_id: project.id,
    };
    
    // Start execution (might be slower)
    response = http.post(`${BASE_URL}/executions`, JSON.stringify(executionRequest), {
      headers: { 'Content-Type': 'application/json' },
    });
    
    check(response, {
      'Start execution - Success': (r) => r.status === 200 || r.status === 201,
    });
    
    errorRate.add(response.status >= 400);
    responseTrend.add(response.timings.duration);
    
    if (response.status === 200 || response.status === 201) {
      const executionData = response.json();
      const executionId = executionData.execution_id;
      
      // Get execution status
      response = http.get(`${BASE_URL}/executions/${executionId}`);
      check(response, {
        'Get execution status - Status 200': (r) => r.status === 200,
      });
      
      errorRate.add(response.status !== 200);
      responseTrend.add(response.timings.duration);
      
      // Get execution logs
      response = http.get(`${BASE_URL}/executions/${executionId}/logs?limit=10`);
      check(response, {
        'Get execution logs - Status 200': (r) => r.status === 200,
      });
      
      errorRate.add(response.status !== 200);
      responseTrend.add(response.timings.duration);
    }
  }
}

function testDashboardOperations() {
  const requests = [
    { name: 'Dashboard Stats', url: `${BASE_URL}/statistics/dashboard` },
    { name: 'Recent Executions', url: `${BASE_URL}/executions?limit=10` },
    { name: 'All Projects', url: `${BASE_URL}/projects` },
  ];
  
  for (const req of requests) {
    const response = http.get(req.url);
    
    check(response, {
      [`${req.name} - Status 200`]: (r) => r.status === 200,
      [`${req.name} - Response time < 300ms`]: (r) => r.timings.duration < 300,
    });
    
    errorRate.add(response.status !== 200);
    responseTrend.add(response.timings.duration);
  }
}

export function teardown(data) {
  // Cleanup test data
  console.log('Cleaning up test data...');
  
  const { projects } = data;
  
  for (const project of projects) {
    const response = http.del(`${BASE_URL}/projects/${project.id}`);
    console.log(`Deleted project ${project.id}: ${response.status}`);
  }
}

export function handleSummary(data) {
  return {
    'performance-results.json': JSON.stringify(data, null, 2),
    stdout: `
    Performance Test Summary:
    ========================
    
    Total Requests: ${data.metrics.http_reqs.values.count}
    Failed Requests: ${data.metrics.http_req_failed.values.rate * 100}%
    Average Response Time: ${data.metrics.http_req_duration.values.avg}ms
    95th Percentile: ${data.metrics.http_req_duration.values['p(95)']}ms
    
    Checks Passed: ${(data.metrics.checks.values.rate * 100).toFixed(2)}%
    
    Virtual Users: ${data.metrics.vus.values.value}
    Virtual Users Max: ${data.metrics.vus_max.values.value}
    
    Test Duration: ${(data.state.testRunDurationMs / 1000).toFixed(2)}s
    `,
  };
} 