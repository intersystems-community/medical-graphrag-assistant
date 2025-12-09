#!/usr/bin/env python3
"""
Check if image-related tables exist in IRIS database.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.db.connection import get_connection

def check_tables():
    """Check for image-related tables in IRIS."""
    conn = get_connection()
    cursor = conn.cursor()

    print("Checking for image-related tables in IRIS...\n")

    # Check for MIMICCXRImages table
    try:
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'MIMICCXRImages'
        """)
        result = cursor.fetchone()
        if result and result[0] > 0:
            print("✓ VectorSearch.MIMICCXRImages table EXISTS")

            # Check row count
            cursor.execute("SELECT COUNT(*) FROM VectorSearch.MIMICCXRImages")
            count = cursor.fetchone()[0]
            print(f"  - Contains {count} images")

            # Check schema
            cursor.execute("""
                SELECT TOP 1 * FROM VectorSearch.MIMICCXRImages
            """)
            row = cursor.fetchone()
            if row:
                print(f"  - Sample row columns: {len(row)} columns")
                print(f"  - First row: {row[:5]}...")  # Show first 5 columns
        else:
            print("✗ VectorSearch.MIMICCXRImages table NOT FOUND")
            print("\nTo create this table, you need to:")
            print("1. Have MIMIC-CXR dataset (PhysioNet access required)")
            print("2. Run image vectorization pipeline")
            print("3. Load vectors into IRIS")
    except Exception as e:
        print(f"✗ Error checking MIMICCXRImages: {e}")

    # Check for other image tables
    print("\nSearching for all tables with 'Image' in name...")
    try:
        cursor.execute("""
            SELECT TABLE_SCHEMA, TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME LIKE '%Image%'
            ORDER BY TABLE_SCHEMA, TABLE_NAME
        """)
        tables = cursor.fetchall()
        if tables:
            for schema, table in tables:
                print(f"  - {schema}.{table}")

                # Get row count
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {schema}.{table}")
                    count = cursor.fetchone()[0]
                    print(f"    ({count} rows)")
                except:
                    pass
        else:
            print("  No tables found with 'Image' in name")
    except Exception as e:
        print(f"Error searching for image tables: {e}")

    cursor.close()
    conn.close()
    print("\nDone!")

if __name__ == "__main__":
    check_tables()
