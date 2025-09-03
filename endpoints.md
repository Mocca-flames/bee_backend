# Student Management API Documentation

## Overview
FastAPI-based student management system with SMS functionality for fee notifications and bulk messaging.

**Base URL**: `http://your-api-domain.com`  
**Version**: 0.1.0

---

## Authentication
This API currently does not require authentication based on the provided schema.

---

# Students Endpoints

## 1. Create Student
**POST** `/api/students/`

Creates a new student record.

### Request Body Schema
```javascript
{
  "name": "string",           // Required, 1-255 characters
  "grade": "string",          // Required
  "parent1_phone": "string",  // Required
  "parent2_phone": "string",  // Optional
  "fee_status": "string"      // Optional, defaults to "unpaid"
}
```

### JavaScript Request Example
```javascript
const createStudent = async (studentData) => {
  const response = await fetch('/api/students/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      name: "John Doe",
      grade: "10th",
      parent1_phone: "+1234567890",
      parent2_phone: "+0987654321",
      fee_status: "unpaid"
    })
  });
  
  if (response.ok) {
    const student = await response.json();
    return student;
  } else {
    throw new Error('Failed to create student');
  }
};
```

### Response Schema (201)
```javascript
{
  "id": "uuid",
  "name": "string",
  "grade": "string",
  "parent1_phone": "string",
  "parent2_phone": "string|null",
  "fee_status": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

---

## 2. Get Students List
**GET** `/api/students/`

Retrieves a list of students with optional grade filtering.

### Query Parameters
- `grade` (optional): Filter students by grade

### JavaScript Request Example
```javascript
const getStudents = async (grade = null) => {
  const url = grade ? `/api/students/?grade=${encodeURIComponent(grade)}` : '/api/students/';
  
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    }
  });
  
  if (response.ok) {
    const students = await response.json();
    return students;
  } else {
    throw new Error('Failed to fetch students');
  }
};
```

### Response Schema (200)
```javascript
[
  {
    "id": "uuid",
    "name": "string",
    "grade": "string",
    "parent1_phone": "string",
    "parent2_phone": "string|null",
    "fee_status": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
]
```

---

## 3. Get Single Student
**GET** `/api/students/{student_id}`

Retrieves a specific student by ID.

### Path Parameters
- `student_id` (required): Student UUID

### JavaScript Request Example
```javascript
const getStudent = async (studentId) => {
  const response = await fetch(`/api/students/${studentId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    }
  });
  
  if (response.ok) {
    const student = await response.json();
    return student;
  } else {
    throw new Error('Failed to fetch student');
  }
};
```

### Response Schema (200)
```javascript
{
  "id": "uuid",
  "name": "string",
  "grade": "string",
  "parent1_phone": "string",
  "parent2_phone": "string|null",
  "fee_status": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

---

## 4. Update Student
**PUT** `/api/students/{student_id}`

Updates a student record.

### Path Parameters
- `student_id` (required): Student UUID

### Request Body Schema
```javascript
{
  "name": "string|null",           // Optional, 1-255 characters if provided
  "grade": "string|null",          // Optional
  "parent1_phone": "string|null",  // Optional
  "parent2_phone": "string|null",  // Optional
  "fee_status": "string|null"      // Optional
}
```

### JavaScript Request Example
```javascript
const updateStudent = async (studentId, updateData) => {
  const response = await fetch(`/api/students/${studentId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      name: "Jane Doe",
      grade: "11th",
      fee_status: "paid"
    })
  });
  
  if (response.ok) {
    const student = await response.json();
    return student;
  } else {
    throw new Error('Failed to update student');
  }
};
```

### Response Schema (200)
```javascript
{
  "id": "uuid",
  "name": "string",
  "grade": "string",
  "parent1_phone": "string",
  "parent2_phone": "string|null",
  "fee_status": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

---

## 5. Delete Student
**DELETE** `/api/students/{student_id}`

Deletes a student record.

### Path Parameters
- `student_id` (required): Student UUID

### JavaScript Request Example
```javascript
const deleteStudent = async (studentId) => {
  const response = await fetch(`/api/students/${studentId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    }
  });
  
  if (response.ok) {
    return { success: true };
  } else {
    throw new Error('Failed to delete student');
  }
};
```

### Response
- **204**: No Content (Success)

---

## 6. Update Fee Status
**PATCH** `/api/students/{student_id}/fee-status`

Updates only the fee status of a student.

### Path Parameters
- `student_id` (required): Student UUID

### Query Parameters
- `fee_status` (required): New fee status ('paid' or 'unpaid')

### JavaScript Request Example
```javascript
const updateFeeStatus = async (studentId, feeStatus) => {
  const response = await fetch(`/api/students/${studentId}/fee-status?fee_status=${feeStatus}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    }
  });
  
  if (response.ok) {
    const student = await response.json();
    return student;
  } else {
    throw new Error('Failed to update fee status');
  }
};
```

### Response Schema (200)
```javascript
{
  "id": "uuid",
  "name": "string",
  "grade": "string",
  "parent1_phone": "string",
  "parent2_phone": "string|null",
  "fee_status": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

---

## 7. Get Student Statistics
**GET** `/api/students/statistics`

Retrieves summary statistics about students.

### JavaScript Request Example
```javascript
const getStudentStatistics = async () => {
  const response = await fetch('/api/students/statistics', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    }
  });
  
  if (response.ok) {
    const stats = await response.json();
    return stats;
  } else {
    throw new Error('Failed to fetch statistics');
  }
};
```

### Response Schema (200)
```javascript
{
  // Dynamic object with various statistics
  // Exact structure depends on implementation
}
```

---

## 8. Get Available Grades
**GET** `/api/students/grades`

Retrieves the list of available grades.

### JavaScript Request Example
```javascript
const getAvailableGrades = async () => {
  const response = await fetch('/api/students/grades', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    }
  });
  
  if (response.ok) {
    const grades = await response.json();
    return grades;
  } else {
    throw new Error('Failed to fetch grades');
  }
};
```

### Response Schema (200)
```javascript
[
  "string" // Array of grade strings
]
```

---

# SMS Endpoints

## 1. Send Fee Notification SMS
**POST** `/api/sms/fee-notification`

Sends fee status notification SMS to specific students' parents.

### Request Body Schema
```javascript
{
  "student_ids": ["uuid"],        // Required, array of student UUIDs
  "template_name": "string",      // Required, minimum 1 character
  "template_vars": {              // Optional, key-value pairs for template variables
    "key": "string"
  }
}
```

### JavaScript Request Example
```javascript
const sendFeeNotification = async (studentIds, templateName, templateVars = {}) => {
  const response = await fetch('/api/sms/fee-notification', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      student_ids: studentIds,
      template_name: templateName,
      template_vars: templateVars
    })
  });
  
  if (response.ok) {
    const result = await response.json();
    return result;
  } else {
    throw new Error('Failed to send fee notifications');
  }
};
```

### Response Schema (200)
```javascript
{
  // Dynamic response object
  // Structure depends on implementation
}
```

---

## 2. Send Bulk SMS
**POST** `/api/sms/bulk`

Sends bulk SMS messages to filtered groups of students' parents.

### Request Body Schema
```javascript
{
  "message": "string",           // Required, minimum 1 character
  "filters": {                   // Optional
    "grades": ["string"],        // Optional, array of grades to filter by
    "fee_status": "string"       // Optional, fee status filter
  },
  "use_primary_contact": boolean // Optional, defaults to true
}
```

### JavaScript Request Example
```javascript
const sendBulkSMS = async (message, filters = null, usePrimaryContact = true) => {
  const response = await fetch('/api/sms/bulk', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: message,
      filters: filters,
      use_primary_contact: usePrimaryContact
    })
  });
  
  if (response.ok) {
    const result = await response.json();
    return result;
  } else {
    throw new Error('Failed to send bulk SMS');
  }
};

// Example usage
const sendToUnpaidFees = () => {
  return sendBulkSMS(
    "Reminder: Your child's school fees are still pending. Please pay at your earliest convenience.",
    {
      grades: ["10th", "11th", "12th"],
      fee_status: "unpaid"
    },
    true
  );
};
```

### Response Schema (200)
```javascript
{
  // Dynamic response object
  // Structure depends on implementation
}
```

---

## 3. Get SMS History
**GET** `/api/sms/history`

Retrieves SMS history logs with filtering and pagination support.

### Query Parameters
- `student_id` (optional): UUID to filter logs by student ID
- `status` (optional): Filter logs by status (e.g., 'success', 'failed')
- `template_name` (optional): Filter logs by template name
- `skip` (optional): Number of logs to skip (default: 0)
- `limit` (optional): Maximum number of logs to return (default: 10)

### JavaScript Request Example
```javascript
const getSMSHistory = async (filters = {}) => {
  const params = new URLSearchParams();
  
  if (filters.student_id) params.append('student_id', filters.student_id);
  if (filters.status) params.append('status', filters.status);
  if (filters.template_name) params.append('template_name', filters.template_name);
  if (filters.skip) params.append('skip', filters.skip.toString());
  if (filters.limit) params.append('limit', filters.limit.toString());
  
  const url = `/api/sms/history${params.toString() ? '?' + params.toString() : ''}`;
  
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    }
  });
  
  if (response.ok) {
    const history = await response.json();
    return history;
  } else {
    throw new Error('Failed to fetch SMS history');
  }
};

// Example usage
const getFailedSMS = () => {
  return getSMSHistory({
    status: 'failed',
    limit: 20
  });
};
```

### Response Schema (200)
```javascript
[
  {
    "id": "uuid",
    "student_id": "uuid|null",
    "recipient_phone": "string",     // 10-12 characters
    "message_content": "string",     // Minimum 1 character
    "status": "string",              // Minimum 1 character
    "error_detail": "string|null",
    "is_bulk": boolean,              // Defaults to false
    "template_name": "string|null",
    "sent_at": "datetime"
  }
]
```

---

# Root Endpoint

## Health Check
**GET** `/`

Basic health check endpoint.

### JavaScript Request Example
```javascript
const healthCheck = async () => {
  const response = await fetch('/', {
    method: 'GET'
  });
  
  if (response.ok) {
    const result = await response.json();
    return result;
  } else {
    throw new Error('Health check failed');
  }
};
```

### Response Schema (200)
```javascript
{
  // Response structure depends on implementation
}
```

---

# Error Handling

## Validation Error (422)
All endpoints may return validation errors with the following structure:

```javascript
{
  "detail": [
    {
      "loc": ["string|integer"],  // Location of the error
      "msg": "string",            // Error message
      "type": "string"            // Error type
    }
  ]
}
```

## JavaScript Error Handling Example
```javascript
const handleAPIError = async (response) => {
  if (response.status === 422) {
    const errorData = await response.json();
    console.error('Validation errors:', errorData.detail);
    return errorData;
  } else {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
};

// Usage in API calls
const createStudentSafe = async (studentData) => {
  try {
    const response = await fetch('/api/students/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(studentData)
    });
    
    if (response.ok) {
      return await response.json();
    } else {
      return await handleAPIError(response);
    }
  } catch (error) {
    console.error('Network error:', error);
    throw error;
  }
};
```

---

# Complete JavaScript API Client Example

```javascript
class StudentManagementAPI {
  constructor(baseURL = '') {
    this.baseURL = baseURL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });

    if (!response.ok) {
      if (response.status === 422) {
        const errorData = await response.json();
        throw new ValidationError(errorData.detail);
      }
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.status === 204 ? null : await response.json();
  }

  // Students
  async createStudent(studentData) {
    return this.request('/api/students/', {
      method: 'POST',
      body: JSON.stringify(studentData)
    });
  }

  async getStudents(grade = null) {
    const query = grade ? `?grade=${encodeURIComponent(grade)}` : '';
    return this.request(`/api/students/${query}`);
  }

  async getStudent(studentId) {
    return this.request(`/api/students/${studentId}`);
  }

  async updateStudent(studentId, updateData) {
    return this.request(`/api/students/${studentId}`, {
      method: 'PUT',
      body: JSON.stringify(updateData)
    });
  }

  async deleteStudent(studentId) {
    return this.request(`/api/students/${studentId}`, {
      method: 'DELETE'
    });
  }

  async updateFeeStatus(studentId, feeStatus) {
    return this.request(`/api/students/${studentId}/fee-status?fee_status=${feeStatus}`, {
      method: 'PATCH'
    });
  }

  async getStatistics() {
    return this.request('/api/students/statistics');
  }

  async getGrades() {
    return this.request('/api/students/grades');
  }

  // SMS
  async sendFeeNotification(studentIds, templateName, templateVars = {}) {
    return this.request('/api/sms/fee-notification', {
      method: 'POST',
      body: JSON.stringify({
        student_ids: studentIds,
        template_name: templateName,
        template_vars: templateVars
      })
    });
  }

  async sendBulkSMS(message, filters = null, usePrimaryContact = true) {
    return this.request('/api/sms/bulk', {
      method: 'POST',
      body: JSON.stringify({
        message,
        filters,
        use_primary_contact: usePrimaryContact
      })
    });
  }

  async getSMSHistory(filters = {}) {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        params.append(key, value.toString());
      }
    });
    
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.request(`/api/sms/history${query}`);
  }
}

class ValidationError extends Error {
  constructor(details) {
    super('Validation Error');
    this.name = 'ValidationError';
    this.details = details;
  }
}

// Usage
const api = new StudentManagementAPI('http://your-api-domain.com');

// Examples
(async () => {
  try {
    // Create a student
    const newStudent = await api.createStudent({
      name: "John Doe",
      grade: "10th",
      parent1_phone: "+1234567890",
      fee_status: "unpaid"
    });
    
    // Send bulk SMS to unpaid students
    await api.sendBulkSMS(
      "Fee reminder: Please pay your outstanding fees.",
      { fee_status: "unpaid" }
    );
    
    // Get SMS history
    const smsHistory = await api.getSMSHistory({
      status: "success",
      limit: 50
    });
    
  } catch (error) {
    if (error instanceof ValidationError) {
      console.error('Validation errors:', error.details);
    } else {
      console.error('API Error:', error.message);
    }
  }
})();
```

This documentation provides complete endpoint information, request/response schemas, and JavaScript examples for interacting with your Student Management API.