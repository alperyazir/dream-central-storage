# **Epic List**

* **Epic 1: Core API & Project Foundation:** Establish the secure, authenticated API backbone with essential infrastructure, CI/CD, and basic book metadata management.
* **Epic 2: Storage Service Integration:** Implement the core file and folder management capabilities by integrating the API with the MinIO object storage.
* **Epic 3: Admin Panel MVP:** Develop the minimum viable React-based Admin Panel for administrators to log in, view, upload, and manage books and application builds.
* **Epic 4: Advanced Features & Production Readiness:** Implement the soft-delete/restore functionality and integrate the planned backup and monitoring solutions.
* **Epic 5: Storage UX & Stability Upgrades:** Streamline upload workflows, align storage versioning, harden session handling, and refresh the admin interface.
* **Epic 6: Storage Namespace Restructuring:** Rename books bucket to publishers for asset isolation, update path hierarchy, and activate teachers storage namespace.
* **Epic 7: Admin Panel - Teachers Integration:** Extend admin panel to manage teacher materials with upload, list, delete, and trash operations.
* **Epic 8: Publisher-Centric Domain Model with Normalized Schema:** Establish properly normalized database with publishers as first-class entities (FK relationship to books), dedicated publisher management, and dynamic asset management for publisher/teacher materials.
* **Epic 9: Publisher-Centric UI & Enhanced Uploads:** Transform the admin panel to publisher-centric navigation with dynamic content type management, enhanced upload dialogs, and improved file filtering (.fbinf, .bak).
* **Epic 10: AI Book Processing Pipeline:** Implement automated AI processing when books are uploaded. Extract text from PDFs, segment by pages/modules, use AI to extract topics and vocabulary, generate audio pronunciations, and store all data under `/ai-data/` for consumption by Dream LMS.

---
