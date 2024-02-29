import mysql.connector
from db_config import DB_CONFIG

def connect():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None
    
def insert_data(conn, query, data):
    try:
        cursor = conn.cursor()
        cursor.execute(query, data)
        conn.commit()
        cursor.close()
        return True
    except mysql.connector.Error as error:
        print("Error inserting data:", error)
        conn.rollback()
        return False


    