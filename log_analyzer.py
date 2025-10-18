import re
from collections import Counter
from datetime import datetime

class LogAnalyzer:
    def __init__(self):
        # Pattern to capture: word, date time, log level, message
        self.log_pattern = re.compile(r'(\w+)\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+-\s+(\w+):\s+(.+)')

    # Analyze the log text and return counts and common messages
    def analyze(self, log_content):
        lines = log_content.strip().split('\n')

        levels = []
        errors = []
        warnings = []
        infos = []

        for line in lines:
            match = self.log_pattern.match(line)
            if match:
                level = match.group(3).upper()
                message = match.group(4)

                levels.append(level)

                if level == 'ERROR':
                    errors.append(message)
                elif level == 'WARNING':
                    warnings.append(message)
                elif level == 'INFO':
                    infos.append(message)

        level_counts = Counter(levels)
        error_counts = Counter(errors)
        warning_counts = Counter(warnings)
        info_counts = Counter(infos)

        top_errors = error_counts.most_common(5)
        top_warnings = warning_counts.most_common(5)
        top_infos = info_counts.most_common(5)

        return {
            'log_level_counts': dict(level_counts),
            'total_logs': len(lines),
            'top_errors': top_errors,
            'top_warnings': top_warnings,
            'top_info': top_infos,
            'analysis_timestamp': self._get_timestamp()
        }

    # Get current timestamp in ISO format string
    def _get_timestamp(self):
        return datetime.now().isoformat()
