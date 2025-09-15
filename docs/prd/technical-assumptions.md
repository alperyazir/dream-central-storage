# Technical Assumptions

## Repository Structure: Polyrepo
The project will use a Polyrepo structure, with separate repositories for the core API service and for each future web application (LMS, Kanban Tracker). This approach provides strong ownership boundaries and independent deployment lifecycles for each part of the system.

## Service Architecture: Monolith
The initial backend API service will be developed as a single, unified application (a monolith). This simplifies the development process for the MVP, reduces deployment complexity, and is the fastest path to delivering the core functionality. The architecture will be designed with clear internal boundaries to allow for potential extraction into microservices in the future if scale demands it.

## Additional Technical Assumptions and Requests
* **Backend Language & Framework:** The backend API will be built using **Python** with the **FastAPI** framework.

---