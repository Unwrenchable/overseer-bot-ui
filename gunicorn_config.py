"""
Gunicorn configuration for Overseer Bot.

This configuration ensures that the bot's scheduler and background tasks
start properly when run with gunicorn.
"""
import logging
import os

# Bind to the PORT environment variable, or default to 5000
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# Use only 1 worker because the app has schedulers and background tasks
# Multiple workers would duplicate these tasks
workers = 1

# Worker class - use sync for compatibility with threading
worker_class = "sync"

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"

# Timeout for worker silence (seconds)
timeout = 120


def on_starting(server):
    """Called just before the master process is initialized."""
    logging.info("Gunicorn server is starting")


def when_ready(server):
    """Called just after the server is started."""
    logging.info("Gunicorn server is ready. Receiving requests.")


def post_worker_init(worker):
    """
    Called just after a worker has been initialized.
    This is where we initialize the bot's scheduler and background tasks.
    """
    logging.info(f"Worker {worker.pid} initialized, starting bot services")
    
    # Import here to avoid issues with module loading order
    from overseer_bot import initialize_bot
    
    # Initialize the bot (scheduler, API polling, activation tweet)
    initialize_bot()
    
    logging.info(f"Worker {worker.pid} bot services started")
