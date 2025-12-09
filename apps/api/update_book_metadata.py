"""Script to update existing books with new metadata fields."""
import io
import zipfile
from app.core.config import get_settings
from app.services.minio import get_minio_client
from app.db import SessionLocal
from app.models.book import Book


def _collect_activity_details(config_data: dict) -> dict:
    """Collect frequency of each activity type in the config.json structure."""
    activity_freq = {}

    def collect_recursive(obj):
        if isinstance(obj, dict):
            if "activity" in obj:
                activity_obj = obj["activity"]
                if isinstance(activity_obj, dict) and "type" in activity_obj:
                    activity_type = activity_obj["type"]
                    if isinstance(activity_type, str):
                        activity_freq[activity_type] = activity_freq.get(activity_type, 0) + 1
            for value in obj.values():
                collect_recursive(value)
        elif isinstance(obj, list):
            for item in obj:
                collect_recursive(item)

    collect_recursive(config_data)
    return activity_freq


def calculate_book_metadata(client, bucket: str, prefix: str) -> tuple[int, dict]:
    """Calculate total size and activity details for a book."""
    import json
    
    total_size = 0
    activity_details = {}
    
    # List all objects under the book prefix
    objects = client.list_objects(bucket, prefix=prefix, recursive=True)
    
    for obj in objects:
        total_size += obj.size
        
        # Check if this is config.json
        if obj.object_name.endswith('/config.json'):
            try:
                response = client.get_object(bucket, obj.object_name)
                config_data = json.loads(response.read())
                response.close()
                response.release_conn()
                activity_details = _collect_activity_details(config_data)
            except Exception as e:
                print(f"Error reading config.json for {prefix}: {e}")
    
    return total_size, activity_details


def main():
    settings = get_settings()
    client = get_minio_client(settings)
    db = SessionLocal()
    
    try:
        books = db.query(Book).filter(Book.status == 'PUBLISHED').all()
        print(f"Found {len(books)} published books to update")
        
        for book in books:
            print(f"\nProcessing: {book.publisher}/{book.book_name}")
            prefix = f"{book.publisher}/{book.book_name}/"
            
            try:
                total_size, activity_details = calculate_book_metadata(
                    client, 
                    settings.minio_books_bucket, 
                    prefix
                )
                
                book.total_size = total_size
                book.activity_details = activity_details if activity_details else None
                db.commit()
                
                print(f"  ✓ Size: {total_size} bytes")
                print(f"  ✓ Activity types: {len(activity_details)}")
                
            except Exception as e:
                print(f"  ✗ Error: {e}")
                db.rollback()
        
        print("\n✓ Metadata update complete!")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
