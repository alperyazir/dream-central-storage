# Requirements

## Functional
1.  **FR1**: The system must provide a secure API endpoint for uploading FlowBook application builds, tagging them with a version number.
2.  **FR2**: The system must provide a secure API endpoint for uploading book datasets, tagging them with a version number and associated metadata (including production lifecycle data like creation date, completion date, and edit history).
3.  **FR3**: The system must store the uploaded application builds and book datasets in an S3-compatible object store (MinIO).
4.  **FR4**: The system must provide API endpoints to list all available FlowBook application versions and all available book dataset versions.
5.  **FR5**: The system must provide an API endpoint to download a specific, versioned FlowBook application build.
6.  **FR6**: The system must provide an API endpoint that takes an application version and a book version as input, packages them together into a single distributable file, and provides a link for download.
7.  **FR7**: The system must provide an API endpoint that can inspect a given book dataset's `config.json` and return a summary of its contents, including the total number of pages and a count of activities grouped by type.

## Non Functional
1.  **NFR1**: All API endpoints must be secured using a token-based authentication mechanism.
2.  **NFR2**: The system architecture must be deployed on a VPS and be scalable to support the future LMS and Kanban tracker applications.
3.  **NFR3**: The API should include versioning from the start (e.g., `/api/v1/...`) to allow for future non-breaking changes.
4.  **NFR4**: The authentication system must be designed to be extensible for future role-based access control (RBAC) to support different user types (e.g., admin, teacher, student).
5.  **NFR5**: The object storage solution must be configured to support efficient streaming of large audio and video files.

---