import logging
import logging.config
import os

def setup_logging(log_file='logs/app.log', log_level=logging.DEBUG):
    log_dir = os.path.dirname(f"logs/{log_file}.log")
    os.makedirs(log_dir, exist_ok=True)
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
        },
        'handlers': {
            'console': {
                'level': log_level,
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
            },
            'file': {
                'level': log_level,
                'class': 'logging.FileHandler',
                'filename': log_file,
                'formatter': 'standard',
            },
        },
        'root': {
            'handlers': ['console', 'file'],
            'level': log_level,
        },
    }

    logging.config.dictConfig(logging_config)

setup_logging()
