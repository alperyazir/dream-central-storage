# Epic 2: Advanced Packaging & Intelligence
**Epic Goal:** The goal of this epic is to build upon our core asset storage by adding the key business logic that solves your primary pain points. By the end of this epic, client applications will be able to request dynamically packaged application/book combinations and retrieve intelligent summaries about book contents, completing the MVP feature set.

## Story 2.1: Implement Book Content Inspection
*As an administrator, I want to request a summary of a book dataset's contents via the API, so that I can quickly see its composition without downloading it.*
* **Acceptance Criteria:**
    1.  A secure `GET /api/v1/books/{book-id}/{version}/summary` endpoint is created.
    2.  The endpoint retrieves the `config.json` for the specified book version from the S3 store.
    3.  The API parses the `config.json` and returns a JSON response containing the total page count and a count of activities grouped by type.
    4.  If the `config.json` is missing or malformed, a relevant error is returned.

## Story 2.2: Implement Asset Packaging Logic
*As a developer, I want to create a service that can take a specific application build and book dataset from storage and package them into a single distributable ZIP file, so that they can be delivered together to end-users.*
* **Acceptance Criteria:**
    1.  A packaging function is created that accepts an application version and a book version as input.
    2.  The function fetches the corresponding files from the S3 store.
    3.  It creates a structured ZIP file containing both the application and the book data.
    4.  The final ZIP file is stored in a temporary or dedicated location in S3.
    5.  The function returns the location of the newly created package.

## Story 2.3: Create Packaging API Endpoint
*As a client application, I want to request that an application build and a book dataset be packaged together via a secure API endpoint, so that I can initiate the creation of a distributable file for a user.*
* **Acceptance Criteria:**
    1.  A secure `POST /api/v1/packages` endpoint is created that requires authentication.
    2.  The endpoint accepts an `app_version` and a `book_version` in its request body.
    3.  The endpoint triggers the asset packaging logic (from Story 2.2).
    4.  Upon successful packaging, the endpoint returns a `201 Created` response containing a URL from which the package can be downloaded.

---