
AUTO_REFRESH_ALLOW = 'auto-refresh-allow'
CONSOLE_API_ALLOW = 'console-api-allow'
SENDER_API_ALLOW = 'sender-api-allow'

ALL = [AUTO_REFRESH_ALLOW, CONSOLE_API_ALLOW, SENDER_API_ALLOW]

SWITCH_STATUS = {
    AUTO_REFRESH_ALLOW: True,
    CONSOLE_API_ALLOW: True,
    SENDER_API_ALLOW:  True,
}

SWITCH_DESCRIPTIONS = {
    AUTO_REFRESH_ALLOW: 'Allow consoles to auto-refresh alerts',
    CONSOLE_API_ALLOW: 'Allow consoles to use the alert API',
    SENDER_API_ALLOW:  'Allow alerts to be submitted via the API',
}