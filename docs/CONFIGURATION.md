# Configuration Guide

## Core Configuration

### Environment Variables

```bash
# Required
TIME_DELTA_HOURS=240              # Timeframe for article inclusion
TRANSFORMERS_CACHE=/path/to/cache # Cache directory for models

# Optional
LOG_LEVEL=INFO                    # Logging level
OUTPUT_FORMAT=json                # Output format
```

## Impact Configuration

### Impact Levels

```python
IMPACT_DOMAINS = {
    "High-Impact": {
        "points": 5,
        "domains": [
            "whitehouse.gov",
            "who.int",
            # ...
        ]
    },
    # ...
}
```

## Output Configuration

### Google Forms
```python
output_config = {
    "type": "google_forms",
    "form_id": "your-form-id",
    "fields": {
        "headline": "entry.1234",
        "url": "entry.5678"
    }
}
```

### Email Output
```python
email_config = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "your-email@domain.com",
    "password": "your-app-password"
}
```

### Slack Integration
```python
slack_config = {
    "webhook_url": "https://hooks.slack.com/...",
    "channel": "#news-updates"
}
```

## Clustering Configuration

```python
clustering_config = {
    "algorithm": "dbscan",
    "eps": 0.3,
    "min_samples": 2,
    "metric": "cosine"
}
```

## Advanced Settings

### Performance Tuning
```python
performance_config = {
    "max_concurrent_requests": 10,
    "request_timeout": 30,
    "cache_ttl": 3600
}
```

### NLP Settings
```python
nlp_config = {
    "model_name": "all-MiniLM-L6-v2",
    "similarity_threshold": 0.625,
    "language": "en"
}
```

## Example Configuration File

```yaml
# config.yaml
meridian:
  time_delta_hours: 72
  output:
    type: google_forms
    form_id: your-form-id
  clustering:
    algorithm: dbscan
    eps: 0.3
  nlp:
    model: all-MiniLM-L6-v2
    threshold: 0.625
```

## Best Practices

1. Use environment variables for sensitive data
2. Keep configuration in version control
3. Document all custom configurations
4. Use separate configs for development/production
