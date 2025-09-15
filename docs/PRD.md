# Dream Central Storage Product Requirements Document (PRD)

## Goals and Background Context

### Goals
* **Decouple** the FlowBook application builds from the book data to eliminate the inefficient and error-prone process of repackaging content with every new app release.
* **Centralize** all application builds and book datasets into a single, version-controlled storage system that acts as the single source of truth.
* **Develop** a core API service to manage the lifecycle of these assets, including uploads, versioning, packaging, and downloads.
* **Establish** a scalable foundation to support future web applications, specifically a Learning Management System (LMS) and a Kanban-based production tracker.

### Background Context
The current production workflow for FlowBook is a manual, email-based process that lacks visibility and control. The most significant operational pain point is the tight coupling of the FlowBook application and its content. Every new application version requires all existing book datasets to be manually repackaged and redeployed, a time-consuming and unsustainable model.

The proposed solution is to create a central storage system (internally named "Dream Central Storage") that cleanly separates the application from its data. This system, powered by a MinIO S3-compatible service and a custom API, will manage all assets independently. This foundational change not only solves the immediate repackaging problem but also enables the development of future systems, such as an LMS for schools and a production tracker to streamline the book creation lifecycle.

### Change Log
| Date | Version | Description | Author |
| :--- | :--- | :--- | :--- |
| 2025-09-15 | 1.0 | Initial PRD Draft | John |

---
## Requirements

### Functional
1.  **FR1**: The system must provide a secure API endpoint for uploading FlowBook application builds, tagging them with a version number.
2.  **FR2**: The system must provide a secure API endpoint for uploading book datasets, tagging them with a version number and associated metadata (including production lifecycle data like creation date, completion date, and edit history).
3.  **FR3**: The system must store the uploaded application builds and book datasets in an S3-compatible object store (MinIO).
4.  **FR4**: The system must provide API endpoints to list all available FlowBook application versions and all available book dataset versions.
5.  **FR5**: The system must provide an API endpoint to download a specific, versioned FlowBook application build.
6.  **FR6**: The system must provide an API endpoint that takes an application version and a book version as input, packages them together into a single distributable file, and provides a link for download.
7.  **FR7**: The system must provide an API endpoint that can inspect a given book dataset's `config.json` and return a summary of its contents, including the total number of pages and a count of activities grouped by type.

### Non Functional
1.  **NFR1**: All API endpoints must be secured using a token-based authentication mechanism.
2.  **NFR2**: The system architecture must be deployed on a VPS and be scalable to support the future LMS and Kanban tracker applications.
3.  **NFR3**: The API should include versioning from the start (e.g., `/api/v1/...`) to allow for future non-breaking changes.
4.  **NFR4**: The authentication system must be designed to be extensible for future role-based access control (RBAC) to support different user types (e.g., admin, teacher, student).
5.  **NFR5**: The object storage solution must be configured to support efficient streaming of large audio and video files.

---
## Technical Assumptions

### Repository Structure: Polyrepo
The project will use a Polyrepo structure, with separate repositories for the core API service and for each future web application (LMS, Kanban Tracker). This approach provides strong ownership boundaries and independent deployment lifecycles for each part of the system.

### Service Architecture: Monolith
The initial backend API service will be developed as a single, unified application (a monolith). This simplifies the development process for the MVP, reduces deployment complexity, and is the fastest path to delivering the core functionality. The architecture will be designed with clear internal boundaries to allow for potential extraction into microservices in the future if scale demands it.

### Additional Technical Assumptions and Requests
* **Backend Language & Framework:** The backend API will be built using **Python** with the **FastAPI** framework.

---
## Epic List

1.  **Epic 1: Foundation & Core Asset Management:** Establish the project infrastructure, API, and core storage functionality for uploading, listing, and downloading individual assets.
2.  **Epic 2: Advanced Packaging & Intelligence:** Implement the core business logic for packaging apps with book data and inspecting book contents on demand.

---
## Epic 1: Foundation & Core Asset Management
**Epic Goal:** The primary goal of this epic is to establish the complete foundational infrastructure and the core API functionalities for our asset management service. By the end of this epic, we will have a fully operational, secure API that can upload, store, version, and download application builds and book datasets, laying the groundwork for all future development.

### Story 1.1: Initial Project & API Setup
*As a developer, I want to set up the new Python FastAPI project with the correct structure and a basic health-check endpoint, so that we have a verifiable and deployable foundation for the API service.*
* **Acceptance Criteria:**
    1.  A new Git repository for the API service is created.
    2.  A new FastAPI project is initialized with a standard project structure.
    3.  A `/health` endpoint is created that returns a `200 OK` status with a simple JSON response (e.g., `{"status": "ok"}`).
    4.  The application can be run locally.

### Story 1.2: S3 Storage Integration
*As a developer, I want to configure the API to securely connect to the MinIO S3-compatible object store, so that the application can access the designated storage bucket for file operations.*
* **Acceptance Criteria:**
    1.  The API retrieves S3 connection credentials (endpoint, key, secret, bucket name) from environment variables.
    2.  The API includes a health check or startup process that verifies a successful connection to the S3 bucket.
    3.  Connection errors are properly logged.

### Story 1.3: Implement API Authentication Middleware
*As a developer, I want to implement a token-based authentication middleware, so that API endpoints can be secured and ready for future role-based access control (RBAC).*
* **Acceptance Criteria:**
    1.  A middleware is implemented that checks for a valid bearer token in the `Authorization` header of incoming requests.
    2.  Endpoints protected by the middleware return a `401 Unauthorized` or `403 Forbidden` error if a valid token is not provided.
    3.  The authentication system is designed to be easily extensible for RBAC in the future (e.g., by decoding roles from a JWT).

### Story 1.4: Upload Application Build
*As an administrator, I want to upload a FlowBook application build via a secure API endpoint, so that it can be stored and versioned in the central storage.*
* **Acceptance Criteria:**
    1.  A secure `POST /api/v1/apps` endpoint is created that requires authentication.
    2.  The endpoint accepts a file upload and a `version` tag.
    3.  Upon successful upload, the file is stored in the S3 bucket under a structured path (e.g., `apps/{version}/flowbook.zip`).
    4.  A success response is returned with the location and version of the stored file.

### Story 1.5: Upload Book Dataset
*As an administrator, I want to upload a FlowBook book dataset via a secure API endpoint, so that it can be stored with its version and lifecycle metadata.*
* **Acceptance Criteria:**
    1.  A secure `POST /api/v1/books` endpoint is created that requires authentication.
    2.  The endpoint accepts a file upload, a `version` tag, and a JSON payload for metadata (e.g., creation date, etc.).
    3.  The file is stored in the S3 bucket (e.g., `books/{book-id}/{version}/data.zip`).
    4.  The metadata is stored and associated with the book version.

### Story 1.6: List Asset Versions
*As a client application, I want to query API endpoints to see all available versions of applications and book datasets, so that I know what assets can be requested.*
* **Acceptance Criteria:**
    1.  A `GET /api/v1/apps` endpoint is created that returns a list of all available application build versions.
    2.  A `GET /api/v1/books` endpoint is created that returns a list of all available book datasets and their versions.

### Story 1.7: Download Application Build
*As a client application, I want to download a specific version of a FlowBook application build, so that it can be delivered to an end-user.*
* **Acceptance Criteria:**
    1.  A secure `GET /api/v1/apps/{version}` endpoint is created that requires authentication.
    2.  The endpoint returns the correct application build file from the S3 store.

---
## Epic 2: Advanced Packaging & Intelligence
**Epic Goal:** The goal of this epic is to build upon our core asset storage by adding the key business logic that solves your primary pain points. By the end of this epic, client applications will be able to request dynamically packaged application/book combinations and retrieve intelligent summaries about book contents, completing the MVP feature set.

### Story 2.1: Implement Book Content Inspection
*As an administrator, I want to request a summary of a book dataset's contents via the API, so that I can quickly see its composition without downloading it.*
* **Acceptance Criteria:**
    1.  A secure `GET /api/v1/books/{book-id}/{version}/summary` endpoint is created.
    2.  The endpoint retrieves the `config.json` for the specified book version from the S3 store.
    3.  The API parses the `config.json` and returns a JSON response containing the total page count and a count of activities grouped by type.
    4.  If the `config.json` is missing or malformed, a relevant error is returned.

### Story 2.2: Implement Asset Packaging Logic
*As a developer, I want to create a service that can take a specific application build and book dataset from storage and package them into a single distributable ZIP file, so that they can be delivered together to end-users.*
* **Acceptance Criteria:**
    1.  A packaging function is created that accepts an application version and a book version as input.
    2.  The function fetches the corresponding files from the S3 store.
    3.  It creates a structured ZIP file containing both the application and the book data.
    4.  The final ZIP file is stored in a temporary or dedicated location in S3.
    5.  The function returns the location of the newly created package.

### Story 2.3: Create Packaging API Endpoint
*As a client application, I want to request that an application build and a book dataset be packaged together via a secure API endpoint, so that I can initiate the creation of a distributable file for a user.*
* **Acceptance Criteria:**
    1.  A secure `POST /api/v1/packages` endpoint is created that requires authentication.
    2.  The endpoint accepts an `app_version` and a `book_version` in its request body.
    3.  The endpoint triggers the asset packaging logic (from Story 2.2).
    4.  Upon successful packaging, the endpoint returns a `201 Created` response containing a URL from which the package can be downloaded.

---
## Checklist Results Report
This PRD has been validated against the BMad PM Requirements Checklist. The document is considered complete and robust. Key strengths include a well-defined MVP scope, clear alignment between goals and requirements, and a logically sequenced epic/story structure. The PRD is approved and ready for the architectural design phase.

---
## Next Steps

### UX Expert Prompt
As this MVP is focused on the backend API and storage service, there is no immediate handoff to the UX Expert. The design process for the future LMS and Kanban web applications will be handled in their respective planning phases.

### Architect Prompt
This Product Requirements Document is complete. Please review it thoroughly, paying close attention to the Requirements and Technical Assumptions sections. Your task is to create the corresponding Architecture Document that provides a complete technical blueprint for the development team.