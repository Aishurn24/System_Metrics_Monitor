from flask import Flask, jsonify, request, render_template, session
import os
import threading
import time
from datetime import datetime, timedelta

# All models are imported 
from src.log_analyzer import LogAnalyzer
from src.auth import AuthManager
from src.metrics import MetricsCollector
from src.alerts import AlertManager
from src.database import DatabaseManager

app = Flask(__name__)
app.secret_key = os.urandom(24)  # the session security
app.permanent_session_lifetime = timedelta(minutes=30)  # Session active till lasts 30 minutes

# Create objects for database, auth, metrics, alert handling
db_manager = DatabaseManager()
auth_manager = AuthManager()
metrics_collector = MetricsCollector()
alert_manager = AlertManager()

# to Keep recent metrics in the list
recent_metrics = []
recent_metrics_lock = threading.Lock()
# Selecting Max number of metrics to hold in memory
MAX_METRICS_STORAGE = 100
# Event to stop the metric collection loop properly 
stop_event = threading.Event()

# collect CPU and memory usage again and again
def collect_metrics_continuously():
    while not stop_event.is_set():
        try:
            cpu = metrics_collector.get_cpu_usage()
            memory = metrics_collector.get_memory_usage()
            now = datetime.now()

            metric = {
                'timestamp': now,
                'cpu_usage': cpu,
                'memory_usage': memory
            }

            #  new metric
            with recent_metrics_lock:
                recent_metrics.append(metric)
                if len(recent_metrics) > MAX_METRICS_STORAGE:
                    recent_metrics.pop(0)

            # Check if any alerts 
            alerts = alert_manager.check_thresholds(cpu, memory, now)
            for alert in alerts:
                db_manager.store_alert(alert)
                print("ALERT:", alert)

            time.sleep(5)  # Sleep 5 seconds before checking next time
        except Exception as e:
            print("Error during metric collection:", e)
            time.sleep(10)  # Sleep 10 sec  if error happens


@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({'error': str(e)}), 500

# Route to analyze uploaded log files
@app.route('/analyze-logs', methods=['POST'])
def analyze_logs():
    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'error': 'No log file provided'}), 400
    try:
        content = file.read().decode('utf-8')
        analyzer = LogAnalyzer()
        result = analyzer.analyze(content)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Registering a new user
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    try:
        user_id = auth_manager.register_user(username, password)
        return jsonify({'message': 'User registered', 'user_id': user_id})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

# User login route
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    try:
        token = auth_manager.login_user(username, password)
        session.clear()
        session['user_id'] = auth_manager.get_user_id(username)
        session['session_token'] = token
        session.permanent = True
        return jsonify({'message': 'Login successful', 'session_token': token})
    except ValueError as e:
        return jsonify({'error': str(e)}), 401

# Check if session token is valid
@app.route('/validate-session', methods=['POST'])
def validate_session():
    data = request.get_json() or {}
    token = data.get('session_token')
    if not token:
        return jsonify({'error': 'Session token needed'}), 400
    is_valid = auth_manager.validate_session(token)
    return jsonify({'valid': is_valid})

# Get summary data for dashboard (protected)
@app.route('/summary', methods=['GET'])
def get_summary():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Must be authenticated'}), 401
    token = auth_header.replace('Bearer ', '')
    if not auth_manager.validate_session(token):
        return jsonify({'error': 'Invalid token'}), 401
    try:
        total_alerts = db_manager.get_total_alerts()
        breakdown = db_manager.get_alert_breakdown()
        recent_alerts = db_manager.get_recent_alerts(10)
        avg_cpu = 0
        avg_memory = 0
        with recent_metrics_lock:
            if recent_metrics:
                last10 = recent_metrics[-10:]
                avg_cpu = sum(m['cpu_usage'] for m in last10) / len(last10)
                avg_memory = sum(m['memory_usage'] for m in last10) / len(last10)
        summary = {
            'total_alerts': total_alerts,
            'alert_breakdown': breakdown,
            'recent_alerts': recent_alerts,
            'average_metrics': {'cpu_usage': round(avg_cpu, 2), 'memory_usage': round(avg_memory, 2)},
            'current_thresholds': alert_manager.get_thresholds(),
            'timestamp': datetime.now().isoformat()
        }
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Serve dashboard page
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

# Provide recent system metrics and alerts
@app.route('/api/metrics')
def get_metrics():
    with recent_metrics_lock:
        metrics = list(recent_metrics[-50:])
    return jsonify({
        'recent_metrics': metrics,
        'current_alerts': db_manager.get_recent_alerts(20)
    })

# Update alert thresholds (requires login)
@app.route('/api/thresholds', methods=['POST'])
def update_thresholds():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    token = auth_header.replace('Bearer ', '')
    if not auth_manager.validate_session(token):
        return jsonify({'error': 'Invalid token'}), 401
    data = request.get_json() or {}
    try:
        cpu_threshold = data.get('cpu_threshold')
        memory_threshold = data.get('memory_threshold')
        if cpu_threshold is not None:
            alert_manager.set_cpu_threshold(cpu_threshold)
        if memory_threshold is not None:
            alert_manager.set_memory_threshold(memory_threshold)
        return jsonify({
            'message': 'Thresholds updated',
            'current_thresholds': alert_manager.get_thresholds()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Close resources on app shutdown
@app.teardown_appcontext
def close_resources(exception):
    db_manager.close_connection()

# Main app run
if __name__ == '__main__':
    db_manager.init_db()  # Create DB tables if not exist
    try:
        auth_manager.register_user('admin', 'password123')  # Create default admin if missing
    except ValueError:
        pass  # Ignore if user already exists

    # Start the metrics collection thread
    metrics_thread = threading.Thread(target=collect_metrics_continuously, daemon=True)
    metrics_thread.start()

    # Start the web server
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    finally:
        stop_event.set() 
