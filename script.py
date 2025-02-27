from garminconnect import Garmin
import psycopg2
import datetime

# Garmin Credentials
USERNAME = ""
PASSWORD = ""

# PostgreSQL Connection
DB_CONFIG = {
    "dbname": "quantified-self",
    "user": "garmin",
    "password": "",
    "host": "192.168.5.97",
    "port": "5432"
}

def create_table():
    """Ensure the activity table exists."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS activity (
                id SERIAL PRIMARY KEY,
                date DATE UNIQUE NOT NULL,
                steps INTEGER NOT NULL
            );
        """)

        conn.commit()
        cur.close()
        conn.close()
        print("Checked/Created activity table.")
    except Exception as e:
        print(f"Database error: {e}")

def fetch_garmin_steps():
    """Login to Garmin and fetch today's step count."""
    try:
        client = Garmin(USERNAME, PASSWORD)
        client.login()
        today = datetime.date.today().strftime("%Y-%m-%d")
        step_data = client.get_stats(today)
        return today, step_data["stepsTaken"]
    except Exception as e:
        print(f"Error fetching Garmin data: {e}")
        return None, None

def save_to_postgres(date, steps):
    """Insert step data into the activity table."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO activity (date, steps)
            VALUES (%s, %s)
            ON CONFLICT (date) DO UPDATE
            SET steps = EXCLUDED.steps;
        """, (date, steps))

        conn.commit()
        cur.close()
        conn.close()
        print(f"Inserted {steps} steps for {date} into activity table")
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    create_table()  # Ensure the table exists before inserting data
    date, steps = fetch_garmin_steps()
    if date and steps is not None:
        save_to_postgres(date, steps)
