# **Technical Assumptions**

## **Repository Structure: Monorepo**

* A **monorepo** structure will be used to simplify shared code and dependency management between the API, Admin Panel, and future applications.

## **Service Architecture: Scalable Monolith**

* A **scalable (or modular) monolith** is recommended for the initial version to speed up development while allowing for future migration to microservices.

## **Testing Requirements: Unit + Integration**

* The project will include both **unit and integration tests** to ensure code quality and system reliability.

## **Additional Technical Assumptions and Requests**

* **Backend Stack**: **Python** with the **FastAPI** framework will be used for the API service.
* **Frontend Stack**: **React** (with Vite and TypeScript) is the chosen framework for the Admin Panel.
* **Storage**: The system will use **MinIO** for S3-compatible object storage.
* **Authentication**: **JWT** will be used for securing the API service.
* **Monitoring**: **Prometheus/Grafana** will be the target for system monitoring.
* **Database**: **PostgreSQL** is recommended for storing book metadata.

---