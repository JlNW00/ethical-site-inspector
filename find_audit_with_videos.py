import sqlite3
import json

conn = sqlite3.connect('data/ethicalsiteinspector.db')
cursor = conn.cursor()

# Get all audits with their video_urls
cursor.execute('SELECT id, status, video_urls FROM audits WHERE status = "completed"')
rows = cursor.fetchall()

print("Completed audits with video_urls:")
found = False
for row in rows:
    audit_id, status, video_urls = row
    print(f"  ID: {audit_id}")
    print(f"  Status: {status}")
    print(f"  video_urls: {video_urls}")
    if video_urls is not None:
        found = True
        print(f"  *** FOUND audit with non-null video_urls: {audit_id} ***")
    print()

conn.close()

if not found:
    print("No completed audits with non-null video_urls found.")
