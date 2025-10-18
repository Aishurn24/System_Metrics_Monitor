import psutil
from datetime import datetime

class MetricsCollector:
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        return psutil.cpu_percent(interval=1)
    
    def get_memory_usage(self) -> float:
        """Get current memory usage percentage"""
        memory = psutil.virtual_memory()
        return memory.percent
    
    def get_disk_usage(self) -> float:
        """Get current disk usage percentage"""
        disk = psutil.disk_usage('/')
        return (disk.used / disk.total) * 100
    
    def get_all_metrics(self) -> dict:
        """Get all system metrics"""
        return {
            'cpu_usage': self.get_cpu_usage(),
            'memory_usage': self.get_memory_usage(),
            'disk_usage': self.get_disk_usage(),
            'timestamp': datetime.now()
        }