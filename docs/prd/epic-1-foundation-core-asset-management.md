# Epic 1: Foundation & Core Asset Management
**Epic Goal:** The primary goal of this epic is to establish the complete foundational infrastructure and the core API functionalities for our asset management service. By the end of this epic, we will have a fully operational, secure API that can upload, store, version, and download application builds and book datasets, laying the groundwork for all future development.

## Story 1.1: Initial Project & API Setup
*As a developer, I want to set up the new Python FastAPI project with the correct structure and a basic health-check endpoint, so that we have a verifiable and deployable foundation for the API service.*
* **Acceptance Criteria:**
    1.  A new Git repository for the API service is created.
    2.  A new FastAPI project is initialized with a standard project structure.
    3.  A `/health` endpoint is created that returns a `200 OK` status with a simple JSON response (e.g., `{"status": "ok"}`).
    4.  The application can be run locally.

## Story 1.2: S3 Storage Integration
*As a developer, I want to configure the API to securely connect to the MinIO S3-compatible object store, so that the application can access the designated storage bucket for file operations.*
* **Acceptance Criteria:**
    1.  The API retrieves S3 connection credentials (endpoint, key, secret, bucket name) from environment variables.
    2.  The API includes a health check or startup process that verifies a successful connection to the S3 bucket.
    3.  Connection errors are properly logged.

## Story 1.3: Implement API Authentication Middleware
*As a developer, I want to implement a token-based authentication middleware, so that API endpoints can be secured and ready for future role-based access control (RBAC).*
* **Acceptance Criteria:**
    1.  A middleware is implemented that checks for a valid bearer token in the `Authorization` header of incoming requests.
    2.  Endpoints protected by the middleware return a `401 Unauthorized` or `403 Forbidden` error if a valid token is not provided.
    3.  The authentication system is designed to be easily extensible for RBAC in the future (e.g., by decoding roles from a JWT).

## Story 1.4: Upload Application Build
*As an administrator, I want to upload a FlowBook application build via a secure API endpoint, so that it can be stored and versioned in the central storage.*
* **Acceptance Criteria:**
    1.  A secure `POST /api/v1/apps` endpoint is created that requires authentication.
    2.  The endpoint accepts a file upload and a `version` tag.
    3.  Upon successful upload, the file is stored in the S3 bucket under a structured path (e.g., `apps/{version}/flowbook.zip`).
    4.  A success response is returned with the location and version of the stored file.

## Story 1.5: Upload Book Dataset
*As an administrator, I want to upload a FlowBook book dataset via a secure API endpoint, so that it can be stored with its version and lifecycle metadata.*
* **Acceptance Criteria:**
    1.  A secure `POST /api/v1/books` endpoint is created that requires authentication.
    2.  The endpoint accepts a file upload, a `version` tag, and a JSON payload for metadata (e.g., creation date, etc.).
    3.  The file is stored in the S3 bucket (e.g., `books/{book-id}/{version}/data.zip`).
    4.  The metadata is stored and associated with the book version.

## Story 1.6: List Asset Versions
*As a client application, I want to query API endpoints to see all available versions of applications and book datasets, so that I know what assets can be requested.*
* **Acceptance Criteria:**
    1.  A `GET /api/v1/apps` endpoint is created that returns a list of all available application build versions.
    2.  A `GET /api/v1/books` endpoint is created that returns a list of all available book datasets and their versions.

## Story 1.7: Download Application Build
*As a client application, I want to download a specific version of a FlowBook application build, so that it can be delivered to an end-user.*
* **Acceptance Criteria:**
    1.  A secure `GET /api/v1/apps/{version}` endpoint is created that requires authentication.
    2.  The endpoint returns the correct application build file from the S3 store.

---