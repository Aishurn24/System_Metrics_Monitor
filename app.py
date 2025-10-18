from flask import Flask, jsonify, request, render_template, session
import os
import threading
import time
from datetime import datetime, timedelta

# Import custom modules
from src.log_analyzer import LogAnalyzer
from src.auth import AuthManager
from src.metrics import MetricsCollector
from src.alerts import AlertManager
from src.database import DatabaseManager

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(minutes=30)

db_manager = DatabaseManager()
auth_manager = AuthManager()
metrics_collector = MetricsCollector()
alert_manager = AlertManager()

recent_metrics = []
recent_metrics_lock = threading.Lock()
MAX_METRICS_STORAGE = 100
stop_event = threading.Event()

def collect_metrics_continuously():
    """Background thread to collect system metrics periodically and generate alerts"""
    while not stop_event.is_set():
        try:
            cpu_usage = metrics_collector.get_cpu_usage()
            memory_usage = metrics_collector.get_memory_usage()
            timestamp = datetime.now()

            metric_data = {
                'timestamp': timestamp,
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage
            }

            with recent_metrics_lock:
                recent_metrics.append(metric_data)
                if len(recent_metrics) > MAX_METRICS_STORAGE:
                    recent_metrics.pop(0)

            alerts = alert_manager.check_thresholds(cpu_usage, memory_usage, timestamp)
            for alert in alerts:
                db_manager.store_alert(alert)
                print(f"ALERT: {alert}")

            time.sleep(5)
        except Exception as e:
            print(f"Error in metrics collection: {e}")
            time.sleep(10)

@app.errorhandler(Exception)
def handle_exception(e):
    """Global JSON error handler"""
    return jsonify({'error': str(e)}), 500

@app.route('/analyze-logs', methods=['POST'])
def analyze_logs():
    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'error': 'No file provided'}), 400

    try:
        log_content = file.read().decode('utf-8')
        analyzer = LogAnalyzer()
        results = analyzer.analyze(log_content)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    try:
        user_id = auth_manager.register_user(username, password)
        return jsonify({'message': 'User registered successfully', 'user_id': user_id})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    try:
        session_token = auth_manager.login_user(username, password)
        session.clear()
        session['user_id'] = auth_manager.get_user_id(username)
        session['session_token'] = session_token
        session.permanent = True

        return jsonify({'message': 'Login successful', 'session_token': session_token})
    except ValueError as e:
        return jsonify({'error': str(e)}), 401

@app.route('/validate-session', methods=['POST'])
def validate_session():
    data = request.get_json() or {}
    session_token = data.get('session_token')
    if not session_token:
        return jsonify({'error': 'Session token required'}), 400

    is_valid = auth_manager.validate_session(session_token)
    return jsonify({'valid': is_valid})

@app.route('/summary', methods=['GET'])
def get_summary():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authentication required'}), 401

    session_token = auth_header.replace('Bearer ', '')
    if not auth_manager.validate_session(session_token):
        return jsonify({'error': 'Invalid session token'}), 401

    try:
        total_alerts = db_manager.get_total_alerts()
        breakdown = db_manager.get_alert_breakdown()
        recent_alerts = db_manager.get_recent_alerts(10)

        avg_cpu = avg_memory = 0
        with recent_metrics_lock:
            if recent_metrics:
                last_ten = recent_metrics[-10:]
                avg_cpu = sum(m['cpu_usage'] for m in last_ten) / len(last_ten)
                avg_memory = sum(m['memory_usage'] for m in last_ten) / len(last_ten)

        summary = {
            'total_alerts': total_alerts,
            'alert_breakdown': breakdown,
            'recent_alerts': recent_alerts,
            'average_metrics': {
                'cpu_usage': round(avg_cpu, 2),
                'memory_usage': round(avg_memory, 2)
            },
            'current_thresholds': alert_manager.get_thresholds(),
            'timestamp': datetime.now().isoformat()
        }
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/metrics')
def get_metrics():
    with recent_metrics_lock:
        metrics = list(recent_metrics[-50:])
    return jsonify({
        'recent_metrics': metrics,
        'current_alerts': db_manager.get_recent_alerts(20)
    })

@app.route('/api/thresholds', methods=['POST'])
def update_thresholds():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authentication required'}), 401

    session_token = auth_header.replace('Bearer ', '')
    if not auth_manager.validate_session(session_token):
        return jsonify({'error': 'Invalid session token'}), 401

    data = request.get_json() or {}
    try:
        cpu_threshold = data.get('cpu_threshold')
        memory_threshold = data.get('memory_threshold')

        if cpu_threshold is not None:
            alert_manager.set_cpu_threshold(cpu_threshold)
        if memory_threshold is not None:
            alert_manager.set_memory_threshold(memory_threshold)

        return jsonify({
            'message': 'Thresholds updated successfully',
            'current_thresholds': alert_manager.get_thresholds()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.teardown_appcontext
def close_resources(exception):
    db_manager.close_connection()

if __name__ == '__main__':
    db_manager.init_db()
    try:
        auth_manager.register_user('admin', 'password123')
    except ValueError:
        pass

    metrics_thread = threading.Thread(target=collect_metrics_continuously, daemon=True)
    metrics_thread.start()

    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    finally:
        stop_event.set()
