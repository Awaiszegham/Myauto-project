import logging
import json
import os
import random

logger = logging.getLogger(__name__)

class AdaptiveMitigationService:
    """Service for adaptive bot detection mitigation based on past performance."""

    def __init__(self, log_file_path: str = "./download_logs.json"): # Placeholder for now
        self.log_file_path = log_file_path
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]

    import logging
import json
import os
import random
from collections import defaultdict

logger = logging.getLogger(__name__)

class AdaptiveMitigationService:
    """Service for adaptive bot detection mitigation based on past performance."""

    def __init__(self, log_file_path: str = "./download_logs.json"):
        self.log_file_path = log_file_path
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]

    def _analyze_logs(self) -> dict:
        """
        Analyzes past download outcomes to determine effective mitigation strategies.
        """
        success_counts = defaultdict(lambda: {'success': 0, 'total': 0})
        
        if not os.path.exists(self.log_file_path):
            return {}

        try:
            with open(self.log_file_path, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line)
                        params = log_entry.get('mitigation_params', {})
                        proxy_used = params.get('proxy_used', False)
                        cookies_used = params.get('cookies_used', False)
                        
                        key = f"proxy_{proxy_used}_cookies_{cookies_used}"
                        success_counts[key]['total'] += 1
                        if log_entry.get('success'):
                            success_counts[key]['success'] += 1
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping malformed log line during analysis: {line.strip()}")
            
            # Calculate success rates
            success_rates = {}
            for key, counts in success_counts.items():
                if counts['total'] > 0:
                    success_rates[key] = counts['success'] / counts['total']
                else:
                    success_rates[key] = 0.0
            
            logger.info(f"Analyzed success rates: {success_rates}")
            return success_rates
        except Exception as e:
            logger.error(f"Error analyzing logs: {e}")
            return {}

    def get_adaptive_params(self) -> dict:
        """
        Provides adaptive mitigation parameters based on learned patterns.
        """
        success_rates = self._analyze_logs()
        
        best_proxy_usage = False
        best_cookies_usage = False
        best_rate = -1

        # Determine best combination of proxy and cookies
        for proxy_val in [True, False]:
            for cookies_val in [True, False]:
                key = f"proxy_{proxy_val}_cookies_{cookies_val}"
                rate = success_rates.get(key, 0.0)
                if rate > best_rate:
                    best_rate = rate
                    best_proxy_usage = proxy_val
                    best_cookies_usage = cookies_val
        
        adaptive_params = {
            'user_agent': random.choice(self.user_agents),
            'sleep_interval': random.uniform(1, 3),
            'proxy_enabled': best_proxy_usage,
            'cookies_enabled': best_cookies_usage
        }
        logger.info(f"Providing adaptive mitigation parameters: {adaptive_params}")
        return adaptive_params

    def record_outcome(self, outcome_data: dict):
        """
        Records the outcome of a download attempt for future analysis.
        """
        try:
            # Ensure the directory exists
            log_dir = os.path.dirname(self.log_file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # Read existing logs, append new data, and write back
            logs = []
            if os.path.exists(self.log_file_path):
                with open(self.log_file_path, 'r') as f:
                    for line in f:
                        try:
                            logs.append(json.loads(line))
                        except json.JSONDecodeError:
                            logger.warning(f"Skipping malformed log line: {line.strip()}")
            
            logs.append(outcome_data)
            
            with open(self.log_file_path, 'w') as f:
                for log_entry in logs:
                    f.write(json.dumps(log_entry) + '\n')
            logger.info(f"Recorded outcome to {self.log_file_path}")
        except Exception as e:
            logger.error(f"Error recording outcome: {e}")

