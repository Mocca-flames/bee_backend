# School Management System

## Getting Started

### Prerequisites
- Docker
- Docker Compose

### Setup
1. Copy `.env.example` to `.env` and update with your BulkSMS credentials.
2. Build and start services:
   ```bash
   docker-compose up --build
   ```
3. Run database migrations (in a new terminal):
   ```bash
   docker-compose exec app alembic upgrade head
   ```

### Development
- Start services: `docker-compose up`
- Start in background: `docker-compose up -d`
- View logs: `docker-compose logs -f app`
- Access database: `docker-compose exec db psql -U school_admin -d school_management`
- Run shell in app container: `docker-compose exec app bash`
- Stop services: `docker-compose down`
- Reset database (destructive): `docker-compose down -v`