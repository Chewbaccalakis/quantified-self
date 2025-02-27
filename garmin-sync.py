from garminconnect import Garmin
import psycopg2
import datetime
import os
from dotenv import load_dotenv
from psycopg2.extras import execute_values

# Load environment variables from .env file
load_dotenv()

# Garmin Credentials
USERNAME = os.getenv("GARMIN_USERNAME")
PASSWORD = os.getenv("GARMIN_PASSWORD")

# PostgreSQL Connection Configuration
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("GARMIN_DB_USER"),
    "password": os.getenv("GARMIN_DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

def get_last_imported_date():
    """Retrieve the most recent date in the activity table."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT MAX(date) FROM activity;")
        last_date = cur.fetchone()[0]
        cur.close()
        conn.close()
        return last_date
    except Exception as e:
        print(f"Database error when fetching last date: {e}")
        return None

def fetch_garmin_data(date):
    """Fetch daily quantified-self metrics for a given date."""
    try:
        client = Garmin(USERNAME, PASSWORD)
        client.login()
        daily_summary = client.get_user_summary(date)

        return {
            "date": date,
            "total_steps": daily_summary.get("totalSteps", 0),
            "total_distance_meters": daily_summary.get("totalDistanceMeters", 0),
            "active_seconds": daily_summary.get("activeSeconds", 0),
            "sedentary_seconds": daily_summary.get("sedentarySeconds", 0),
            "moderate_intensity_minutes": daily_summary.get("moderateIntensityMinutes", 0),
            "vigorous_intensity_minutes": daily_summary.get("vigorousIntensityMinutes", 0),
            "total_calories": daily_summary.get("totalKilocalories", 0),
            "active_calories": daily_summary.get("activeKilocalories", 0),
            "resting_calories": daily_summary.get("bmrKilocalories", 0),
            "min_heart_rate": daily_summary.get("minHeartRate"),
            "max_heart_rate": daily_summary.get("maxHeartRate"),
            "resting_heart_rate": daily_summary.get("restingHeartRate"),
            "stress_duration": daily_summary.get("stressDuration"),
            "total_stress_duration": daily_summary.get("totalStressDuration"),
            "measurable_awake_duration": daily_summary.get("measurableAwakeDuration"),
            "measurable_asleep_duration": daily_summary.get("measurableAsleepDuration"),
            "body_battery_highest": daily_summary.get("bodyBatteryHighestValue"),
            "body_battery_lowest": daily_summary.get("bodyBatteryLowestValue"),
            "body_battery_most_recent": daily_summary.get("bodyBatteryMostRecentValue"),
            "avg_respiration": daily_summary.get("avgWakingRespirationValue"),
            "highest_respiration": daily_summary.get("highestRespirationValue"),
            "lowest_respiration": daily_summary.get("lowestRespirationValue"),
            "avg_spo2": daily_summary.get("averageSpo2"),
            "lowest_spo2": daily_summary.get("lowestSpo2"),
        }
    except Exception as e:
        print(f"Error fetching data for {date}: {e}")
        return None

def save_to_postgres(data_list):
    """Insert multiple days of quantified-self metrics into the activity table."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        query = """
            INSERT INTO activity (
                date, total_steps, total_distance_meters, active_seconds, sedentary_seconds, 
                moderate_intensity_minutes, vigorous_intensity_minutes, total_calories, 
                active_calories, resting_calories, min_heart_rate, max_heart_rate, resting_heart_rate, 
                stress_duration, total_stress_duration, measurable_awake_duration, measurable_asleep_duration, 
                body_battery_highest, body_battery_lowest, body_battery_most_recent, avg_respiration, 
                highest_respiration, lowest_respiration, avg_spo2, lowest_spo2
            ) VALUES %s
            ON CONFLICT (date) DO UPDATE
            SET 
                total_steps = EXCLUDED.total_steps,
                total_distance_meters = EXCLUDED.total_distance_meters,
                active_seconds = EXCLUDED.active_seconds,
                sedentary_seconds = EXCLUDED.sedentary_seconds,
                moderate_intensity_minutes = EXCLUDED.moderate_intensity_minutes,
                vigorous_intensity_minutes = EXCLUDED.vigorous_intensity_minutes,
                total_calories = EXCLUDED.total_calories,
                active_calories = EXCLUDED.active_calories,
                resting_calories = EXCLUDED.resting_calories,
                min_heart_rate = EXCLUDED.min_heart_rate,
                max_heart_rate = EXCLUDED.max_heart_rate,
                resting_heart_rate = EXCLUDED.resting_heart_rate,
                stress_duration = EXCLUDED.stress_duration,
                total_stress_duration = EXCLUDED.total_stress_duration,
                measurable_awake_duration = EXCLUDED.measurable_awake_duration,
                measurable_asleep_duration = EXCLUDED.measurable_asleep_duration,
                body_battery_highest = EXCLUDED.body_battery_highest,
                body_battery_lowest = EXCLUDED.body_battery_lowest,
                body_battery_most_recent = EXCLUDED.body_battery_most_recent,
                avg_respiration = EXCLUDED.avg_respiration,
                highest_respiration = EXCLUDED.highest_respiration,
                lowest_respiration = EXCLUDED.lowest_respiration,
                avg_spo2 = EXCLUDED.avg_spo2,
                lowest_spo2 = EXCLUDED.lowest_spo2;
        """

        data_tuples = [
            (
                entry["date"], entry["total_steps"], entry["total_distance_meters"], entry["active_seconds"], 
                entry["sedentary_seconds"], entry["moderate_intensity_minutes"], entry["vigorous_intensity_minutes"], 
                entry["total_calories"], entry["active_calories"], entry["resting_calories"], entry["min_heart_rate"], 
                entry["max_heart_rate"], entry["resting_heart_rate"], entry["stress_duration"], 
                entry["total_stress_duration"], entry["measurable_awake_duration"], entry["measurable_asleep_duration"], 
                entry["body_battery_highest"], entry["body_battery_lowest"], entry["body_battery_most_recent"], 
                entry["avg_respiration"], entry["highest_respiration"], entry["lowest_respiration"], 
                entry["avg_spo2"], entry["lowest_spo2"]
            )
            for entry in data_list if entry
        ]

        from psycopg2.extras import execute_values
        execute_values(cur, query, data_tuples)
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"Inserted {len(data_tuples)} days of data into the activity table.")
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    last_imported_date = get_last_imported_date()
    today = datetime.date.today()

    if last_imported_date is None:
        print("No previous data found. Importing the last 60 days...")
        last_imported_date = today - datetime.timedelta(days=60)

    # Ensure we reimport the last known day
    start_date = last_imported_date.strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    print(f"Fetching data from {start_date} to {end_date}...")

    data_list = []
    for days_ago in range((today - last_imported_date).days + 1):
        date = (last_imported_date + datetime.timedelta(days=days_ago)).strftime("%Y-%m-%d")
        print(f"Fetching data for {date}...")
        data = fetch_garmin_data(date)
        if data:
            data_list.append(data)

    if data_list:
        save_to_postgres(data_list)