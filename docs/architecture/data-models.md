# Data Models

## 1. ApplicationBuild
**Purpose**: To track and manage each versioned build of the FlowBook desktop application.

**Key Attributes**:
- `id`: (UUID) Unique identifier for the database record.
- `version`: (Text) The semantic version of the application build (e.g., "2.1.0").
- `s3_key`: (Text) The path to the application's ZIP file in the MinIO store.
- `created_at`: (Timestamp) When the record was created.

## 2. BookDataset
**Purpose**: To track each versioned book dataset and its associated production metadata.

**Key Attributes**:
- `id`: (UUID) Unique identifier for the database record.
- `book_identifier`: (Text) A human-readable ID to group different versions of the same book (e.g., "algebra-101").
- `version`: (Text) The semantic version of the book dataset (e.g., "1.4.2").
- `s3_key`: (Text) The path to the book's data file in the MinIO store.
- `metadata`: (JSONB) A flexible field to store lifecycle data, such as creation date, edit history, and completion status.
- `created_at`: (Timestamp) When the record was created.

**Relationships**:  
For the MVP, these two models are independent. A relationship between an ApplicationBuild and a BookDataset is only formed temporarily when a user makes an API request to package them together.

---
