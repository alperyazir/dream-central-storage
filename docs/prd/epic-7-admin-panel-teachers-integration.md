# **Epic 7: Admin Panel - Teachers & Storage Namespace Integration**

**Epic Goal**: Extend the admin panel frontend to support teacher materials management and provide better visibility into storage namespaces (publishers, teachers). This enables administrators to manage teacher-uploaded content through the same interface used for books.

**Priority**: MEDIUM - Completes the teachers storage feature delivered in Epic 6.

---

## **Existing System Context**

- **Current functionality**: Admin panel manages books, applications, and trash
- **Technology stack**: React 18, TypeScript, MUI components, Zustand stores, Vite
- **Integration points**:
  - NavBar.tsx (sidebar navigation)
  - App.tsx (routing)
  - API calls via lib/books.ts, lib/api.ts patterns
  - Backend API `/teachers/{teacher_id}/*` endpoints (from Epic 6.4)

---

## **Story 7.1: Add Teachers Navigation and Page**

**As an** administrator, **I want** a Teachers section in the admin panel, **so that** I can view and manage teacher-uploaded materials.

**Acceptance Criteria:**

1. NavBar displays "Teachers" link with appropriate icon (School or Person icon) below "Applications".
2. Route `/teachers` is registered in App.tsx and protected by authentication.
3. Teachers page displays a list/table of teacher materials with columns:
   - Teacher ID
   - Filename
   - File type (MIME)
   - Size
   - Upload date
4. Teachers page includes search/filter functionality by teacher ID.
5. Teachers page has "Upload Material" button that opens upload dialog.
6. Delete action soft-deletes material to trash (uses existing `/teachers/{teacher_id}/materials/{path}` DELETE endpoint).

**Technical Notes:**
- Follow existing Books.tsx patterns for table, filtering, and dialogs
- Create `apps/admin-panel/src/pages/Teachers.tsx`
- Create `apps/admin-panel/src/lib/teachers.ts` for API calls
- Add route in App.tsx: `<Route path="/teachers" element={<Teachers />} />`
- Add NavLink in NavBar.tsx with SchoolIcon from @mui/icons-material

---

## **Story 7.2: Create Teacher Material Upload Dialog**

**As an** administrator, **I want** to upload materials for a specific teacher, **so that** I can add teaching resources on their behalf.

**Acceptance Criteria:**

1. TeacherUploadDialog component accepts teacher_id as required input.
2. Dialog displays teacher ID being uploaded to.
3. File picker accepts allowed MIME types (PDF, images, audio, video, documents).
4. Upload progress indicator shows during upload.
5. Success/error feedback displayed after upload attempt.
6. Dialog validates file size before upload (100MB limit shown to user).
7. After successful upload, Teachers page refreshes to show new material.

**Technical Notes:**
- Create `apps/admin-panel/src/components/TeacherUploadDialog.tsx`
- Follow BookUploadDialog.tsx patterns
- API endpoint: `POST /teachers/{teacher_id}/upload`
- Add upload function to `lib/teachers.ts`

---

## **Story 7.3: Add Teacher ID Selector to Upload Flow**

**As an** administrator, **I want** to select or enter a teacher ID when uploading materials, **so that** I can organize materials by teacher.

**Acceptance Criteria:**

1. Teachers page shows list of existing teacher IDs (derived from materials listing).
2. Upload dialog includes teacher ID input field (text input with autocomplete from existing IDs).
3. New teacher IDs can be entered (creates new namespace automatically on upload).
4. Validation prevents empty teacher ID.
5. Teacher ID field shows helper text explaining the format requirements.

**Technical Notes:**
- Teacher IDs are prefixes in storage, not database records
- Derive existing teacher IDs from `/teachers/{teacher_id}/materials` by listing all prefixes
- May need new API endpoint `GET /teachers` to list all teacher prefixes, or derive client-side

---

## **Story 7.4: Update Trash Page for Teacher Materials**

**As an** administrator, **I want** the Trash page to display deleted teacher materials, **so that** I can restore or permanently delete them.

**Acceptance Criteria:**

1. Trash page shows teacher materials alongside books and apps.
2. Teacher material entries display item_type as "teacher_material".
3. Teacher materials show teacher_id in metadata column.
4. Restore action works for teacher materials (moves back to teachers bucket).
5. Permanent delete action works for teacher materials.
6. Filter/tab allows viewing only teacher materials in trash.

**Technical Notes:**
- Backend already returns `item_type: "teacher_material"` from Epic 6.4
- Update Trash.tsx to handle new item type
- May need to update trash item rendering to show teacher-specific info

---

## **Compatibility Requirements**

- [x] Existing book management functionality unchanged
- [x] Existing trash functionality continues to work
- [x] No database schema changes required
- [x] API endpoints from Epic 6.4 used as-is
- [x] UI follows existing MUI component patterns

## **Risk Mitigation**

- **Primary Risk:** Breaking existing Books or Trash functionality
- **Mitigation:** Incremental changes, reuse existing patterns, thorough testing
- **Rollback Plan:** Revert frontend changes only; backend unaffected

## **Definition of Done**

- [ ] All stories completed with acceptance criteria met
- [ ] Teachers page functional with CRUD operations
- [ ] Trash page displays and manages teacher materials
- [ ] Existing book/app functionality verified working
- [ ] No console errors in browser
- [ ] Responsive design maintained

---

## **Story Manager Handoff**

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is an enhancement to an existing React + TypeScript admin panel
- Integration points: NavBar.tsx, App.tsx, lib/*.ts API modules, Trash.tsx
- Existing patterns to follow: Books.tsx page structure, BookUploadDialog.tsx, MUI components
- Critical compatibility requirements: Existing functionality must remain intact
- Each story must include verification that existing book/trash functionality remains intact

The epic should maintain system integrity while delivering teacher materials management in the admin panel."

---

## **File Structure Preview**

```
apps/admin-panel/src/
├── pages/
│   └── Teachers.tsx          # NEW - Teacher materials page
├── components/
│   └── TeacherUploadDialog.tsx  # NEW - Upload dialog
├── lib/
│   └── teachers.ts           # NEW - API calls for teachers
└── components/
    └── NavBar.tsx            # MODIFY - Add Teachers link
```
