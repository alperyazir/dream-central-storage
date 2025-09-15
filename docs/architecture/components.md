# Components

## 1. API Routers
**Responsibility**: Defines the HTTP endpoints, handles request and response validation using Pydantic, and routes incoming requests to the appropriate service. This is the public-facing entry point of our application.

**Key Interfaces**:  
`POST /apps`, `POST /books`, `GET /apps`, `GET /books`, `GET /apps/{version}`, `POST /packages`, `GET /books/{...}/summary`

**Dependencies**: Services / Business Logic

## 2. Services / Business Logic
**Responsibility**: Contains the core application logic. For example, the PackagingService will orchestrate fetching files from storage and zipping them, while an AssetService will handle the creation and retrieval of asset records from the database.

**Key Interfaces**:  
Functions like `create_application_build()`, `get_all_books()`, `package_assets()`, `get_book_summary()`.

**Dependencies**: Data Access Layer, Storage Client

## 3. Data Access Layer (Repositories)
**Responsibility**: Implements the Repository Pattern for all database interactions. This component will contain classes like `ApplicationBuildRepository` that abstract away the SQLAlchemy queries, providing simple methods like `get_by_version()` or `create()`.

**Key Interfaces**: CRUD-like functions (Create, Read, Update, Delete) for each data model.

**Dependencies**: Database / SQLAlchemy ORM

## 4. Storage Client
**Responsibility**: A dedicated module that encapsulates all interaction with the MinIO S3-compatible object store. It will handle uploading, downloading, and managing file paths (S3 keys).

**Key Interfaces**: Functions like `upload_file()`, `generate_presigned_download_url()`, `get_file_stream()`.

**Dependencies**: MinIO S3 Server

---
