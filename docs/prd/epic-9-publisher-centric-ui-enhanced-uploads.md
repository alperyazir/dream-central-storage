# **Epic 9: Publisher-Centric UI & Enhanced Uploads**

**Epic Goal**: Transform the admin panel to a publisher-centric navigation model with dynamic content type management and improved file upload filtering.

**Priority**: HIGH - Builds on Epic 8's normalized schema to deliver the intended UX.

**Dependencies**: Epic 8 (Stories 8.1-8.3 backend work must be complete)

---

## **Background**

Epic 8 established the database foundation with publishers as first-class entities (normalized schema with FK relationships). The backend now has:
- `publishers` table with full CRUD API endpoints
- `books` table with `publisher_id` foreign key
- Publisher repository with relationship queries

However, the frontend still uses the original flat navigation (Dashboard → Books → Apps → Teachers → Trash) and the upload dialogs don't leverage the new publisher-centric model. This epic delivers the UI transformation to match the backend architecture.

**Current State:**
- Sidebar: Flat navigation with "Books" as a standalone section
- Upload: BookUploadDialog uploads ZIPs, auto-detects publisher from config.json
- File filtering: Filters macOS junk (._*, .DS_Store, __MACOSX) but NOT `.fbinf` or `.bak` files

**Target State:**
- Sidebar: Publisher list as primary navigation, expandable to show content types
- Upload: Select publisher → Select content type → Upload with validation
- File filtering: Also filters `.fbinf` and `.bak` files from ZIP archives

---

## **Story 9.1: Publisher-Centric Sidebar Navigation**

**As an** administrator, **I want** the sidebar to show publishers as the primary navigation, **so that** I can quickly access any publisher's content without going through filters.

**Acceptance Criteria:**

1. Left sidebar restructured with collapsible "Publishers" section showing:
   - List of all publishers (fetched from `/api/publishers/`)
   - Each publisher item expandable to show content types (Books, Assets)
   - Click publisher name → navigates to publisher detail view
   - Visual indicator for publisher status (active/inactive)

2. Publisher detail page created at `/publishers/:publisherId`:
   - Shows publisher metadata (name, display_name, description, logo, contact)
   - Tabs or sections for: Books, Assets (future: grouped by asset type)
   - "Upload" button context-aware to this publisher
   - Edit publisher metadata inline or via modal

3. Navigation structure:
   ```
   Dashboard
   Publishers (collapsible)
     ├── Universal ELT
     │   ├── Books (3)
     │   └── Assets (5)
     ├── Oxford Press
     │   ├── Books (12)
     │   └── Assets (2)
     └── + Add Publisher
   Teachers
   Trash
   ```

4. "Books" top-level nav item behavior changed:
   - Option A: Remove entirely (access books via publisher)
   - Option B: Keep as "All Books" aggregate view with publisher column
   - **Recommend Option B** for backward compatibility

5. Frontend API client created: `lib/publishers.ts`
   - `fetchPublishers()` - List all publishers
   - `fetchPublisher(id)` - Get single publisher
   - `createPublisher(data)` - Create new publisher
   - `updatePublisher(id, data)` - Update publisher
   - `deletePublisher(id)` - Soft-delete publisher

6. TypeScript interfaces:
   ```typescript
   interface Publisher {
     id: number;
     name: string;
     display_name: string | null;
     description: string | null;
     logo_url: string | null;
     contact_email: string | null;
     status: 'active' | 'inactive' | 'suspended';
     created_at: string;
     updated_at: string;
   }
   ```

7. Sidebar state persisted (expanded/collapsed publishers) in localStorage.

8. Mobile-responsive: Publishers list collapses to icons on small screens.

**Technical Notes:**
- Use React Router nested routes: `/publishers/:id`, `/publishers/:id/books`, `/publishers/:id/assets`
- Consider virtualized list if publisher count exceeds 50
- Publisher logo displayed as avatar in sidebar list
- Loading skeleton while fetching publishers

---

## **Story 9.2: Enhanced Upload Dialog with Content Type Selector**

**As an** administrator, **I want** the upload dialog to let me select publisher and content type before uploading, **so that** files are organized correctly without relying on auto-detection.

**Acceptance Criteria:**

1. New `PublisherUploadDialog` component with stepped flow:
   ```
   Step 1: Select Publisher (dropdown/autocomplete from API)
   Step 2: Select Content Type (Books | Materials | Logos | + Add New)
   Step 3: Select Files (drag & drop or file picker)
   Step 4: Confirm & Upload
   ```

2. Content type selector behavior:
   - Predefined types: "Books", "Materials", "Logos"
   - "Add New Type" option opens text input
   - New types validated: alphanumeric, hyphens, underscores only (`^[a-z0-9_-]+$`)
   - Reserved names blocked: "trash", "temp", "books" (for asset uploads)

3. Upload routing based on content type:
   - **Books**: Uses existing `/api/storage/books/upload` (ZIP with config.json)
   - **Other types**: Uses new `/api/publishers/{id}/assets/{type}` endpoint (Story 9.4 dependency)

4. Validation rules per content type:
   | Type | Accepted Formats | Max Size | Notes |
   |------|-----------------|----------|-------|
   | Books | .zip | 500MB | Must contain config.json |
   | Materials | .pdf, .docx, .pptx, images, audio, video | 100MB | Single files |
   | Logos | .png, .jpg, .svg | 5MB | Images only |
   | Custom | All common formats | 100MB | Default rules |

5. When opened from publisher detail page:
   - Publisher pre-selected and locked
   - Skip to Step 2

6. Upload progress shown per-file for multi-file uploads.

7. Success feedback shows: Publisher name, content type, file path in storage.

8. Error handling:
   - Invalid file type → Show allowed types for selected content type
   - File too large → Show max size for content type
   - Publisher not selected → Disable upload button

**Technical Notes:**
- Reuse existing drag-drop styling from `BookUploadDialog`
- Content type icons: Books (MenuBook), Materials (Description), Logos (Image), Custom (Folder)
- Consider Stepper component from MUI for visual flow

---

## **Story 9.3: Filter Unwanted Files from ZIP Uploads**

**As a** system administrator, **I want** ZIP uploads to automatically filter out `.fbinf` and `.bak` files, **so that** storage isn't cluttered with unnecessary backup/index files.

**Acceptance Criteria:**

1. `iter_zip_entries()` in `apps/api/app/services/storage.py` updated to skip:
   - Files ending with `.fbinf` (FlowPaper index files)
   - Files ending with `.bak` (backup files)
   - Files ending with `.tmp` (temporary files)

2. Filtering is case-insensitive (`.BAK`, `.Bak`, `.bak` all filtered).

3. Filtered files logged at DEBUG level for troubleshooting:
   ```python
   logger.debug("Skipping backup/temp file: %s", entry.filename)
   ```

4. Existing macOS filtering unchanged:
   - `__MACOSX/` folders
   - `.DS_Store` files
   - `._*` resource fork files

5. Unit tests added for new filtering:
   - Test ZIP with `.fbinf` file → not in manifest
   - Test ZIP with `.bak` file → not in manifest
   - Test ZIP with `.BAK` file (uppercase) → not in manifest
   - Test ZIP with legitimate files → all in manifest

6. No breaking changes to existing upload behavior.

**Technical Notes:**
- Add to existing skip logic in `iter_zip_entries()` function
- Pattern: `entry.filename.lower().endswith(('.fbinf', '.bak', '.tmp'))`
- Consider making the filter list configurable via settings (future enhancement)

---

## **Story 9.4: Asset Management API Endpoints**

**As an** API consumer, **I want** endpoints to upload and manage publisher assets by type, **so that** the frontend can support dynamic content type uploads.

**Acceptance Criteria:**

1. New endpoints in `app/routers/publishers.py`:

   ```
   GET  /publishers/{publisher_id}/assets
        → List all asset types with file counts

   GET  /publishers/{publisher_id}/assets/{asset_type}
        → List files in specific asset type

   POST /publishers/{publisher_id}/assets/{asset_type}
        → Upload file to asset type (creates folder if needed)

   DELETE /publishers/{publisher_id}/assets/{asset_type}/{filename}
        → Soft-delete file to trash
   ```

2. Storage path structure:
   ```
   publishers/
     {publisher_name}/
       books/           ← Existing book content
         {book_name}/
       assets/          ← New asset structure
         materials/
           worksheet1.pdf
         logos/
           logo.png
         {custom_type}/
           file.ext
   ```

3. Asset type validation:
   - Pattern: `^[a-z0-9_-]{1,50}$`
   - Reserved names rejected: `books`, `trash`, `temp`
   - Returns 400 Bad Request for invalid asset type

4. `GET /publishers/{id}/assets` response:
   ```json
   {
     "publisher_id": 1,
     "publisher_name": "Universal ELT",
     "asset_types": [
       {"name": "materials", "file_count": 5, "total_size": 15000000},
       {"name": "logos", "file_count": 2, "total_size": 50000}
     ]
   }
   ```

5. `POST /publishers/{id}/assets/{type}` behavior:
   - Creates `assets/{type}/` folder if doesn't exist
   - Validates file against content type rules (if defined)
   - Returns uploaded file metadata

6. Delete moves to trash with metadata:
   ```
   trash/publishers/{publisher_name}/assets/{type}/{filename}
   ```

7. Trash listing (`list_trash_entries`) updated to recognize asset items:
   - `item_type: "publisher_asset"`
   - `metadata: {"publisher": "...", "asset_type": "...", "filename": "..."}`

8. All endpoints require authentication (existing `_require_admin` pattern).

9. Tests added for all new endpoints.

**Technical Notes:**
- Reuse MinIO client from existing storage service
- Asset type folder created on first upload (lazy creation)
- Consider adding `GET /publishers/{id}/assets/{type}/{filename}` for presigned download URL

---

## **Compatibility Requirements**

- [ ] Existing "Books" page continues to work (Option B: aggregate view)
- [ ] Existing book upload flow unchanged (auto-detect still works)
- [ ] No database schema changes required (builds on Epic 8)
- [ ] Storage paths backward compatible with Epic 6 structure
- [ ] API changes are additive (no breaking changes)

## **Risk Mitigation**

- **Primary Risk:** Navigation change confuses existing users
- **Mitigation:**
  - Keep "Books" as aggregate view initially
  - Add tooltip/onboarding for new publisher navigation
  - Gradual rollout: publisher sidebar collapsed by default

- **Secondary Risk:** Asset upload performance with large files
- **Mitigation:**
  - Chunked upload for files > 10MB
  - Progress indicator per file
  - Cancel upload capability

## **Definition of Done**

- [ ] All 4 stories completed with acceptance criteria met
- [ ] Publisher-centric sidebar functional and responsive
- [ ] Upload dialog supports publisher + content type selection
- [ ] ZIP uploads filter .fbinf, .bak, .tmp files
- [ ] Asset management endpoints functional
- [ ] All existing tests pass
- [ ] New tests added for all new functionality
- [ ] No console errors or TypeScript compilation errors
- [ ] Code review completed

---

## **Story Manager Handoff**

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This builds on Epic 8's normalized publisher schema (backend complete)
- Focus is UI transformation + upload enhancement + file filtering
- Navigation change is significant UX shift - consider progressive disclosure
- Asset endpoints follow existing patterns in storage.py and publishers.py
- File filtering is backend-only change in storage service

Integration points:
- Frontend: React + TypeScript + MUI components
- Backend: FastAPI + MinIO storage
- Existing patterns: BookUploadDialog, TeacherUploadDialog for upload UI

Story sequence:
1. Story 9.3 (file filtering) - backend only, can start immediately
2. Story 9.4 (asset API) - backend, enables Story 9.2
3. Story 9.1 (sidebar) - frontend, can start in parallel with 9.4
4. Story 9.2 (upload dialog) - frontend, depends on 9.4

The epic delivers the publisher-centric UX promised by Epic 8's architecture."

---

## **Architecture Notes**

### Navigation State Management

The publisher sidebar state (expanded/collapsed items) should be managed via:
- React Context for runtime state
- localStorage for persistence across sessions
- URL params for deep-linking to expanded publishers

### Upload Dialog State Machine

```
IDLE → SELECTING_PUBLISHER → SELECTING_TYPE → SELECTING_FILES → UPLOADING → SUCCESS/ERROR
```

Consider using XState or useReducer for complex state transitions.

### File Filtering Strategy

Current filtering in `iter_zip_entries()`:
```python
# Skip macOS
if "/__MACOSX/" in normalized_path or normalized_path.startswith("__MACOSX/"):
    continue
if os.path.basename(normalized_path) == ".DS_Store":
    continue
if os.path.basename(normalized_path).startswith("._"):
    continue

# NEW: Skip backup/temp files
if normalized_path.lower().endswith(('.fbinf', '.bak', '.tmp')):
    continue
```
