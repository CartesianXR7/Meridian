"""
Meridian Insights
================

A powerful RSS news aggregator with advanced clustering and ranking capabilities.
"""

__version__ = "0.4.0"
__author__ = "Stephen A. Hedrick"
__email__ = "Stephen@wavebound.io"

from .meridian import (
    MeridianAggregator,
    parse_sources_from_headlines,
    CustomJSONEncoder,
)

__all__ = [
    "MeridianAggregator",
    "parse_sources_from_headlines",
    "CustomJSONEncoder",
]
