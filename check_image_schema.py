#!/usr/bin/env python3
"""
Check the schema of image tables.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.db.connection import get_connection

def check_schema():
    """Check schema of MedicalImageVectors table."""
    conn = get_connection()
    cursor = conn.cursor()

    print("Checking MedicalImageVectors table schema...\n")

    try:
        # Get column information
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'MedicalImageVectors'
            AND TABLE_SCHEMA = 'SQLUser'
            ORDER BY ORDINAL_POSITION
        """)

        columns = cursor.fetchall()
        if columns:
            print(f"Found {len(columns)} columns:\n")
            for col_name, data_type, max_len in columns:
                if max_len:
                    print(f"  - {col_name}: {data_type}({max_len})")
                else:
                    print(f"  - {col_name}: {data_type}")
        else:
            print("No column information found")

        # Check if table can be queried
        print("\nTrying to query table...")
        cursor.execute("SELECT TOP 1 * FROM SQLUser.MedicalImageVectors")
        row = cursor.fetchone()
        if row:
            print(f"Sample row: {row}")
        else:
            print("Table is empty (0 rows)")

    except Exception as e:
        print(f"Error: {e}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_schema()
