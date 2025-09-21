# **Epic 2: Storage Service Integration**
**Epic Goal**: This epic implements the core file and folder management capabilities by integrating the API with the MinIO object storage. It will deliver the functionality for uploading, preserving, and listing the directory structures for both book datasets and application builds. Upon completion, the system will be able to physically store and retrieve the content managed by the metadata API from Epic 1.

## **Story 2.1: MinIO Service Connection & Bucket Setup**
**As a** developer, **I want** the API to connect to the MinIO storage service and ensure the necessary buckets exist, **so that** the application is ready to handle file storage operations.
**Acceptance Criteria:**
1.  The FastAPI application securely connects to the MinIO instance using credentials from environment variables.
2.  A utility script or an application startup event ensures the required buckets (`books`, `apps`, `trash`) are created if they don't already exist.
3.  The connection is robust and includes basic error handling for connectivity issues.

## **Story 2.2: Book Folder Upload Endpoint**
**As an** administrator, **I want** an API endpoint that can upload an entire book folder, **so that** I can add new book datasets to the system.
**Acceptance Criteria:**
1.  A new endpoint (e.g., `POST /books/{book_id}/upload`) is created to handle folder uploads.
2.  The endpoint accepts a folder structure and recursively uploads all files and sub-folders to the `books` bucket in MinIO.
3.  Files are stored under a path corresponding to their publisher and book name (e.g., `publisher_name/book_name/`).
4.  The endpoint returns a success message with a manifest of the uploaded files.
5.  The endpoint is protected and requires a valid JWT.

## **Story 2.3: Application Build Folder Upload Endpoint**
**As an** administrator, **I want** an API endpoint that can upload an application build folder, **so that** I can add new FlowBook application versions to the system.
**Acceptance Criteria:**
1.  A new endpoint (e.g., `POST /apps/{platform}/upload`) is created for app build uploads.
2.  The endpoint accepts a folder and uploads its contents to the `apps` bucket in MinIO.
3.  Files are stored under a path corresponding to their platform (e.g., `macOS/`, `windows/`).
4.  The endpoint is protected and requires a valid JWT.

## **Story 2.4: List Contents of Buckets/Folders**
**As an** administrator, **I want** to list the contents of books and application builds via the API, **so that** I can verify uploads and manage stored files.
**Acceptance Criteria:**
1.  An endpoint (e.g., `GET /storage/books/{publisher}/{book_name}`) is created to list the file structure of a specific book.
2.  An endpoint (e.g., `GET /storage/apps/{platform}`) is created to list the contents of a specific application build.
3.  The endpoints return a structured list of files and folders (e.g., a JSON tree).
4.  The endpoints are protected and require a valid JWT.

---