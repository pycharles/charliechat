# Analytics Module

This module provides a clean, extensible interface for analytics providers in the Charlie Chat API. It's designed to work seamlessly in both development and production (AWS Lambda) environments.

## Features

- **Lazy Initialization**: Analytics clients are only initialized when needed
- **Environment Detection**: Automatically detects AWS Lambda environment
- **Safe Event Capture**: All analytics functions are safe to call even when disabled
- **Extensible Design**: Easy to add new analytics providers
- **Consistent Naming**: Uses `analytics_{provider}_{service}` naming convention

## Current Providers

### PostHog (`posthog_client.py`)

PostHog integration with the following features:
- Automatic Lambda environment detection
- Safe event capture with `capture_event()`
- User identification with `identify_user()`
- User aliasing with `alias_user()`
- Event flushing with `flush_events()`

**Environment Variables:**
- `POSTHOG_API_KEY`: PostHog project API key (required in Lambda)
- `POSTHOG_HOST`: PostHog host URL (optional, defaults to app.posthog.com)

### Amplitude (`amplitude_client.py`)

Example implementation showing how to add additional analytics providers.

## Usage

### Basic Event Capture

```python
from app.analytics import capture_event

# Capture an event (safe to call in any environment)
capture_event("user_action", {
    "action_type": "button_click",
    "page": "home"
}, distinct_id="user123")
```

### User Identification

```python
from app.analytics.posthog_client import identify_user

# Identify a user
identify_user("user123", {
    "name": "John Doe",
    "email": "john@example.com"
})
```

### Checking Analytics Status

```python
from app.analytics import analytics_posthog_fastapi

if analytics_posthog_fastapi:
    print("PostHog is enabled")
else:
    print("PostHog is disabled")
```

## Environment Detection

The analytics module automatically detects the environment:

- **Development**: Analytics are disabled (no Lambda environment variables)
- **Production**: Analytics are enabled when running in AWS Lambda with proper API keys

## Adding New Analytics Providers

To add a new analytics provider (e.g., Mixpanel):

1. Create `mixpanel_client.py` following the same pattern
2. Use the naming convention: `analytics_mixpanel_fastapi`
3. Implement the required functions:
   - `get_mixpanel_client()`
   - `capture_event()`
   - `_is_lambda_environment()`
   - `_initialize_mixpanel()`
4. Add environment variables to `.env-template`
5. Update `__init__.py` to expose the new client

## Configuration

Add the following to your `.env` file for production:

```bash
# PostHog Configuration
POSTHOG_API_KEY=your_posthog_api_key_here
POSTHOG_HOST=https://app.posthog.com  # Optional

# Future: Amplitude Configuration
# AMPLITUDE_API_KEY=your_amplitude_api_key_here
```

## Logging

The analytics module provides comprehensive logging:

- **INFO**: Initialization status and environment detection
- **WARNING**: Missing API keys or configuration issues
- **ERROR**: Initialization failures or event capture errors
- **DEBUG**: Individual event captures and user operations

## Testing

The analytics module is designed to be safe for testing:

- All functions return `False` when analytics are disabled
- No exceptions are raised for missing providers
- Events are logged but not sent in development
- Lambda environment can be simulated for testing
