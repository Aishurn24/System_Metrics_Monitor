from datetime import datetime

class AlertManager:
    def __init__(self):
        # Set initial alert thresholds for CPU and memory usage
        self.cpu_threshold = 25.0
        self.memory_threshold = 30.0
        self.active_alerts = {}  # Not used much for now

    # Check if current CPU or memory use is above thresholds and create alerts
    def check_thresholds(self, cpu_usage, memory_usage, timestamp):
        alerts = []
        if cpu_usage > self.cpu_threshold:
            alert = {
                'type': 'CPU',
                'message': 'High CPU usage: {:.2f}%'.format(cpu_usage),
                'value': cpu_usage,
                'threshold': self.cpu_threshold,
                'timestamp': timestamp,
                'severity': 'HIGH'
            }
            alerts.append(alert)

        if memory_usage > self.memory_threshold:
            alert = {
                'type': 'MEMORY',
                'message': 'High Memory usage: {:.2f}%'.format(memory_usage),
                'value': memory_usage,
                'threshold': self.memory_threshold,
                'timestamp': timestamp,
                'severity': 'HIGH'
            }
            alerts.append(alert)

        return alerts

    # Update CPU threshold within valid range 0-100
    def set_cpu_threshold(self, threshold):
        if threshold >= 0 and threshold <= 100:
            self.cpu_threshold = threshold
        else:
            raise ValueError("CPU threshold must be between 0 and 100")

    # Update Memory threshold within valid range 0-100
    def set_memory_threshold(self, threshold):
        if threshold >= 0 and threshold <= 100:
            self.memory_threshold = threshold
        else:
            raise ValueError("Memory threshold must be between 0 and 100")

    # Return the current thresholds as a simple dictionary
    def get_thresholds(self):
        return {
            'cpu_threshold': self.cpu_threshold,
            'memory_threshold': self.memory_threshold
        }
