# Twilio Configuration
TWILIO_ACCOUNT_SID = 'your_account_sid'  # Replace with actual SID from environment variable
TWILIO_AUTH_TOKEN = 'your_auth_token'    # Replace with actual token from environment variable
TWILIO_WHATSAPP_NUMBER = 'your_whatsapp_number'  # Replace with your WhatsApp number

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/debug.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'connect': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Create logs directory if it doesn't exist
import os
if not os.path.exists('logs'):
    os.makedirs('logs') 