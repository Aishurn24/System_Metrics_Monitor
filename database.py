import sqlite3
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path='codexray.db'):
        # Save database file path and connect to SQLite DB
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()

    # Close the database connection when done
    def close_connection(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    # Create the alerts table if it doesn't exist
    def init_db(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                value REAL NOT NULL,
                threshold REAL NOT NULL,
                severity TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                acknowledged BOOLEAN DEFAULT FALSE
            )
        ''')
        self.conn.commit()

    # Add a new alert record to the DB
    def store_alert(self, alert):
        self.cursor.execute('''
            INSERT INTO alerts (type, message, value, threshold, severity, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (alert['type'], alert['message'], alert['value'], alert['threshold'], alert['severity'], alert['timestamp']))
        self.conn.commit()

    # Get total count of alerts stored
    def get_total_alerts(self):
        self.cursor.execute('SELECT COUNT(*) FROM alerts')
        count = self.cursor.fetchone()[0]
        return count

    # Get how many alerts of each type
    def get_alert_breakdown(self):
        self.cursor.execute('SELECT type, COUNT(*) FROM alerts GROUP BY type')
        rows = self.cursor.fetchall()
        result = {}
        for row in rows:
            key = row[0]
            value = row[1]
            result[key] = value
        return result

    # Get recent alert records, default limit 10
    def get_recent_alerts(self, limit=10):
        self.cursor.execute('''
            SELECT type, message, value, threshold, severity, timestamp
            FROM alerts
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        rows = self.cursor.fetchall()

        alerts = []
        for row in rows:
            alert = {
                'type': row[0],
                'message': row[1],
                'value': row[2],
                'threshold': row[3],
                'severity': row[4],
                'timestamp': row[5]
            }
            alerts.append(alert)
        return alerts
