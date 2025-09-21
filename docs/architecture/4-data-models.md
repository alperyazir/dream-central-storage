# 4. Data Models

## Book  
- **Purpose:** Represents metadata for a single interactive book.  

```ts
// packages/shared/
export interface Book {
  id: number;
  publisher: string;
  book_name: string;
  language: string;
  category: string;
  version?: string;
  status: 'draft' | 'published' | 'archived';
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}
```

## User  
- **Purpose:** Represents an admin user with credentials.  

```ts
// packages/shared/
export interface User {
  id: number;
  email: string;
  hashed_password: string;
}

export interface SafeUser {
  id: number;
  email: string;
}
```

---
