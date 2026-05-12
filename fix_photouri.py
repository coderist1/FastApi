import sqlite3

conn = sqlite3.connect('car_rental.db')
cursor = conn.cursor()

# Update vehicle 1 to store relative path instead of full URL
cursor.execute(
    "UPDATE vehicles SET photo_uri = ? WHERE id = ?",
    ("/uploads/175a5037-1bb2-416b-9544-1461ac7599a7.jpeg", 1)
)

# Update vehicle 2 to store relative path instead of base64
cursor.execute(
    "UPDATE vehicles SET photo_uri = ? WHERE id = ?",
    ("/uploads/64d8ceea-00f6-42a2-ad1d-9830d4bb48b7.jpeg", 2)
)

conn.commit()
print("✓ Updated 2 vehicle records to use relative paths")

# Verify
cursor.execute("SELECT id, photo_uri FROM vehicles")
for row in cursor.fetchall():
    print(f"  Vehicle {row[0]}: {row[1][:60]}...")

conn.close()
