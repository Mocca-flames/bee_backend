# School Management System - Backend Technical Plan

## 1. Project Structure
```
school_management/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── student.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── student.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── students.py
│   │       └── sms.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── sms_service.py
│   │   └── phone_validator.py
│   └── utils/
│       ├── __init__.py
│       └── logger.py
├── requirements.txt
├── .env
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── alembic/
└── README.md
```

## 2. Database Schema

### Students Table
```sql
CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    grade VARCHAR(10) NOT NULL CHECK (grade IN ('Grade R', 'Grade 1', 'Grade 2', 'Grade 3', 'Grade 4', 'Grade 5', 'Grade 6', 'Grade 7')),
    parent1_phone VARCHAR(12) NOT NULL, -- Stored in +27XXXXXXXXX format for SMS service compatibility
    parent2_phone VARCHAR(12), -- Optional backup contact, stored in +27XXXXXXXXX format
    fee_status VARCHAR(20) NOT NULL DEFAULT 'unpaid' CHECK (fee_status IN ('paid', 'unpaid')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_students_grade ON students(grade);
CREATE INDEX idx_students_fee_status ON students(fee_status);
CREATE INDEX idx_students_name ON students(name);
```

## 3. Docker Configuration

### Dockerfile
```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    restart: always
    environment:
      POSTGRES_USER: ${DB_USER:-school_admin}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-school_password}
      POSTGRES_DB: ${DB_NAME:-school_management}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-school_admin}"]
      interval: 30s
      timeout: 10s
      retries: 5

  app:
    build: .
    restart: always
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://${DB_USER:-school_admin}:${DB_PASSWORD:-school_password}@db:5432/${DB_NAME:-school_management}
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./app:/app/app:ro  # Mount for development
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

volumes:
  postgres_data:
```

## 4. Environment Variables (.env)
```
# Database
DB_USER=school_admin
DB_PASSWORD=school_password
DB_NAME=school_management
DATABASE_URL=postgresql://school_admin:school_password@db:5432/school_management

# BulkSMS Configuration
BULKSMS_USERNAME=your_username
BULKSMS_PASSWORD=your_password
BULKSMS_API_URL=https://api.bulksms.com/v1/messages

# Application Settings
DEBUG=True
LOG_LEVEL=INFO

# Docker Development
COMPOSE_PROJECT_NAME=school_management
```

## 5. API Endpoints

### Student Management
- `POST /api/students/` - Create new student
- `GET /api/students/` - List all students (with optional grade filter)
- `GET /api/students/{student_id}` - Get specific student
- `PUT /api/students/{student_id}` - Update student details
- `DELETE /api/students/{student_id}` - Delete student
- `PATCH /api/students/{student_id}/fee-status` - Update fee status only

### SMS Operations
- `POST /api/sms/fee-notification` - Send fee status SMS to specific students
- `POST /api/sms/bulk` - Send bulk SMS to filtered groups
- `GET /api/sms/history` - Get SMS sending history/logs

### Utility Endpoints
- `GET /api/students/grades` - Get list of available grades
- `GET /api/students/statistics` - Get summary stats (total students, fees paid/unpaid by grade)

## 6. Request/Response Schemas

### Student Creation/Update
```json
{
    "name": "John Doe",
    "grade": "Grade 5",
    "parent1_phone": "0821234567",
    "parent2_phone": "0837654321", // Optional
    "fee_status": "unpaid"
}
```

### Bulk SMS Request
```json
{
    "message": "Dear Parent, there will be a parent meeting on Friday...",
    "filters": {
        "grades": ["Grade 5", "Grade 6"], // Optional - if empty, sends to all
        "fee_status": "unpaid" // Optional - filter by fee status
    },
    "use_primary_contact": true // true = parent1_phone, false = both contacts
}
```

### Fee Notification Request
```json
{
    "student_ids": ["uuid1", "uuid2"],
    "message_template": "Dear Parent, {student_name} school fees are {fee_status}."
}
```

## 7. Core Services

### SMS Service Features
- BulkSMS API integration
- Phone number validation using your existing function (`_clean_and_validate_phone`) to ensure `+27XXXXXXXXX` format for compatibility with Telco services (BulkSMS, Twilio, etc.)
- Message templating with variables
- Batch processing for large recipient lists
- Error handling and retry logic
- SMS history logging

### Phone Validator Service
- Your existing SA phone validation function (`_clean_and_validate_phone`) which cleans, validates, and formats numbers to `+27XXXXXXXXX`.
- Additional methods for formatting display
- Bulk validation for multiple numbers

## 8. Key Models & Business Logic

### Student Model
- UUID primary key for security
- Grade validation (R-7 only)
- Phone number validation on save, ensuring `+27XXXXXXXXX` format
- Automatic timestamp updates
- Fee status management

### SMS Filtering Logic
- Grade-based filtering
- Fee status filtering
- Combined filters support
- Primary vs all contacts selection

## 9. Implementation Phases

### Phase 1: Docker Setup & Core Infrastructure
- Docker containerization setup
- PostgreSQL database container
- FastAPI project structure
- Basic database connection and models
- Environment configuration

### Phase 2: Student Management
- Complete CRUD operations for students
- Phone validation integration
- Data validation and error handling
- Basic logging setup

### Phase 3: SMS Integration
- BulkSMS service implementation
- Fee notification endpoints
- Basic bulk SMS functionality
- SMS error handling and logging

### Phase 4: Advanced SMS Features & Polish
- Grade and fee status filtering
- Message templating system
- SMS history and comprehensive logging
- API documentation (Swagger)
- Performance optimization

## 10. Docker Development Workflow

### Getting Started
```bash
# Clone repository
git clone <repo-url>
cd school_management

# Copy environment file
cp .env.example .env
# Edit .env with your BulkSMS credentials

# Build and start services
docker-compose up --build

# Run database migrations (in new terminal)
docker-compose exec app alembic upgrade head
```

### Development Commands
```bash
# Start services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f app

# Access database
docker-compose exec db psql -U school_admin -d school_management

# Run shell in app container
docker-compose exec app bash

# Stop services
docker-compose down

# Reset database (destructive)
docker-compose down -v
```

## 11. Technology Stack

### Core Framework
- **FastAPI** - Modern, fast web framework
- **SQLAlchemy** - ORM for database operations
- **Alembic** - Database migrations
- **Pydantic** - Data validation and serialization

### Database
- **PostgreSQL** - Robust relational database
- **asyncpg** - Async PostgreSQL driver

### SMS & External APIs
- **requests** - HTTP client for BulkSMS API
- **python-multipart** - Form data handling

### Containerization
- **Docker** - Application containerization
- **Docker Compose** - Multi-service orchestration
- **PostgreSQL 15** - Database container

### Development & Utilities
- **python-dotenv** - Environment variable management
- **loguru** - Advanced logging
- **pytest** - Testing framework

## 12. Security Considerations

### Basic Security Measures
- Environment variable protection
- Input validation and sanitization
- SQL injection prevention via ORM
- Basic rate limiting for SMS endpoints
- Secure phone number storage

### Authentication (Simple)
- Single admin token via environment variable
- Header-based authentication
- No complex user management needed

## 13. Error Handling Strategy

### SMS Errors
- Failed sends logged with recipient details
- Retry mechanism for temporary failures
- Admin notification for critical errors
- Graceful degradation for partial failures

### Database Errors
- Constraint violation handling
- Connection error recovery
- Data validation errors
- Detailed error logging

## 14. Monitoring & Logging

### Log Categories
- Student CRUD operations
- SMS sending attempts and results
- API request/response logging
- Error tracking and alerts

### Metrics to Track
- SMS delivery rates
- API response times
- Database query performance
- Error frequency by type

This plan provides a solid foundation for your MVP while keeping it simple and focused on your core requirements. The modular structure allows for easy expansion as needs grow.
