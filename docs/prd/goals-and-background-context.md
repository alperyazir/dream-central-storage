# Goals and Background Context

## Goals
* **Decouple** the FlowBook application builds from the book data to eliminate the inefficient and error-prone process of repackaging content with every new app release.
* **Centralize** all application builds and book datasets into a single, version-controlled storage system that acts as the single source of truth.
* **Develop** a core API service to manage the lifecycle of these assets, including uploads, versioning, packaging, and downloads.
* **Establish** a scalable foundation to support future web applications, specifically a Learning Management System (LMS) and a Kanban-based production tracker.

## Background Context
The current production workflow for FlowBook is a manual, email-based process that lacks visibility and control. The most significant operational pain point is the tight coupling of the FlowBook application and its content. Every new application version requires all existing book datasets to be manually repackaged and redeployed, a time-consuming and unsustainable model.

The proposed solution is to create a central storage system (internally named "Dream Central Storage") that cleanly separates the application from its data. This system, powered by a MinIO S3-compatible service and a custom API, will manage all assets independently. This foundational change not only solves the immediate repackaging problem but also enables the development of future systems, such as an LMS for schools and a production tracker to streamline the book creation lifecycle.

## Change Log
| Date | Version | Description | Author |
| :--- | :--- | :--- | :--- |
| 2025-09-15 | 1.0 | Initial PRD Draft | John |

---