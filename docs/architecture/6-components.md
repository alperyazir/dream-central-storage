# 6. Components

System composed of:  
- React Admin Panel (Frontend)  
- FastAPI Backend  
- PostgreSQL DB  
- MinIO Storage  

```mermaid
graph TD
  A[React Admin Panel] -->|REST API (HTTPS)| B[FastAPI Backend]
  B -->|SQL Queries| C[(PostgreSQL)]
  B -->|S3 API| D[(MinIO Storage)]

  style A fill:#D6E8FF
  style B fill:#D5F5E3
  style C fill:#FFF4C1
  style D fill:#FFE4C4
```

---
