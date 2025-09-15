# Tech Stack

## Cloud Infrastructure
- **Provider**: Self-hosted on a Virtual Private Server (VPS)
- **Key Services**: MinIO (S3-Compatible Object Store), PostgreSQL
- **Deployment Regions**: N/A (Single VPS instance initially)

## Technology Stack Table
| Category | Technology | Version | Purpose | Rationale |
| --- | --- | --- | --- | --- |
| Language | Python | 3.11.x | Primary development language | Modern, stable, and widely supported. |
| Framework | FastAPI | 0.103.x | Backend API framework | High performance, excellent async support, and native dependency injection. |
| Web Server | Uvicorn | 0.23.x | ASGI server for FastAPI | The standard, high-performance server for running FastAPI applications. |
| Database | PostgreSQL | 15.x | Primary relational database | Powerful, reliable, and works seamlessly with the chosen starter template. |
| Data Access (ORM) | SQLAlchemy | 2.0.x | Object-Relational Mapper | The de-facto ORM for Python, provides a robust way to interact with the DB. |
| DB Migrations | Alembic | 1.12.x | Database migration tool | Handles schema changes systematically. Included with the starter template. |
| Containerization | Docker | 24.0.x | Container runtime & tooling | Ensures a consistent environment for development and deployment. |
| File Storage | MinIO | Latest | S3-compatible object store | Provides the required S3 API for our assets, can be self-hosted on the VPS. |
| Testing | Pytest | 7.4.x | Testing framework | Standard for testing FastAPI applications; powerful and flexible. |

---
