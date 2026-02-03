import pymysql
import pandas as pd
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME


def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=3306,
        ssl={"ssl": {}},  # requis pour Azure MySQL
        cursorclass=pymysql.cursors.DictCursor
    )


def fetch_dataframe(query):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
        return pd.DataFrame(rows)
    finally:
        conn.close()



def execute_update(query, params):
    """
    Execute an UPDATE / INSERT query with parameters
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
        conn.commit()
    finally:
        conn.close()
