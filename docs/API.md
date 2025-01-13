# Meridian Insights API Documentation

## Core Classes

### MeridianAggregator

Main class for news aggregation and processing.

```python
class MeridianAggregator:
    def __init__(self, config: dict = None):
        """
        Initialize the aggregator.
        
        Args:
            config (dict, optional): Configuration dictionary
        """
        
    async def fetch_feeds(self) -> list:
        """
        Fetch articles from RSS feeds.
        
        Returns:
            list: List of fetched articles
        """
        
    def cluster_articles(self, articles: list) -> dict:
        """
        Cluster similar articles.
        
        Args:
            articles (list): List of articles to cluster
            
        Returns:
            dict: Clustered articles
        """

    def configure_output(self, config: dict) -> None:
        """
        Configure output destinations.
        
        Args:
            config (dict): Output configuration
        """
```

## Configuration Options

### Impact Scoring
```python
IMPACT_DOMAINS = {
    "High-Impact": {
        "points": 5,
        "domains": [...]
    },
    "Medium-High Impact": {
        "points": 3,
        "domains": [...]
    }
    # ...
}
```

### Output Configuration
```python
output_config = {
    "type": str,  # "google_forms", "slack", "email"
    "credentials": dict,  # Optional authentication details
    "destination": str,  # Output destination details
}
```

## Usage Examples

### Basic Usage
```python
from meridian import MeridianAggregator

aggregator = MeridianAggregator()
results = await aggregator.fetch_and_process()
```

### Custom Configuration
```python
config = {
    "time_delta_hours": 48,
    "similarity_threshold": 0.7,
    "min_cluster_size": 2
}

aggregator = MeridianAggregator(config)
```

## Error Handling

The API uses custom exceptions:
- `FeedFetchError`: RSS feed fetching errors
- `ClusteringError`: Article clustering errors
- `OutputError`: Output destination errors
