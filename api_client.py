"""
API Client for fetching status and alerts from overseer-bot-ai
Polls external APIs and aggregates event data for dashboard display
"""
import os
import logging
import requests
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

# Configuration from environment variables
OVERSEER_BOT_AI_URL = os.getenv('OVERSEER_BOT_AI_URL', '')
OVERSEER_BOT_AI_API_KEY = os.getenv('OVERSEER_BOT_AI_API_KEY', '')
TOKEN_SCALPER_URL = os.getenv('TOKEN_SCALPER_URL', '')
TOKEN_SCALPER_API_KEY = os.getenv('TOKEN_SCALPER_API_KEY', '')

# Polling configuration
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '15'))  # seconds (default 15s)
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '5'))  # seconds

# Alert storage
ALERT_HISTORY = []
ALERT_HISTORY_LOCK = threading.Lock()
MAX_ALERTS = 100  # Keep last 100 alerts

# Health status tracking
HEALTH_STATUS = {
    'overseer_bot_ai': {
        'status': 'unknown',
        'last_check': None,
        'last_success': None,
        'error': None
    },
    'token_scalper': {
        'status': 'unknown',
        'last_check': None,
        'last_success': None,
        'error': None
    }
}
HEALTH_STATUS_LOCK = threading.Lock()


def add_alert(alert_type: str, source: str, data: dict, message: str = None):
    """
    Add an alert to the history (thread-safe)
    
    Args:
        alert_type: Type of alert (e.g., 'trade', 'rugpull', 'airdrop', 'status')
        source: Source system (e.g., 'overseer-bot-ai', 'token-scalper')
        data: Alert data dictionary (should contain only essential fields to avoid memory issues)
        message: Optional human-readable message
    
    Note: The data dictionary is stored as-is. Ensure external APIs return 
    reasonably-sized data objects. Consider extracting only essential fields 
    if the external API returns large responses.
    """
    global ALERT_HISTORY
    with ALERT_HISTORY_LOCK:
        alert = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'source': source,
            'data': data,
            'message': message or f"{alert_type.upper()} from {source}"
        }
        ALERT_HISTORY.append(alert)
        
        # Keep only the most recent alerts (bounded memory usage)
        if len(ALERT_HISTORY) > MAX_ALERTS:
            ALERT_HISTORY = ALERT_HISTORY[-MAX_ALERTS:]
        
        logging.info(f"Alert added: {alert_type} from {source}")


def get_alerts(limit: int = 50) -> List[dict]:
    """
    Get recent alerts (thread-safe)
    
    Args:
        limit: Maximum number of alerts to return
        
    Returns:
        List of alert dictionaries in reverse chronological order
    """
    with ALERT_HISTORY_LOCK:
        return list(reversed(ALERT_HISTORY[-limit:]))


def update_health_status(service: str, status: str, error: str = None):
    """
    Update health status for a service (thread-safe)
    
    Args:
        service: Service name ('overseer_bot_ai' or 'token_scalper')
        status: Status string ('healthy', 'unhealthy', 'unknown')
        error: Optional error message
    """
    with HEALTH_STATUS_LOCK:
        HEALTH_STATUS[service]['status'] = status
        HEALTH_STATUS[service]['last_check'] = datetime.now().isoformat()
        if status == 'healthy':
            HEALTH_STATUS[service]['last_success'] = datetime.now().isoformat()
            HEALTH_STATUS[service]['error'] = None
        else:
            HEALTH_STATUS[service]['error'] = error


def get_health_status() -> dict:
    """Get current health status for all services (thread-safe)"""
    with HEALTH_STATUS_LOCK:
        return {k: v.copy() for k, v in HEALTH_STATUS.items()}


def fetch_overseer_bot_ai_status() -> Optional[dict]:
    """
    Fetch status from overseer-bot-ai /api/status endpoint
    
    Returns:
        Status data dictionary or None if failed
    """
    if not OVERSEER_BOT_AI_URL:
        return None
    
    try:
        url = f"{OVERSEER_BOT_AI_URL.rstrip('/')}/api/status"
        headers = {}
        if OVERSEER_BOT_AI_API_KEY:
            headers['Authorization'] = f"Bearer {OVERSEER_BOT_AI_API_KEY}"
        
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        update_health_status('overseer_bot_ai', 'healthy')
        
        # Add status as an alert
        add_alert(
            'status',
            'overseer-bot-ai',
            data,
            f"Status update: {data.get('status', 'unknown')}"
        )
        
        return data
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch overseer-bot-ai status: {e}")
        update_health_status('overseer_bot_ai', 'unhealthy', str(e))
        return None


def fetch_overseer_bot_ai_alerts() -> Optional[List[dict]]:
    """
    Fetch alerts from overseer-bot-ai /api/alerts endpoint
    
    Returns:
        List of alert dictionaries or None if failed
    """
    if not OVERSEER_BOT_AI_URL:
        return None
    
    try:
        url = f"{OVERSEER_BOT_AI_URL.rstrip('/')}/api/alerts"
        headers = {}
        if OVERSEER_BOT_AI_API_KEY:
            headers['Authorization'] = f"Bearer {OVERSEER_BOT_AI_API_KEY}"
        
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        alerts = response.json()
        update_health_status('overseer_bot_ai', 'healthy')
        
        # Add each alert to our history
        if isinstance(alerts, list):
            for alert in alerts:
                alert_type = alert.get('type', 'unknown')
                add_alert(
                    alert_type,
                    'overseer-bot-ai',
                    alert,
                    alert.get('message', f"{alert_type} alert")
                )
        
        return alerts
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch overseer-bot-ai alerts: {e}")
        update_health_status('overseer_bot_ai', 'unhealthy', str(e))
        return None


def fetch_token_scalper_status() -> Optional[dict]:
    """
    Fetch status from Token-scalper /api/status endpoint
    
    Returns:
        Status data dictionary or None if failed
    """
    if not TOKEN_SCALPER_URL:
        return None
    
    try:
        url = f"{TOKEN_SCALPER_URL.rstrip('/')}/api/status"
        headers = {}
        if TOKEN_SCALPER_API_KEY:
            headers['Authorization'] = f"Bearer {TOKEN_SCALPER_API_KEY}"
        
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        update_health_status('token_scalper', 'healthy')
        
        # Add status as an alert
        add_alert(
            'status',
            'token-scalper',
            data,
            f"Status update: {data.get('status', 'unknown')}"
        )
        
        return data
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch token-scalper status: {e}")
        update_health_status('token_scalper', 'unhealthy', str(e))
        return None


def poll_external_apis():
    """
    Main polling loop - fetches data from external APIs periodically
    Runs in a background daemon thread
    
    Note: This is an infinite loop that runs as a daemon thread. The thread
    will be automatically terminated when the main application exits. No
    explicit shutdown handling is required since this is a daemon thread.
    
    For production use, consider implementing graceful shutdown if needed:
    - Use a threading.Event() to signal shutdown
    - Check the event in the loop: while not shutdown_event.is_set()
    - Set the event from main thread on shutdown
    """
    logging.info(f"Starting API polling (interval: {POLL_INTERVAL}s)")
    
    while True:
        try:
            # Fetch from overseer-bot-ai
            if OVERSEER_BOT_AI_URL:
                fetch_overseer_bot_ai_status()
                fetch_overseer_bot_ai_alerts()
            
            # Fetch from token-scalper
            if TOKEN_SCALPER_URL:
                fetch_token_scalper_status()
            
        except Exception as e:
            logging.error(f"Error in polling loop: {e}")
        
        # Sleep until next poll
        time.sleep(POLL_INTERVAL)


def start_polling():
    """Start the background polling thread"""
    if not OVERSEER_BOT_AI_URL and not TOKEN_SCALPER_URL:
        logging.warning("No external API URLs configured. Polling disabled.")
        return
    
    polling_thread = threading.Thread(target=poll_external_apis, daemon=True)
    polling_thread.start()
    logging.info("API polling thread started")


# Initialize health status on module load
if not OVERSEER_BOT_AI_URL:
    update_health_status('overseer_bot_ai', 'disabled', 'No URL configured')
if not TOKEN_SCALPER_URL:
    update_health_status('token_scalper', 'disabled', 'No URL configured')
