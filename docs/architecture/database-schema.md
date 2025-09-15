# Database Schema
```sql
-- Enable UUID generation function if not already enabled
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Table for storing application builds
CREATE TABLE application_builds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version TEXT NOT NULL,
    s3_key TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure every version string is unique
    UNIQUE(version)
);

-- Table for storing book datasets and their metadata
CREATE TABLE book_datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_identifier TEXT NOT NULL,
    version TEXT NOT NULL,
    s3_key TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure that for any given book, the version is unique
    UNIQUE(book_identifier, version)
);

-- Add an index for faster lookups of all versions of a specific book
CREATE INDEX idx_book_datasets_identifier ON book_datasets(book_identifier);
```

---
