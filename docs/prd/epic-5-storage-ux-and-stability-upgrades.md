# **Epic 5: Storage UX & Stability Upgrades**
**Epic Goal**: Deliver a smoother administrator experience for managing digital books and app builds while tightening platform stability. This epic focuses on streamlining upload workflows, expanding platform coverage, enforcing consistent storage versioning, improving destructive-action controls, hardening login persistence, and refreshing the admin interface with a modern, light turquoise palette.

## **Story 5.1: Flexible Book Upload Targeting**
**As an** administrator, **I want** the book upload flow to support both new titles and targeted updates, **so that** I can add fresh content without unnecessary selection steps while still being able to patch existing books.
**Acceptance Criteria:**
1. The admin panel upload modal offers a clear choice between creating a new book and updating an existing one; selecting "new" hides the target dropdown while "update" requires it.
2. Fresh book uploads succeed without providing an existing book identifier and return the new book metadata to the dashboard list within one refresh cycle.
3. Update uploads continue to require selecting an existing book and send the book identifier to the API as today.
4. API handlers support both flows, automatically creating metadata entries for new uploads and maintaining backward compatibility for updates.
5. New uploads must include a `config.json` file at the archive root; the backend maps keys like `publisher_name`/`book_title` to canonical metadata and emits warnings when legacy `metadata.json` is used as a fallback.

## **Story 5.2: Add Linux Platform Support for App Uploads**
**As an** administrator, **I want** to upload Linux application builds, **so that** the platform can distribute desktop apps across all supported operating systems.
**Acceptance Criteria:**
1. The app upload UI exposes Linux as a selectable platform alongside existing options (e.g., Windows, macOS).
2. Uploading a Linux build routes to a dedicated API endpoint or parameter that stores the folder under the `apps/linux` path.
3. Dashboard listings and download links surface Linux builds with appropriate platform badges.
4. Automated tests cover the Linux platform selection and confirm payloads include the correct platform metadata.

## **Story 5.3: Align Version Folder Names with Manifest Version File**
**As an** administrator, **I want** uploaded builds to use the version specified in the repo’s `data/version` file, **so that** storage folders match the official release numbering for both apps and books.
**Acceptance Criteria:**
1. When uploading an app or book, the service reads the `data/version` file at the root of the uploaded archive/folder.
2. The extracted version string becomes the folder name under the respective book or app directory instead of a random UUID.
3. If the version already exists, the system prevents overwriting without an explicit confirmation flag returned to the UI.
4. Validation covers absent or malformed `data/version` files, returning actionable error messages to the administrator.

## **Story 5.4: Simplify Dashboard Columns**
**As an** administrator, **I want** the listings to hide the raw storage path, **so that** the dashboard stays focused on actionable information.
**Acceptance Criteria:**
1. The "Storage Path" column is removed from both book and app tables in the admin panel UI.
2. Table layouts adjust responsively so remaining columns align without clipping or overflow.
3. Unit tests and snapshots are updated to reflect the new column structure.
4. Documentation (e.g., admin guide) is refreshed to remove references to the storage path column.

## **Story 5.5: Permanently Delete Items from Trash**
**As an** administrator, **I want** the trash view to offer permanent deletion, **so that** I can reclaim storage space when items are no longer needed.
**Acceptance Criteria:**
1. Each trash row includes a "Delete Permanently" control gated behind a confirmation modal.
2. Confirming the action removes the folder from object storage (MinIO) and deletes any related metadata records.
3. The UI refreshes the trash listing after deletion and surfaces success/error toasts.
4. Automated tests cover both successful deletion and failure scenarios (e.g., storage error).

## **Story 5.6: Persist Admin Sessions Across Refreshes**
**As an** administrator, **I want** to stay logged in after refreshing the page, **so that** I do not have to re-enter credentials repeatedly during active work.
**Acceptance Criteria:**
1. Auth tokens or session identifiers persist in a secure storage mechanism (e.g., HTTP-only cookie or encrypted localStorage) that survives page refresh.
2. On app initialization, persisted credentials are rehydrated and validated before showing the dashboard.
3. Sessions still expire according to existing backend policies (e.g., token TTL), and the UI handles expiry gracefully.
4. Security review confirms no regression against architecture guidelines for credential storage.

## **Story 5.7: Refresh the Admin UI with a Light Turquoise Palette**
**As an** administrator, **I want** a modernized UI with a light turquoise color scheme, **so that** the interface feels more polished and inviting.
**Acceptance Criteria:**
1. A revised design system (colors, typography, spacing) is documented and applied across primary layouts, tables, buttons, and modals.
2. The light turquoise palette becomes the dominant accent color while maintaining accessibility (WCAG AA for text/icons against backgrounds).
3. Global styles and component themes are updated without regressing existing functionality or layout responsiveness.
4. Screenshots or prototypes illustrating the new look are added to the design documentation for stakeholder review.

---

## **Story 5.9: Force Delete Overrides for Trash Items**
**As an** administrator, **I want** an authorised override for trash deletions within the retention window, **so that** I can immediately remove sensitive or erroneous uploads when compliance approvals exist.
**Acceptance Criteria:**
1. The trash UI surfaces an override flow for retention conflicts that is restricted to authenticated administrators and requires an explicit justification before retrying the delete.
2. Override attempts send `force=true` with the justification to the `DELETE /trash` API, bypassing the retention check while the default flow continues to enforce the seven-day window.
3. Forced deletions emit structured audit logs that include administrator id, target key, timestamp, override flag, and justification, satisfying FR7/NFR3 logging requirements.
4. UI feedback clearly differentiates forced deletions, refreshing the trash listing on success while showing the existing retention warning when the override is not used.
5. Automated tests cover forced deletion success, justification validation, retention conflicts without override, and regression of the default retention guard across backend and frontend layers.

## **Story 5.10: Trash Retention Visibility**
**As an** administrator, **I want** the trash view to highlight retention timelines, **so that** I understand when items can be deleted or when overrides are required.
**Acceptance Criteria:**
1. Trash listings include retention metadata (youngest object timestamp, eligibility timestamp, eligibility flag) sourced from the storage API.
2. UI surfaces countdown messaging for each entry, disabling default deletion until retention is satisfied while still allowing intentional overrides.
3. API responses log retention context and follow existing audit/error handling patterns.
4. Automated tests cover retention metadata serialization and UI messaging for both eligible and ineligible entries.

## **Story 5.11: Book Content Explorer Drawer**
**As an** administrator, **I want** to inspect a book’s folders and metadata in the admin panel, **so that** I can verify uploads and access key files without external tools.
**Acceptance Criteria:**
1. Book listings expose a content explorer panel that loads `config.json` metadata and the storage tree for the selected book.
2. The explorer renders a collapsible tree with download actions and consistent error messaging.
3. Metadata parsing reuses Story 5.8 logic and surfaces missing fields gracefully.
4. Automated tests cover drawer interactions, listing errors, and download triggers.

## **Story 5.12: Media Preview in Book Explorer**
**As an** administrator, **I want** inline previews for media assets, **so that** I can validate audio, video, and image uploads directly in the explorer.
**Acceptance Criteria:**
1. Supported images display inline previews; unsupported formats retain download-only behaviour.
2. Audio and video files stream through HTML5 players using the existing Range-enabled endpoints.
3. Preview failures show actionable feedback and fallback download controls.
4. Frontend tests exercise media selection, preview rendering, and error handling states.
