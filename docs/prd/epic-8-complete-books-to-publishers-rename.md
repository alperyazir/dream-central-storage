# **Epic 8: Publisher-Centric Domain Model with Normalized Schema**

**Epic Goal**: Establish a properly normalized database schema with `publishers` as first-class entities, creating a scalable foundation for publisher-centric content management.

> **Note**: Dynamic asset management (upload dialogs, asset type selection, file filtering) has been moved to **Epic 9: Publisher-Centric UI & Enhanced Uploads**.

**Priority**: HIGH - Foundation for scalable multi-asset architecture.

---

## **Background**

Epic 6 renamed the MinIO bucket from `books` to `publishers` and restructured storage paths to support publisher-level asset isolation. The storage layer now uses:
```
publishers/{publisher}/books/{book_name}/
publishers/{publisher}/logos/  (reserved)
publishers/{publisher}/materials/  (reserved)
```

However, the database schema remained denormalized - a single `books` table where each row represents one book, with the publisher name stored as a string column. This creates several issues:

1. **Naming confusion**: Table named `books` (or `publishers` after initial 8.1) doesn't match what rows represent
2. **No publisher entity**: Cannot store publisher-level metadata (logos, contacts, settings)
3. **Redundant data**: Publisher name repeated in every book record
4. **Limited scalability**: Hard to add publisher-specific features

This revised epic properly normalizes the schema by:
1. Creating a `publishers` table for publisher entities
2. Keeping `books` table for book/asset records with FK to publishers
3. Aligning the domain model with the storage structure
4. Providing basic publisher management UI in the admin panel

**Important**: Story 8.1 from the previous version was partially implemented (table renamed from `books` to `publishers`). This must be **rolled back first** before proceeding with the normalized design.

---

## **Pre-Requisite: Rollback Story 8.1**

Before starting this epic, the previous Story 8.1 changes must be rolled back:

1. Run `docker exec infrastructure-api-1 alembic downgrade -1` to revert the table rename
2. Restore `apps/api/app/models/book.py` to use `__tablename__ = "books"`
3. Verify the `books` table exists in the database
4. Update Story 8.1 status to "Cancelled - Superseded by normalized schema design"

---

## **Story 8.1: Create Publishers Table & Establish Normalized Schema**

**As a** database administrator, **I want** a properly normalized schema with publishers as first-class entities, **so that** we can store publisher metadata and establish proper relationships between publishers and their assets.

**Acceptance Criteria:**

1. New `publishers` table created with the following structure:
   ```sql
   CREATE TABLE publishers (
     id SERIAL PRIMARY KEY,
     name VARCHAR(255) NOT NULL UNIQUE,  -- Publisher identifier (unique)
     display_name VARCHAR(255),           -- Human-readable name
     description TEXT,                    -- Publisher description
     logo_url VARCHAR(512),               -- Path to logo in storage
     contact_email VARCHAR(255),          -- Contact information
     status VARCHAR(20) DEFAULT 'active', -- active, inactive, suspended
     created_at TIMESTAMPTZ DEFAULT NOW(),
     updated_at TIMESTAMPTZ DEFAULT NOW()
   );
   ```

2. `books` table modified to use FK relationship:
   ```sql
   ALTER TABLE books ADD COLUMN publisher_id INTEGER;
   -- Migrate data: Create publisher records from unique publisher values
   -- Update books.publisher_id to reference new publishers.id
   ALTER TABLE books ADD CONSTRAINT fk_books_publisher
     FOREIGN KEY (publisher_id) REFERENCES publishers(id);
   -- Keep publisher column temporarily for backward compatibility
   -- Mark publisher column as deprecated (remove in future story)
   ```

3. Migration includes data migration logic:
   - Extract unique `publisher` values from `books` table
   - Create corresponding records in `publishers` table
   - Update `books.publisher_id` to reference the new publisher records

4. Migration includes both `upgrade()` and `downgrade()` functions.

5. Existing book data remains intact and queryable after migration.

6. Application starts successfully with new schema.

7. ORM models updated:
   - `Publisher` model created in `app/models/publisher.py`
   - `Book` model updated to include `publisher_id` FK and relationship
   - Both models coexist and work correctly

**Technical Notes:**
- Migration file: `apps/api/alembic/versions/YYYYMMDD_01_create_publishers_table_normalize_schema.py`
- Data migration must handle empty `publisher` values gracefully
- Consider creating a "default" publisher for orphan books
- Index on `books.publisher_id` for query performance
- Keep `books.publisher` column temporarily for backward compatibility during transition

---

## **Story 8.2: Update Backend Models, Schemas, and Repositories**

**As a** backend developer, **I want** the ORM models, Pydantic schemas, and repositories updated to work with the normalized schema, **so that** the codebase properly reflects the publisher-books relationship.

**Acceptance Criteria:**

1. `Publisher` model created in `app/models/publisher.py`:
   ```python
   class Publisher(Base):
       __tablename__ = "publishers"
       id: Mapped[int]
       name: Mapped[str]  # Unique identifier
       display_name: Mapped[str | None]
       description: Mapped[str | None]
       logo_url: Mapped[str | None]
       contact_email: Mapped[str | None]
       status: Mapped[str]
       created_at: Mapped[datetime]
       updated_at: Mapped[datetime]
       # Relationship
       books: Mapped[list["Book"]] = relationship(back_populates="publisher_rel")
   ```

2. `Book` model updated in `app/models/book.py`:
   ```python
   class Book(Base):
       # Existing fields...
       publisher_id: Mapped[int] = mapped_column(ForeignKey("publishers.id"))
       # Relationship
       publisher_rel: Mapped["Publisher"] = relationship(back_populates="books")
       # Keep publisher string column for backward compatibility (deprecated)
       publisher: Mapped[str]  # DEPRECATED - use publisher_rel.name
   ```

3. Pydantic schemas created for Publisher in `app/schemas/publisher.py`:
   - `PublisherBase`, `PublisherCreate`, `PublisherUpdate`, `PublisherRead`
   - `PublisherWithBooks` (includes nested book list)

4. Book schemas updated to optionally include publisher details:
   - `BookRead` can include `publisher_name` derived from relationship
   - `BookCreate` accepts either `publisher_id` or `publisher` string (backward compat)

5. `PublisherRepository` created in `app/repositories/publisher.py`:
   - Standard CRUD operations
   - `get_by_name()` method for lookup by identifier
   - `get_with_books()` method for eager loading

6. `BookRepository` updated to support publisher relationship queries.

7. All existing tests pass, new tests added for Publisher model.

**Technical Notes:**
- Use SQLAlchemy 2.0 relationship patterns
- Ensure backward compatibility: existing code using `book.publisher` string still works
- Add deprecation warnings when accessing `book.publisher` directly
- Consider adding `publisher_name` property to Book model for convenience

---

## **Story 8.3: Create Publisher API Endpoints**

**As an** API consumer, **I want** dedicated endpoints for managing publishers, **so that** I can create, read, update, and delete publisher entities independently from books.

**Acceptance Criteria:**

1. New router `app/routers/publishers.py` with endpoints:
   - `POST /publishers/` - Create new publisher
   - `GET /publishers/` - List all publishers (with pagination)
   - `GET /publishers/{publisher_id}` - Get publisher by ID
   - `GET /publishers/by-name/{name}` - Get publisher by name
   - `PUT /publishers/{publisher_id}` - Update publisher
   - `DELETE /publishers/{publisher_id}` - Soft-delete publisher

2. Publisher endpoints return `PublisherRead` schema.

3. `GET /publishers/{publisher_id}/books` - List books for a publisher.

4. Books endpoints updated to work with publisher relationships:
   - `POST /books/` accepts `publisher_id` (preferred) or `publisher` string
   - `GET /books/` can filter by `publisher_id`
   - Response includes publisher information

5. Router registered in `app/main.py`.

6. OpenAPI documentation shows new `/publishers/` endpoints.

7. All API tests pass, new tests added for publisher endpoints.

**Technical Notes:**
- Maintain backward compatibility: `/books/` endpoints still work with `publisher` string
- Add query parameter `?include_publisher=true` for eager loading publisher data
- Consider adding `/publishers/{publisher_id}/stats` for publisher-level analytics

---

## **Story 8.4: Update Frontend Admin Panel for Publishers**

**As an** administrator, **I want** the admin panel to display and manage publishers as separate entities, **so that** I can view publisher details and their associated books.

**Acceptance Criteria:**

1. Navigation updated:
   - "Publishers" section in sidebar (bucket-based, as discussed)
   - Publishers list page showing all publishers
   - Publisher detail page showing publisher info + their books

2. Publisher management UI:
   - Create publisher form (name, display name, description, contact)
   - Edit publisher form
   - Delete publisher (with confirmation if has books)

3. Books UI updated:
   - Book list shows publisher name (from relationship)
   - Book create/edit form uses publisher dropdown instead of text input
   - Filter books by publisher

4. API client updated:
   - `lib/publishers.ts` - Publisher API functions
   - `lib/books.ts` - Updated to work with publisher_id

5. TypeScript interfaces added:
   - `Publisher`, `PublisherCreate`, `PublisherUpdate`
   - `Book` interface includes `publisher_id` and optional `publisher` object

6. No console errors or TypeScript compilation errors.

7. Frontend tests updated.

**Technical Notes:**
- Publisher dropdown should use autocomplete for large publisher lists
- Consider showing publisher logo/avatar in lists
- Book upload dialog should require selecting a publisher first

---

## **Story 8.5: Update Utility Scripts and Documentation**

**As a** developer, **I want** all utility scripts and documentation updated to reflect the normalized schema, **so that** the entire codebase is internally consistent.

**Acceptance Criteria:**

1. Utility script `apps/api/update_book_metadata.py` updated to work with publisher relationship.

2. README files updated to document:
   - New `/publishers/` endpoints
   - Publisher-book relationship
   - Asset management endpoints

3. API documentation reflects new schema and endpoints.

4. Database schema documentation updated.

5. Code comments updated where they reference old schema structure.

6. Environment variable examples updated if needed.

7. Test fixtures and seed data scripts updated for normalized schema.

**Technical Notes:**
- Update any scripts that directly reference `book.publisher` string
- Add examples showing how to create publisher + book together

---

## **Compatibility Requirements**

- [ ] Database migration is reversible (downgrade function provided)
- [ ] No data loss during schema normalization
- [ ] Backward compatibility maintained during transition:
  - Books API still accepts `publisher` string (creates publisher if needed)
  - Existing `book.publisher` column retained temporarily
- [ ] Frontend remains functional throughout backend deployment
- [ ] Storage paths unchanged (still use publisher name, not ID)

## **Risk Mitigation**

- **Primary Risk:** Data migration complexity
- **Mitigation:**
  - Test migration thoroughly in development environment
  - Backup database before running migration
  - Migration creates publishers from existing unique values
  - Rollback plan: downgrade migration restores original schema
- **Secondary Risk:** Breaking existing API consumers
- **Mitigation:**
  - Maintain backward compatibility for `publisher` string in book creation
  - Add deprecation warnings, remove in future version
  - Document migration path for API consumers

## **Definition of Done**

- [ ] Pre-requisite rollback completed (previous 8.1 changes reverted)
- [ ] All 5 stories completed with acceptance criteria met
- [ ] Database properly normalized with publishers table
- [ ] FK relationships working correctly
- [ ] All existing functionality preserved (books CRUD, uploads, trash)
- [ ] New publisher management endpoints functional
- [ ] Basic publisher management UI in admin panel
- [ ] All tests pass (unit, integration)
- [ ] API documentation updated
- [ ] Code review completed and approved

> **Note**: Dynamic asset management and enhanced upload dialogs are covered in Epic 9.

---

## **Story Manager Handoff**

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is a database normalization refactoring of an existing FastAPI + React + PostgreSQL + MinIO application
- The key change is introducing `publishers` as a first-class entity with FK relationship to `books`
- Backward compatibility is critical: existing code using `book.publisher` string must continue to work during transition
- Storage paths continue to use publisher name (not ID) to maintain consistency with MinIO structure
- Integration points: Database (Alembic migrations with data migration), Backend (FastAPI models/routers), Frontend (React + TypeScript)
- Each story must verify existing functionality remains intact
- Story sequence: Schema normalization (8.1) → Models/repos (8.2) → API (8.3) → Frontend (8.4) → Cleanup (8.5)

The epic establishes a scalable foundation for publisher-centric content management while preserving all existing functionality.

**Note**: Dynamic asset management (Story 8.5 in original spec) has been moved to Epic 9 for better separation of concerns."

---

## **Architecture Decision Record**

### Why Normalize the Schema?

**Problem Statement:**
The original schema stored publisher information as a string column in every book record. This led to:
- Confusion about what the table represents
- Inability to store publisher-level metadata
- Redundant data storage
- Limited query capabilities

**Decision:**
Create a proper normalized schema with:
- `publishers` table: Publisher entities with their own attributes
- `books` table: Book records with FK to publishers

**Consequences:**
- ✅ Clear domain model (publishers own books)
- ✅ Can add publisher metadata (logo, contact, settings)
- ✅ Proper relationships enable complex queries
- ✅ Scalable for future features (publisher dashboard, analytics)
- ⚠️ Requires data migration
- ⚠️ API changes needed (mitigated with backward compatibility)

### Storage Path Decision

**Decision:** Continue using `publisher.name` (not `publisher.id`) in storage paths.

**Rationale:**
- Maintains consistency with existing MinIO structure from Epic 6
- Human-readable paths for debugging
- Avoids need to migrate existing storage data
- Publisher name is unique, so functionally equivalent to ID

**Trade-off:** If publisher is renamed, storage paths become orphaned. Mitigation: Prevent publisher rename or implement storage path migration.
