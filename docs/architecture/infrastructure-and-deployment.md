# Infrastructure and Deployment

## Infrastructure as Code
- **Tool**: Docker Compose
- **Location**: `docker-compose.yml` in the root of the project.
- **Approach**: We will use a single docker-compose.yml file to define all the services required to run our application: the FastAPI API, the PostgreSQL database, and the MinIO object store.

## Deployment Strategy
**Strategy**: Git Pull & Rebuild

**Process**:
1. SSH into the production VPS.
2. Navigate to the project directory.
3. Pull the latest changes from the main branch of the Git repository.
4. Run `docker-compose up --build -d` to rebuild the API container and restart services.

## Environments
- **Development**: Runs on a developer's local machine using `docker-compose up`.
- **Production**: A single VPS instance.

## Rollback Strategy
**Primary Method**: Git Revert. On the VPS, check out the previous stable Git commit/tag and re-run the `docker-compose up --build -d` command.

---
