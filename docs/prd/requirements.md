# **Requirements**

## **Functional**

* **FR1**: The system must store both FlowBook application builds and book datasets in a MinIO S3-compatible object storage.
* **FR2**: The system must allow users to upload book and application data as complete folders, preserving their directory structure.
* **FR3**: The Admin Panel must provide functionality to upload, list, soft-delete, and restore files/folders.
* **FR4**: Soft-deleted items must be moved to a separate `trash` bucket.
* **FR5**: Book data must be organized by publisher name (e.g., `publisher_name/books/book1/`).
* **FR6**: A dedicated API service shall provide endpoints for all data management operations (upload, download, list, etc.).
* **FR7**: All operations that modify data must be logged to create an audit trail.
* **FR8**: The system must support direct streaming of audio and video files via HTTP range requests.
* **FR9**: The Admin Panel must allow for viewing and editing of book metadata stored in the database.
* **FR10**: The Admin Panel must support uploading, listing, and managing Linux application builds alongside macOS and Windows releases.

## **Non-Functional**

* **NFR1**: The API service must be stateless to allow for future horizontal scaling.
* **NFR2**: All API endpoints must be protected using JWT authentication.
* **NFR3**: Items in the `trash` bucket must be retained for a 7-day period before being eligible for permanent deletion, and hard-delete workflows must enforce this window (allowing explicit overrides when authorised) while recording deletions in the audit log.
* **NFR4**: A daily or weekly backup of the storage system must be synced to a secondary location.
* **NFR5**: System health (disk usage, network, errors) must be monitored, for example with Prometheus/Grafana.
* **NFR6**: Consistency between the file system and database metadata must be maintained by ensuring all operations are performed via the API.

---
