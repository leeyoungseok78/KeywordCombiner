import pandas as pd
import psycopg2
from io import StringIO
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_predefined_data():
    """
    Load predefined regional data from PostgreSQL database
    """
    try:
        conn = psycopg2.connect(
            host=os.environ['PGHOST'],
            database=os.environ['PGDATABASE'],
            user=os.environ['PGUSER'],
            password=os.environ['PGPASSWORD'],
            port=os.environ['PGPORT']
        )
        
        query = "SELECT * FROM korean_regions"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        logger.info(f"Successfully loaded {len(df)} rows from the database.")
        return df
    except Exception as e:
        logger.error(f"Error loading data from database: {str(e)}")
        return pd.DataFrame(columns=['id', 'name', 'level_1', 'level_2', 'level_3'])

def save_to_csv(df):
    """
    Convert DataFrame to CSV
    """
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
    csv_str = csv_buffer.getvalue()
    return csv_str

def update_database_from_excel(df):
    """
    Update the PostgreSQL database with data from the uploaded Excel file
    """
    try:
        conn = psycopg2.connect(
            host=os.environ['PGHOST'],
            database=os.environ['PGDATABASE'],
            user=os.environ['PGUSER'],
            password=os.environ['PGPASSWORD'],
            port=os.environ['PGPORT']
        )
        cursor = conn.cursor()
        
        cursor.execute("TRUNCATE TABLE korean_regions")
        
        for _, row in df.iloc[1:].iterrows():
            cursor.execute(
                "INSERT INTO korean_regions (name, level_1, level_2, level_3) VALUES (%s, %s, %s, %s)",
                (row['Region'], row['Keyword_B'], row['Keyword_C'], '')
            )
        
        conn.commit()
        conn.close()
        logger.info("Successfully updated database with Excel data.")
        return True
    except Exception as e:
        logger.error(f"Error updating database with Excel data: {str(e)}")
        return False

def create_korean_regions_table():
    """
    Create the korean_regions table in the PostgreSQL database
    """
    try:
        conn = psycopg2.connect(
            host=os.environ['PGHOST'],
            database=os.environ['PGDATABASE'],
            user=os.environ['PGUSER'],
            password=os.environ['PGPASSWORD'],
            port=os.environ['PGPORT']
        )
        cursor = conn.cursor()
        
        create_table_query = """
        CREATE TABLE IF NOT EXISTS korean_regions (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            level_1 VARCHAR(50) NOT NULL,
            level_2 VARCHAR(50),
            level_3 VARCHAR(50)
        );
        """
        
        cursor.execute(create_table_query)
        conn.commit()
        conn.close()
        logger.info("Successfully created korean_regions table.")
        return True
    except Exception as e:
        logger.error(f"Error creating korean_regions table: {str(e)}")
        return False
