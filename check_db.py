import sqlite3

conn = sqlite3.connect('car_rental.db')
cursor = conn.cursor()

# Get schema
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", [row[0] for row in cursor.fetchall()])

# Get vehicles columns
cursor.execute("PRAGMA table_info(vehicles)")
print("\nVehicles columns:")
for row in cursor.fetchall():
    print(f"  {row[1]} ({row[2]})")

# Get sample vehicles
cursor.execute("SELECT * FROM vehicles LIMIT 3")
print("\nSample vehicles:")
for row in cursor.fetchall():
    print(f"  {row}")

conn.close()
