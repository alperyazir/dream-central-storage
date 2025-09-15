# Source Tree
```plaintext
dream-central-storage-api/
├── alembic/                   # Database migration scripts (Alembic)
├── app/
│   ├── api/                   # API Endpoints (Routers)
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── assets.py      # Routers for /apps and /books
│   │       │   └── packages.py    # Router for /packages
│   │       └── deps.py          # FastAPI dependencies (e.g., for auth)
│   ├── core/                  # Core application settings (e.g., config)
│   ├── crud/                  # Data Access Layer (Repositories)
│   │   ├── crud_app_build.py
│   │   └── crud_book_dataset.py
│   ├── db/                    # Database session management
│   ├── models/                # SQLAlchemy Data Models
│   │   ├── application_build.py
│   │   └── book_dataset.py
│   ├── schemas/               # Pydantic schemas (for API validation)
│   ├── services/              # Business Logic
│   │   ├── packaging_service.py # Logic for zipping files
│   │   └── storage_service.py   # Logic for interacting with MinIO
│   ├── tests/                 # All application tests
│   └── main.py                # Main FastAPI application entrypoint
├── docker-compose.yml         # Docker configuration
├── Dockerfile                 # Application Dockerfile
└── requirements.txt           # Python package dependencies
```

---
