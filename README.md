# Meridian Insights

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python Versions](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11-blue)

An intelligent RSS news aggregator that scores and clusters headlines using advanced NLP techniques and authority-based ranking.

## 🚀 Features

- **Smart Feed Aggregation**: Automatically fetches and processes articles from multiple RSS feeds
- **Impact Scoring**: Implements sophisticated source credibility scoring
- **Advanced Clustering**: Groups similar headlines using state-of-the-art NLP
- **Flexible Output**: Supports multiple output destinations (Google Forms, Email, Slack, Cloud Services)
- **Temporal Filtering**: Configurable timeframe for article inclusion
- **Source Classification**: Multi-tier authority classification system
- **Entity Recognition**: Advanced named entity extraction from headlines

## 📋 Prerequisites

- Python 3.9 or higher
- pip package manager
- Virtual environment (recommended)

## 🛠 Installation

```bash
# Clone the repository
git clone https://github.com/CartesianXR7/Meridian-Insights.git
cd Meridian-Insights

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install NLP models
python -m spacy download en_core_web_sm
python -m nltk.downloader vader_lexicon stopwords
```

## ⚙️ Configuration

### Environment Variables
- `TIME_DELTA_HOURS`: Number of hours to look back (default: 240)
- `TRANSFORMERS_CACHE`: Cache directory for transformer models

### Impact Levels
The system uses four authority levels for sources:
- High Impact (5 points)
- Medium-High Impact (3 points)
- Medium Impact (2 points)
- Medium-Low Impact (1 point)

## 📊 Usage Examples

### Basic Usage
```python
from meridian import MeridianAggregator

# Initialize aggregator
aggregator = MeridianAggregator()

# Run aggregation
results = aggregator.run()
```

### Custom Output Configuration
```python
# Configure for Google Forms output
aggregator.configure_output(
    output_type="google_forms",
    form_id="your-form-id"
)

# Or configure for multiple outputs
aggregator.configure_output([
    {"type": "google_forms", "form_id": "your-form-id"},
    {"type": "slack", "webhook_url": "your-webhook-url"}
])
```

## 🔧 Customization

### Adding New Sources
To add new RSS feeds, modify the `rss_feeds` list in the configuration:

```python
rss_feeds = [
    "https://example.com/feed",
    "https://another-source.com/rss"
]
```

### Adjusting Impact Scores
Modify the `IMPACT_DOMAINS` dictionary to adjust source credibility scores.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
flake8
black .
```

## 🔬 Technical Details

### Clustering Algorithm
- Uses DBSCAN clustering
- Sentence embeddings via SentenceTransformers
- Configurable similarity thresholds

### NLP Pipeline
1. Text preprocessing
2. Named entity recognition
3. Sentiment analysis
4. Semantic similarity computation

## 📈 Performance Considerations

- Async RSS feed fetching
- Optimized clustering for large datasets
- Configurable caching for embeddings

## 🔒 Security

- No sensitive credentials in source code
- Safe handling of external connections
- Input sanitization for all data sources

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

- Create an [Issue](https://github.com/CartesianXR7/Meridian-Insights/issues) for bug reports
- Start a [Discussion](https://github.com/CartesianXR7/Meridian-Insights/discussions) for questions
- Email: Stephen@wavebound.io

## 🙌 Acknowledgments

- All the open-source projects that made this possible
- Contributors and maintainers
- The NLP and RSS communities