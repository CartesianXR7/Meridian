#!/usr/bin/env python3
"""
Meridian RSS News Insights Aggregator
====================================

A powerful RSS news aggregator that scores and clusters headlines, with flexible output options.

Copyright (c) 2023 Stephen A. Hedrick and Wavebound, LLC
Licensed under the MIT License. See LICENSE file for details.

Author: Stephen A. Hedrick
Email: Stephen@wavebound.io
Repository: https://github.com/CartesianXR7/meridian

Features:
- Fetches articles from specified RSS feeds.
- Assigns impact scores based on predefined impact levels and source domains.
- Filters articles within configurable timeframes.
- Extracts named entities from article titles for topic-based clustering.
- Clusters similar headlines using SentenceTransformers and DBSCAN.
- Flexible output options (Google Forms, email, Slack, cloud services)
"""

import os
import re
import ssl
import json
import numpy as np
import asyncio
import subprocess
from tqdm import tqdm
from tqdm.asyncio import tqdm
from typing import List, Dict
from collections import defaultdict

from datetime import datetime, timedelta, date
from dateutil import parser as date_parser
from dateutil import tz
import pycountry
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
from googletrans import Translator

import feedparser
from bs4 import BeautifulSoup

from sentence_transformers import SentenceTransformer
from transformers import pipeline
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from ftfy import fix_text as ftfy_fix_text

import spacy
from fuzzywuzzy import fuzz
import nltk
from nltk.corpus import stopwords
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('stopwords')
nltk.download('vader_lexicon')

import language_tool_python
import contractions
import tldextract

import torch
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering
from newspaper import Article

from aiohttp import ClientSession
from collections import defaultdict, Counter

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email_validator import validate_email, EmailNotValidError
import logging


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("meridian.log"),
        logging.StreamHandler()
    ]
)

# Initialize global variables
nlp = None
# redis_client = None
translator = None

def fix_contractions(text):
    return contractions.fix(text)

def capitalize_proper_nouns(text: str) -> str:
    words = nltk.word_tokenize(text)
    pos_tags = nltk.pos_tag(words)
    capitalized_words = []
    for word, tag in pos_tags:
        if tag in ['NNP', 'NNPS']:
            word = word.capitalize()
        capitalized_words.append(word)
    return ' '.join(capitalized_words)

def divider() -> str:
    # Return an HTML divider
    return "<hr style='border:1px solid #ccc;'>\n"

# Initialize the grammar tool
tool = language_tool_python.LanguageTool('en-US')

def initialize_resources():
    global nlp, translator, sentiment_analyzer, s3_client
    # redis_client,

    nltk.data.path.append("/tmp/nltk_data")

    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=True)

    # Load spaCy model
    nlp = spacy.load("en_core_web_sm")

    # Initialize Google Translator
    translator = Translator()

    nltk.download("stopwords", download_dir="/tmp/nltk_data")

    # Ensure the VADER lexicon is downloaded
    nltk.download("vader_lexicon", download_dir="/tmp/nltk_data")

    # Initialize the VADER sentiment analyzer
    sentiment_analyzer = SentimentIntensityAnalyzer()

    # Update VADER lexicon with custom words specific to major news headlines
    new_words = {
        "catastrophe": -3.5,
        "disaster": -3.0,
        "explosion": -3.0,
        "explosions": -3.0,
        "blows up": -3.0,
        "war": -3.0,
        "tragedy": -3.0,
        "collapse": -3.0,
        "hurricane": -3.0,
        "earthquake": -3.0,
        "shooting": -3.0,
        "terrorist": -3.0,
        "fraud": -3.0,
        "impeach": -3.0,
        "impeached": -3.0,
        "impeachment": -3.0,
        "impeaches": -3.0,
        "attack": -2.5,
        "cyberattack": -2.5,
        "defeat": -2.5,
        "failure": -2.5,
        "fail": -2.5,
        "crash": -2.5,
        "recession": -2.5,
        "pandemic": -2.5,
        "plummet": -2.5,
        "conflict": -2.5,
        "flood": -2.5,
        "disinformation": -2.5,
        "urgent": -2.5,
        "security probe": -2.5,
        "critical": -2.0,
        "breaking": -2.0,
        "decline": -2.0,
        "wildfire": -2.0,
        "critical condition": -2.0,
        "brace for": -2.0,
        "hemoraging": -2.0,
        "braces for": -2.0,
        "loss": -2.0,
        "leak": -2.0,
        "siezes": -2.0,
        "low growth": -2.0,
        "high debt": -2.0,
        "weigh on": -2.0,
        "imminent risk": -2.0,
        "famine": -2.0,
        "virus": -2.0,
        "afraid": -2.0,
        "accident": -2.0,
        "nonexistent": -2.0,
        "storm": -2.0,
        "shocked": -2.0,
        "recall": -2.0,
        "recalls": -2.0,
        "could impact": -2.0,
        "explosions": -2.0,
        "explosion": -2.0,
        "drought": -2.0,
        "killed": -2.0,
        "alert": -1.5,
        "bailout": -1.5,
        "sanctions on": -1.5,
        "to cut up to": -1.5,
        "strike": -1.5,
        "hospitalized": -1.5,
        "antisemitic": -1.5,
        "trump": -1.5,
        "putin": -1.5,
        "nazi": -1.5,
        "nazis": -1.5,
        "protest": -1.5,
        "gap is growing": -1.5,
        "controversial": -1.0,
        "despite": -1.0,
        "migrants": -1.0,
        "condemn": -1.0,
        "racist": -1.0,
        "rubio": -1.0,
        "gaetz": -1.0,
        "gabbard": -1.0,
        "thune": -1.0,
        "ramaswamy": -1.0,
        "musk": -1.0,
        "flood": -1.0,
        "tax": -1.0,
        "react to": -1.0,
        "taxes": -1.0,
        "capital gains": -1.0,
        "plunge": -1.0,
        "disappointing": -1.0,
        "warning": -1.0,
        "closing": -1.0,
        "raising": -1.0,
        "faces at least": -1.0,
        "plot": -1.0,
        "assasination": -1.0,
        "to invest": 1.0,
        "nasa": 1.0,
        "launch of": 1.0,
        "launching": 1.0,
        "moon": 1.0,
        "stars": 1.0,
        "surge": 1.5,
        "help": 1.5,
        "invest": 1.5,
        "soar": 2.0,
        "soars": 2.0,
        "new high": 2.0,
        "launches": 2.0,
        "expedition": 2.0,
        "making it easier": 2.0,
        "gain": 2.0,
        "making it easier to": 2.0,
        "win": 2.0,
        "soars": 2.0,
        "growth": 2.0,
        "breakthrough": 2.5,
        "success": 2.5,
        "victory": 2.5,
        "turnout": 3,
        "nuclear power": 3,
        # Add more words as needed
    }
    sentiment_analyzer.lexicon.update(new_words)


rss_feeds = [
    # High-Impact Feeds
    "https://www.whitehouse.gov/briefing-room/feed/",
    "https://www.scotusblog.com/feed/",
    "https://www.weather.gov/news/",
    "https://www.govinfo.gov/rss/cprt.xml",
    "https://www.cio.gov/feed.xml",
    "https://www.ftc.gov/feeds/press-release.xml",
    "https://www.nass.usda.gov/rss/news.xml",
    "https://www.usda.gov/rss/latest-releases.xml",
    "https://www.rd.usda.gov/rss.xml",
    "https://www.nrc.gov/public-involve/rss?feed=news",
    "https://www.usace.army.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=9&Site=420&Category=20166&isdashboardselected=0&max=20",
    "https://www.census.gov/economic-indicators/indicator.xml",
    "https://www.nasa.gov/rss/dyn/breaking_news.rss",
    "https://www.nature.com/nature.rss",
    "https://www.sciencemag.org/rss/news_current.xml",
    "https://www.theguardian.com/world/world-health-organization/rss",
    "https://www.nih.gov/news-releases/feed.xml",
    "https://tools.cdc.gov/api/v2/resources/media/733939.rss",
    "https://tools.cdc.gov/api/v2/resources/media/132608.rss",
    "https://tools.cdc.gov/api/v2/resources/media/320567.rss",
    "https://tools.cdc.gov/api/v2/resources/media/132782.rss",
    "https://tools.cdc.gov/api/v2/resources/media/316422.rss",
    "https://www.ecb.europa.eu/rss/press.html",
    "https://www.federalreserve.gov/feeds/press_all.xml",
    "https://www.imf.org/en/News/RSS?TemplateID={2FA3421A-F179-46B6-B8D9-5C65CB4A6584}",
    "https://www.sec.gov/news/pressreleases.rss",
    "https://www.nist.gov/news-events/news/rss.xml",
    "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
    "https://isc.sans.edu/rssfeed_full.xml",
    "https://www.usgs.gov/news/149245/feed",
    "https://www.esa.int/rssfeed/Our_Activities/Telecommunications_Integrated_Applications",
#    "http://www.worldbank.org/en/news/rss",
    "https://www.rand.org/news/press.xml",
    "https://www.energylivenews.com/feed/",
#    "https://www.iea.org/newsroom/rss",
    "https://unevoc.unesco.org/unevoc_rss.xml",
    "https://www.iaea.org/feeds/topnews",
    "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/oci-press-releases/rss.xml",
#    "https://www.osha.gov/news/newsreleases.xml",
    "https://oceanservice.noaa.gov/rss/nosnews.xml",
    "https://oceanservice.noaa.gov/newsroom/nosmedia.xml",
    "https://www.safetyandhealthmagazine.com/rss/topic/99-news",
    "https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?max=10&ContentType=1&Site=945",
    "https://www.wipo.int/pressroom/en/rss.xml",
#    "https://www.fao.org/feeds/fao-newsroom-rss", #https://www.fao.org/news/rss-feed/en/
    "https://www.eia.gov/rss/press_rss.xml",
#    "https://www.rigzone.com/news/rss/rigzone_headlines.aspx",
    "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22general-interest%22%7D",
    "https://www.irena.org/iapi/rssfeed/News",
    "https://www.itu.int/hub/tag/itu-t/feed/",
#    "https://www.ifc.org/wps/wcm/connect/corp_ext_content/ifc_external_corporate_site/home/newsroom/media_rss",
    "https://news.mit.edu/topic/mitmachine-learning-rss.xml",
    "https://news.mit.edu/topic/mitcyber-security-rss.xml",
    "https://www.ft.com/news-feed?format=rss",
    "https://nasdaqtrader.com/rss.aspx?feed=currentheadlines&categorylist=0",
    "https://www.nasdaq.com/feed/nasdaq-original/rss.xml",
    "https://www.nasdaq.com/feed/rssoutbound?category=Commodities",
    "https://www.nasdaq.com/feed/rssoutbound?category=IPOs",
    "https://www.nasdaq.com/feed/rssoutbound?category=Markets",
    "https://www.nasdaq.com/feed/rssoutbound?category=Stocks",
    "https://www.nasdaq.com/feed/rssoutbound?category=Artificial+Intelligence",
    "https://www.nasdaq.com/feed/rssoutbound?category=FinTech",
    "https://www.nasdaq.com/feed/rssoutbound?category=Innovation",
    "https://www.nasdaq.com/feed/rssoutbound?category=Nasdaq",
    "https://www.nasdaq.com/feed/rssoutbound?category=Technology",
    "https://asia.nikkei.com/rss/feed/nar",
    "https://travel.state.gov/_res/rss/TAsTWs.xml",
    "https://www.railway.supply/en/news-en/feed/",
    "https://markets.newyorkfed.org/read?productCode=50&eventCodes=500&limit=25&startPosition=0&sort=postDt:-1&format=xml",
    "https://www.prnewswire.com/rss/news-releases-list.rss",
    "https://www.opec.org/opec_web/en/pressreleases.rss",
    "https://www.windpowermonthly.com/rss/news",
    "https://feed.businesswire.com/rss/home/?rss=G1QFDERJXkJeEF9YXA==&_gl=1*1lurxps*_gcl_au*MTI0MDcyOTY2Mi4xNzM0NjUwMjk4*_ga*MTQyMTk2MzY1MC4xNzM0NjUwMjk4*_ga_ZQWF70T3FK*MTczNDY1MDI5Ny4xLjEuMTczNDY1MDQzMy40Ni4wLjA.",
    "https://feed.businesswire.com/rss/home/?rss=G1QFDERJXkJeGVtWWQ==&_gl=1*1di1nun*_gcl_au*MTI0MDcyOTY2Mi4xNzM0NjUwMjk4*_ga*MTQyMTk2MzY1MC4xNzM0NjUwMjk4*_ga_ZQWF70T3FK*MTczNDY1MDI5Ny4xLjEuMTczNDY1MDQzMy40Ni4wLjA.",
    "https://feed.businesswire.com/rss/home/?rss=G1QFDERJXkJeEFtRXw==&_gl=1*ibfq09*_gcl_au*MTI0MDcyOTY2Mi4xNzM0NjUwMjk4*_ga*MTQyMTk2MzY1MC4xNzM0NjUwMjk4*_ga_ZQWF70T3FK*MTczNDY1MDI5Ny4xLjEuMTczNDY1MDY0NC42MC4wLjA.",
    "https://feed.businesswire.com/rss/home/?rss=G1QFDERJXkJeEFtRWA==&_gl=1*ucren7*_gcl_au*MTI0MDcyOTY2Mi4xNzM0NjUwMjk4*_ga*MTQyMTk2MzY1MC4xNzM0NjUwMjk4*_ga_ZQWF70T3FK*MTczNDY1MDI5Ny4xLjEuMTczNDY1MDY1OS40NS4wLjA.",
    "https://www.usgs.gov/news/all/feed",
    "https://www.dol.gov/rss/releases.xml",
    "https://www.justice.gov/news/rss?m=1",
    "https://federalnewsnetwork.com/category/all-news/feed/",
    "https://www.space.com/home/feed/site.xml",
    "https://spacenews.com/feed/",
    "https://www.bankinfosecurity.com/rss-feeds",
    "https://www.cisa.gov/news.xml",
    "https://krebsonsecurity.com/feed/",
#    "https://www.cshub.com/rss/news",
    "https://ourworldindata.org/atom-data-insights.xml",
    "https://www.spglobal.com/commodityinsights/en/rss-feed/oil#",
    "https://www.spglobal.com/commodityinsights/en/rss-feed/natural-gas",
    "https://www.spglobal.com/commodityinsights/en/rss-feed/coal",
    "https://www.spglobal.com/commodityinsights/en/rss-feed/electric-power", 
    "https://www.spglobal.com/commodityinsights/en/rss-feed/metals",
    "https://www.spglobal.com/commodityinsights/en/rss-feed/shipping",
    "https://www.spglobal.com/commodityinsights/en/rss-feed/agriculture",
    "https://www.spglobal.com/commodityinsights/en/rss-feed/lng",
    "https://www.spglobal.com/commodityinsights/en/rss-feed/energy-transition",
#    "https://www.bls.gov/feed/cpi_latest.rss",
    "https://www.chicagofed.org/forms/rss/DataReleases",
    "https://www.consumerfinance.gov/about-us/newsroom/feed/",
    "https://www.chicagofed.org/forms/rss/NewsReleases",
    "https://www.aba.com/rss/press",
    "https://www.federalreserve.gov/feeds/press_all.xml", # fed press all
    "https://www.federalreserve.gov/feeds/press_monetary.xml", # fed monetary press all
    "https://www.federalreserve.gov/feeds/Data/H15_H15_RIFSPFF_N.B.XML", # fed funds
    "https://www.federalreserve.gov/feeds/Data/H15_H15_RIFSRP_F02_N.B.XML", # discount rate release
    "https://www.hkex.com.hk/Services/RSS-Feeds/News-Releases?sc_lang=en", # HKEX
#    "https://news.crunchbase.com/feed/",
#    "https://www.digitaljournal.com/feed",
    "https://www.elastic.co/blog/feed",
    "https://www.uscourts.gov/news/rss",


    # Medium-High Impact Feeds
    "https://www.schneier.com/feed/atom/",
    "https://news.sophos.com/en-us/category/threat-research/feed/",
    "https://securelist.com/feed/",
    "https://www.bleepingcomputer.com/feed/",
    "https://feeds.feedburner.com/eset/blog",
    "https://feeds.feedburner.com/TheHackersNews?format=xml",
    "https://github.blog/engineering.atom",
    "https://developer.nvidia.com/blog/feed",
    "https://www.adp.com/~/spark_feed/people-management",
    "https://www.globenewswire.com/RssFeed/country/United%20States/feedTitle/GlobeNewswire%20-%20News%20from%20United%20States",
    "https://www.labornotes.org/feed",
    "https://audioboom.com/channels/4905579.rss",
#    "https://thebusinessjournal.com/feed/",
    "https://newsletter.blockthreat.io/feed",
    "https://www.c4isrnet.com/arc/outboundfeeds/rss/category/cyber/?outputType=xml",
    "https://blog.criminalip.io/feed/",
    "https://www.eff.org/rss/updates.xml",
    "https://mondovisione.com/media-and-resources/news/rss/",
    "https://www.morningstar.ca/ca/news/27103/RSS.aspx",
    "https://mises.org/rss.xml",
    "https://feeds.feedburner.com/LibertyStreetEconomics",
    "https://ai-techpark.com/feed/",
    "https://www.artificialintelligence-news.com/feed/",
    "https://lastweekin.ai/feed",
    "https://feeds.feedburner.com/RBloggers",
    "https://news.mit.edu/topic/mitmachine-learning-rss.xml", 
    "https://feeds.feedburner.com/blogspot/gJZg",
    "https://www.reddit.com/r/machinelearningnews/hot/.rss",
    "https://www.automotive-iq.com/rss/categories/cybersecurity",
    "https://www.automotive-iq.com/rss/categories/industry-reports",
    "https://www.automotive-iq.com/rss/news",
    "https://www.automotive-iq.com/rss/news-trends",
    "https://spectrum.ieee.org/customfeeds/feed/all-topics/rss", 
    "https://www.rcrwireless.com/feed",
    "https://feeds.feedburner.com/edgeindustryreview",
    "https://feed.theregister.com/atom?q=edge+computing",
    "https://www.manufacturingtomorrow.com/rss/news/",
    "https://feeds.feedburner.com/biometricupdate",
    "https://www.finextra.com/rss/headlines.aspx",
    "https://www.manufacturingtomorrow.com/rss/news/",
    "https://feeds.feedburner.com/sc247/rss/news",
    "https://dataprivacymanager.net/feed",
    "https://www.earthquakenewstoday.com/feed/",
    "https://www.rnz.co.nz/rss/world.xml",
    "https://www.rnz.co.nz/rss/media-technology.xml",
    "https://feedx.net/rss/ap.xml",
#    "https://www.reutersagency.com/feed/?taxonomy=best-customer-impacts&post_type=best",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://time.com/feed/",
    "https://chaski.huffpost.com/us/auto/vertical/world-news",
#    "https://www.telegraph.co.uk/news/rss.xml",
    "https://feeds.feedburner.com/NDTV-LatestNews",
    "https://www.forbes.com/real-time/feed2/",
    "https://feeds.npr.org/1001/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://feeds.bloomberg.com/economics/news.rss",
    "https://feeds.bloomberg.com/industries/news.rss",
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    "https://www.economist.com/sections/economics/rss.xml",
    "https://feeds.marketwatch.com/marketwatch/topstories/",
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "https://www.investing.com/rss/news.rss",
    "https://www.wired.com/feed/rss",
    "https://www.techradar.com/rss",
    "https://arstechnica.com/feed/",
    "https://qz.com/rss",
    "http://feeds.hbr.org/harvardbusiness",
#    "https://news.crunchbase.com/feed/",
    "https://techcrunch.com/tag/saas/feed/",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://rss.dw.com/xml/rss-en-all",
    "https://feeds.feedburner.com/fastcompany/headlines",
    "https://feeds.feedburner.com/InformationIsBeautiful",
    
    # Medium Impact Feeds
    "https://www.cbsnews.com/latest/rss/main",
    "https://feeds.abcnews.com/abcnews/topstories",
    "https://www.latimes.com/world-nation/rss2.0.xml",
    "https://www.globaltimes.cn/rss/outbrain.xml",
    "https://feeds.nbcnews.com/feeds/topstories",
    "https://moxie.foxnews.com/google-publisher/world.xml",
    "https://rss.cnn.com/rss/edition.rss",
    "https://feeds.washingtonpost.com/rss/business",
    "https://www.barchart.com/news/rss/commodities",
    "https://www.barchart.com/news/rss/financials",
    "https://www.barchart.com/news/authors/rss",
    "https://biztoc.com/feed",
    "https://feeds.feedburner.com/InformationIsBeautiful",
    "https://www.bitdefender.com/nuxt/api/en-us/rss/hotforsecurity/industry-news/",
    "https://bluepurple.binaryfirefly.com/feed",
    "https://www.cyberdefensemagazine.com/feed/",
    "https://cyberscoop.com/feed/",
    "https://www.cybersecuritydive.com/feeds/news/",
    "https://hackread.com/feed/",
    
    # Medium-Low Impact Feeds
    "http://feeds.feedburner.com/DrudgeReportFeed",
    "https://www.theregister.com/headlines.rss",
    "https://rss.slashdot.org/Slashdot/slashdot",
    "https://gtmnow.com/feed/",
    "https://www.thesalesblog.com/blog/rss.xml",
    "https://oldschoolsalesdog.com/feed/",
#    "https://www.producthunt.com/feed?category=undefined",
#    "https://age-of-product.com/category/news/",
#    "https://spectechular.walkme.com/feed/",
    "https://feeds.feedburner.com/StrategyBusiness-Manufacturing",
    "https://www.waterstechnology.com/feeds/rss/category/operations",
    "https://feeds.feedburner.com/StrategyBusiness-Strategy",
    "https://www.allthingssupplychain.com/feed/",
    "https://www.supplychainbrain.com/rss/articles",
    "https://theundercoverrecruiter.com/feed/",
    "https://recruitingblogs.com/profiles/blog/feed?xn_auth=no",
    "https://legaltechnology.com/feed/",
    "https://medium.com/feed/artificialis",
    "https://www.waterstechnology.com/feeds/rss/category/data-management",
    "https://tech.eu/category/deep-tech/feed",
#    "https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml",
]


def clean_html(raw_html):
    cleanr = re.compile("<.*?>")
    return re.sub(cleanr, "", raw_html)


def extract_text_from_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def preprocess_text(text: str) -> str:
    """
    Preprocesses the input text by lemmatizing, removing stopwords and punctuation.

    Parameters:
    - text (str): The text to preprocess.

    Returns:
    - str: The preprocessed text.
    """
    doc = nlp(text)
    return ' '.join([token.lemma_ for token in doc if not token.is_stop and not token.is_punct])



def extract_entities(text: str) -> List[str]:
    doc = nlp(text)
    return [ent.text for ent in doc.ents]


async def fetch_feed(session, feed_url: str) -> str:
    try:
        async with session.get(feed_url) as response:
            if response.status == 200:
                return await response.text()
            else:
                logging.error(f"Failed to fetch {feed_url}: Status {response.status}")
                return None
    except Exception as e:
        logging.error(f"Error fetching {feed_url}: {e}")
        return None


async def fetch_all_feeds(rss_feeds: List[str]) -> List[str]:
    async with ClientSession() as session:
        tasks = [fetch_feed(session, feed_url) for feed_url in rss_feeds]
        return await asyncio.gather(*tasks)


def process_article(entry, feed_url: str) -> Dict:
    if not hasattr(entry, "link"):
        return None

    article_url = entry.link

    article_data = {
        "title": entry.get("title", "Untitled Article"),
        "url": article_url,
        "publish_date": entry.get("published", entry.get("updated", "")),
        "source": feed_url,
        "content": ''
    }

    # Try to get the content from the entry
    if 'content' in entry and entry.content:
        content = entry.content[0].value if isinstance(entry.content, list) else entry.content
        article_data['content'] = extract_text_from_html(content)
    elif 'summary' in entry and entry.summary:
        article_data['content'] = extract_text_from_html(entry.summary)
    else:
        article_data['content'] = ''

    # If content is still empty, fetch the article
    if not article_data['content'].strip():
        try:
            article = Article(article_url)
            article.download()
            article.parse()
            article_data['content'] = article.text
        except Exception as e:
            logging.error(f"Error fetching content from {article_url}: {e}")
            article_data['content'] = ''

    return article_data

#    if 'content' in entry:
#        content = entry.content[0].value if isinstance(entry.content, list) else entry.content
#        article_data['content'] = extract_text_from_html(content)
#    else:
#        article_data['content'] = article_data['summary']

#    try:
#        lang = translator.detect(article_data['content']).lang
#        if lang != 'en':
#            article_data['content'] = translator.translate(article_data['content'], src=lang, dest='en').text
#            article_data['title'] = translator.translate(article_data['title'], src=lang, dest='en').text
#    except Exception as e:
#        logging.error(f"Language detection/translation error: {e}")
#
#    redis_client.setex(article_id, 86400, json.dumps(article_data))

#    return article_data

def calculate_headline_count(article: Dict, all_articles: List[Dict]) -> int:
    target_headline = article.get("title", "").strip().lower()
    if not target_headline:
        return 0
    count = sum(1 for a in all_articles if a.get("title", "").strip().lower() == target_headline)
    return count

def calculate_priority_score(article: Dict, all_articles: List[Dict]) -> float:
    sentiment_score, impact_score, action_score = calculate_scores_for_headline(article.get("title", ""))
    
    # Adjust the weights as needed
    priority_score = 0.4 * sentiment_score + 0.3 * impact_score + 0.3 * action_score
    return priority_score


def process_feeds(rss_feeds: List[str]) -> List[Dict]:
    # Run the asynchronous feed fetching and processing
    loop = asyncio.get_event_loop()
    feed_contents = loop.run_until_complete(fetch_all_feeds(rss_feeds))
    articles_content = []

    for feed_content, feed_url in tqdm(
        zip(feed_contents, rss_feeds), total=len(rss_feeds), desc="Processing feeds"
    ):
        if feed_content:
            feed = feedparser.parse(feed_content)
            if "entries" in feed and len(feed.entries) > 0:
                for entry in feed.entries:
                    article_data = process_article(entry, feed_url)
                    if article_data:
                        articles_content.append(article_data)
            else:
                logging.warning(f"No entries found in feed: {feed_url}")

    logging.info(
        f"Processed {len(articles_content)} articles from {len(rss_feeds)} feeds"
    )
    return articles_content


# Define common time zone abbreviations and their mappings
tzinfos = {
    "EST": tz.gettz("America/New_York"),
    "EDT": tz.gettz("America/New_York"),
    "CST": tz.gettz("America/Chicago"),
    "CDT": tz.gettz("America/Chicago"),
    "MST": tz.gettz("America/Denver"),
    "MDT": tz.gettz("America/Denver"),
    "PST": tz.gettz("America/Los_Angeles"),
    "PDT": tz.gettz("America/Los_Angeles"),
    "BST": tz.gettz("Europe/London"),
    "GMT": tz.gettz("Europe/London"),
    "IST": tz.gettz("Asia/Kolkata"),
    "UTC": tz.UTC,
    # Add other time zones as needed
}


def fix_invalid_time(date_str):
    # Match times with hour '24'
    match = re.search(r"24:(\d{2}):(\d{2})", date_str)
    if match:
        # Replace '24' with '00'
        fixed_time = "00:{}:{}".format(match.group(1), match.group(2))
        # Replace in the date string
        date_str = date_str.replace(
            "24:{}:{}".format(match.group(1), match.group(2)), fixed_time
        )
        # Indicate that the date should be incremented
        increment_day = True
    else:
        increment_day = False
    return date_str, increment_day


def filter_and_preprocess_articles(articles_content: List[Dict]) -> List[Dict]:
    """
    Filters articles within a 7-day window and preprocesses their content.

    Parameters:
    - articles_content (List[Dict]): The list of all fetched articles.

    Returns:
    - List[Dict]: The list of filtered and preprocessed articles.
    """
    logging.info("Filtering articles by date and preprocessing...")
    filtered_articles = []
    today = datetime.now(tz.gettz("America/Chicago")).date()
    seven_days_ago = today - timedelta(days=6)
    future_allowed = today + timedelta(days=1)

    for article in tqdm(articles_content, desc="Preprocessing articles"):
        publish_date = article.get("publish_date")
        publish_datetime = today  # Default to today

        if publish_date:
            # Fix invalid times
            fixed_publish_date, increment_day = fix_invalid_time(publish_date)
            try:
                # Try parsing the date using dateutil.parser with tzinfos
                parsed_date = date_parser.parse(
                    fixed_publish_date, tzinfos=tzinfos, fuzzy=True
                )
                if increment_day:
                    parsed_date += timedelta(days=1)
                publish_datetime = parsed_date.date()
            except (ValueError, TypeError) as e:
                logging.warning(
                    f"Unrecognized date format for article '{article['title']}': {publish_date}. Assigning today's date."
                )
                publish_datetime = today  # Assign today's date

        else:
            logging.warning(
                f"No publish date for article '{article['title']}'. Assigning today's date."
            )
            publish_datetime = today  # Assign today's date

        # Assign the parsed or default date with consistent key name
        article["publish_datetime"] = publish_datetime

        # Calculate 'headline_count' and 'priority_score'
        article["headline_count"] = calculate_headline_count(article, articles_content)
        article["priority_score"] = calculate_priority_score(article, articles_content)

        # Check if the article falls within the desired date range
        if seven_days_ago <= publish_datetime <= future_allowed:
            article["preprocessed_content"] = preprocess_article_content(article["content"])
            article["entities"] = extract_entities(article["title"])
            if article["title"] and len(article["title"].split()) >= 4:
                # Only add articles with non-empty title and at least 4 words
                filtered_articles.append(article)
            else:
                logging.info(f"Skipping article with short title: '{article['title']}'")
        else:
            logging.info(
                f"Skipping article outside the 7-day window: '{article['title']}' (Date: {publish_datetime})"
            )

    logging.info(f"Filtered and preprocessed {len(filtered_articles)} articles")
    return filtered_articles



def calculate_similarity(article1, article2):
    # Title similarity using fuzzy matching
    title_similarity = fuzz.token_set_ratio(article1["title"], article2["title"]) / 100

    # Title similarity using TF-IDF and cosine similarity
    if article1["title"] and article2["title"]:
        try:
            # Use bigrams and ignore common stopwords with TF-IDF
            tfidf = TfidfVectorizer(
                ngram_range=(1, 2), stop_words="english"
            ).fit_transform([article1["title"], article2["title"]])

            # Calculate cosine similarity between the two titles
            title_similarity2 = cosine_similarity(tfidf[0], tfidf[1])[0][0]

            # Only consider similarity scores above a set threshold 0-1
            if title_similarity2 < 0.85:
                title_similarity2 = 0  # Set to 0 if below threshold
        except ValueError:
            title_similarity2 = 0
    else:
        title_similarity2 = 0

    # Temporal similarity based on date only
    date_diff = abs(
        (article1["publish_datetime"] - article2["publish_datetime"]).days
    )  # Difference in days
    temporal_similarity = (
        1 if date_diff == 0 else 0
    )  # Full similarity if published on the same day, otherwise 0

    # Combine similarities with weights
    total_similarity = (
        0.3 * title_similarity + 0.6 * title_similarity2 + 0.1 * temporal_similarity
    )

    return total_similarity


# Original clustering function using nested loops (commented out)
# def cluster_articles(filtered_articles):
#     logging.info("Clustering similar articles...")
#     num_articles = len(filtered_articles)

#     # Adding a check to ensure there are articles to cluster
#     if num_articles == 0:
#         logging.error("No articles available for clustering.")
#         return defaultdict(list)  # Return empty result

#     similarity_matrix = np.zeros((num_articles, num_articles))

#     for i in tqdm(range(num_articles), desc="Calculating similarities"):
#         for j in range(i + 1, num_articles):
#             similarity = calculate_similarity(
#                 filtered_articles[i], filtered_articles[j]
#             )
#             similarity_matrix[i, j] = similarity_matrix[j, i] = similarity

#     # Use a higher threshold for clustering
#     threshold = 0.4
#     clustered_articles = defaultdict(list)

#     for i in range(num_articles):
#         cluster_found = False
#         for cluster_id, cluster in clustered_articles.items():
#             if any(
#                 similarity_matrix[i][filtered_articles.index(article)] >= threshold
#                 for article in cluster
#             ):
#                 clustered_articles[cluster_id].append(filtered_articles[i])
#                 cluster_found = True
#                 break
#         if not cluster_found:
#             new_cluster_id = len(clustered_articles)
#             clustered_articles[new_cluster_id].append(filtered_articles[i])

#     # Logging the number of clusters found
#     logging.info(f"Clustering complete. Found {len(clustered_articles)} clusters")
#     return clustered_articles

# Alternative clustering function using Agglomerative Clustering (commented out)
# def cluster_articles(filtered_articles):
#     logging.info("Clustering similar articles...")
#     num_articles = len(filtered_articles)

#     if num_articles == 0:
#         logging.error("No articles available for clustering.")
#         return defaultdict(list)

#     # Extract article texts
#     texts = [article["title"] for article in filtered_articles]

#     # Convert texts to TF-IDF vectors
#     vectorizer = TfidfVectorizer()
#     tfidf_matrix = vectorizer.fit_transform(texts)

#     # Compute cosine similarity matrix
#     similarity_matrix = cosine_similarity(tfidf_matrix)
#     np.fill_diagonal(similarity_matrix, 0)  # Ensure self-similarity is 1

#     # Convert similarity to distance matrix
#     distance_matrix = 1 - similarity_matrix

#     # Perform Agglomerative Clustering
#     threshold = 0.85  # Adjust as needed
#     clustering_model = AgglomerativeClustering(
#         n_clusters=None,
#         # affinity='precomputed',
#         linkage='average',
#         distance_threshold=threshold
#     )
#     clustering_model.fit(distance_matrix)

#     # Organize articles into clusters
#     clustered_articles = defaultdict(list)
#     for idx, label in enumerate(clustering_model.labels_):
#         clustered_articles[label].append(filtered_articles[idx])

#     logging.info(f"Clustering complete. Found {len(clustered_articles)} clusters")
#     return clustered_articles


# New clustering function using Hugging Face Sentence Transformers and DBSCAN
def cluster_articles(filtered_articles):
    logging.info(
        "Clustering similar articles using Sentence Transformers and DBSCAN..."
    )
    num_articles = len(filtered_articles)

    if num_articles == 0:
        logging.error("No articles available for clustering.")
        return defaultdict(list)

    # Extract article titles
    texts = [article["title"] for article in filtered_articles]

    # Load the pre-trained Sentence Transformer model
    model_name = "all-MiniLM-L6-v2"  
    model = SentenceTransformer(model_name)

    # Generate embeddings for the titles
    embeddings = model.encode(texts, show_progress_bar=True)

    # Normalize embeddings
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

    # Use DBSCAN for clustering, adjust as needed
    clustering_model = DBSCAN(eps=0.25, min_samples=2, metric="cosine")
    clustering_model.fit(embeddings)

    labels = clustering_model.labels_

    # Organize articles into clusters
    clustered_articles = defaultdict(list)
    for idx, label in enumerate(labels):
        if label == -1:
            # Noise point, assign to its own cluster
            clustered_articles[f"noise_{idx}"].append(filtered_articles[idx])
        else:
            clustered_articles[label].append(filtered_articles[idx])

    logging.info(f"Clustering complete. Found {len(clustered_articles)} clusters")
    return clustered_articles


def is_valid_headline(title):
    # Avoid headlines that are likely advertisements, video streams, or news bulletins
    invalid_patterns = [
        r"(?i)\bnews bulletin\b",
        r"(?i)\bvideo:",
        r"(?i)\bsports\b",
        r"(?i)\watch on tv\b",
        r"(?i)\bonline for free\b",
        r"(?i)\bhow to watch\b",
        r"(?i)\bathlete\b",
        r"(?i)\bhow to get\b",
        r"(?i)\bhints, answers\b",
        r"(?i)\bcelebrity\b",
        r"(?i)\bholiday\b",
        r"(?i)\bhow to\b",
        r"(?i)\bwatch live:",
        r"(?i)\broundup:",
        r"(?i)\bhurdle hints\b",
        r"(?i)\bstreaming",
        r"(?i)\bbest restaurants\b",
        r"(?i)\bnow available\b",
        r"(?i)\bin free\b",
        r"(?i)\bcustomer\b",
        r"(?i)\bvideo...\b",
        r"(?i)\bmensware",
        r"(?i)\bfashion",
        r"(?i)\bpromo",
        r"(?i)\btouchscreen",
        r"(?i)\bblogging",
        r"(?i)\btested and reviewed\b",
        r"(?i)\bthe best\b",
        r"(?i)\bbest movies\b",
        r"(?i)\blower blood pressure\b",
        r"(?i)\bshare the 1\b",
        r"(?i)\bshare the one\b",
        r"(?i)\bdegree",
        r"(?i)\bmentorship",
        r"(?i)\bhelp\b",
        r"(?i)\blowest price\b",
        r"(?i)\baseball\b",
        r"(?i)\bfootball\b",
        r"(?i)\basketball\b",
        r"(?i)\depository\b",
        r"(?i)\dividend\b",
        r"(?i)\sneaker\b",
        r"(?i)\bstar-studded\b",
        r"(?i)\bwordle\b",
        r"(?i)\bget the new\b",
        r"(?i)\bpromo code\b",
        r"(?i)\breview:\b",
        r"(?i)\binnovation",
        r"(?i)\bstormcast",
        r"(?i)\bhas anyone ever\b",
        r"(?i)\btoday:",
        r"(?i)\bawesome",
        r"(?i)\btop picks\b",
        r"(?i)\bbest phones\b",
        r"(?i)\bhoroscope:",
        r"(?i)\bapple launches\b",
        r"(?i)\bquick take:\b",
        r"(?i)\banalysis",
        r"(?i)\bcoupon",
        r"(?i)\bsavings",
        r"(?i)\bwebinar",
        r"(?i)\bgrammy",
        r"(?i)\bvideo",
        r"(?i)\bReview:",
        r"(?i)\bmorning read\b",
        r"(?i)\bmy notes\b",
        r"(?i)\bdownload:\b",
        r"(?i)\bcheap",
        r"(?i)\bmac",
        r"(?i)\bearnings call:\b",
        r"(?i)\best things\b",
        r"(?i)\btoday:",
        r"(?i)\bshopping season\b",
        r"(?i)\bwhat to expect\b",
        r"(?i)\bhints and answers\b",
        r"(?i)\bprime day\b",
        r"(?i)\bbrands\b",
        r"(?i)\bfor free\b",
        r"(?i)\bnominated",
        r"(?i)\bwatch:",
        r"(?i)\bclosing bell\b",
        r"(?i)\bdaily discussion\b",
        r"(?i)\bsigns of ageing\b",
        r"(?i)\bvs\.\b",
        r"(?i)\bv\.\b",
        r"(?i)\bvs\b",
        r"(?i)\bv\b",
        r"(?i)\bleague\b",
        r"(?i)\btrophy\b",
        r"(?i)\bmanager\b",
        r"(?i)\bwhat to know about\b",
        r"(?i)\bblack friday\b",
        r"(?i)\bcrossword\b",
        r"(?i)\blivestream\b",
        r"(?i)\bbusinessweek:",
        r"(?i)\bearnings snapshot:",
        r"(?i)\bearnings preview\b",
        r"(?i)\bbloomberg surveillance\b",
        r"(?i)\bbloomberg open interest\b",
        r"(?i)\bperforming badly\b",
        r"(?i)\bopinion:",
        r"(?i)\bphotos:",
        r"(?i)\blive updates\b",
        r"(?i)\blive thread\b",
        r"(?i)\badvertisement\b",
        r"(?i)\bsponsored content\b",
    ]
    return not any(re.search(pattern, title) for pattern in invalid_patterns)


def prioritize_headline(title, content):
    priority_keywords = [
        # BUSINESS
        "business",
        "venture capital",
        "private equity",
        "seed funding",
        "series-a",
        "series a",
        "series-b",
        "series b",
        "tax",
        "taxes",
        "LLC",
        "saas",
        "b2b",
        "ecommerce",
        # ECONOMIC
        "economy",
        "economic",
        "economies",
        "central bank",
        "rate cuts",
        "housing",
        "mortgage rates",
        "fomc",
        "monetary",
        "financial",
        "business",
        "federal reserve",
        "inflation",
        "gdp",
        "jobs",
        "strike",
        "markets",
        "deal",
        "layoff",
        "layoffs",
        "prices",
        "corporate",
        "enterprise",
        "volatility",
        "equities",
        "securities",
        "futures",
        "crypto",
        "bitcoin",
        "ethereum",
        "dogecoin",
        "xrp",
        "ripple",
        "shiba",
        "exchange",
        "earnings",
        "bankruptcy",
        "bankrupt",
        "acquire",
        "acquisition",
        # CLIMATE
        "weather",
        "weather pattern",
        "climate",
        "natural disaster",
        "fema",
        "hurricane",
        "tropical storm",
        "tropical development",
        "storm brews",
        "flooding",
        "floods",
        "volcanic",
        "wildfire",
        "tsunami",
        "freak",
        "torrential",
        "flare",
        "climate change",
        "asteroid",
        "pollution",
        "earthquake",
        "environment",
        "freeze",
        "frozen",
        "cold snap",
        "tornado",
        "eclipse",
        "air quality",
        "smog",
        # COMODITIES
        "silicon",
        "cobalt",
        "graphite",
        "gold",
        "silver",
        # CYBER
        "hack",
        "breach",
        "cyber",
        "leak",
        "leaked",
        "hackers",
        "misinformation",
        "compromise",
        "back door",
        "backfire",
        "documents",
        "secret",
        "influenced",
        # ENERGY
        "energy",
        "oil",
        "renewable",
        "solar",
        "wind",
        "turbine",
        "reactors",
        "petroleum",
        "gasoline",
        "gas prices",
        "nuclear",
        "thermonuclear",
        "electric grid",
        "power grid",
        "blackout",
        "blackouts",
        "brownout",
        "brownouts",
        "without water",
        "without power",
        "without electricity",
        # FINANCIAL MARKETS
        "stock market",
        "mag 7",
        "magnificent 7",
        "s&p",
        "prices fall",
        "prices soar",
        "faang",
        "index",
        "plunge",
        "dow",
        "valuation",
        "tesla",
        "google",
        "amd",
        "nvidia",
        "netflix",
        "meta",
        "amazon",
        "apple",
        "boeing",
        "spacex",
        "starlink",
        "dell",
        "twitter",
        "gamestop",
        "microsoft",
        "intel",
        "ibm",
        "investors",
        "stock",
        "enterprise",
        "executive",
        # GOVERNMENT
        "senate",
        "congress",
        "parliament",
        "secretary",
        "state",
        "department of defense",
        "dod",
        "pentagon",
        "secret service",
        "nato",
        "pentagon",
        "cia",
        "fbi",
        "government",
        "stimulus",
        "mandate",
        "ministry",
        "minister",
        "coalition",
        "authorities",
        # HEALTH
        "health",
        "pandemic",
        "spreading rapidly",
        "spreading across",
        "outbreak",
        "hot zone",
        "panic",
        "illness",
        "virus",
        "strain",
        "vaccine",
        "hospitals",
        "medical centers",
        "cdc",
        # IMPACT
        "major shift",
        "sea change",
        "major trend",
        "amping up",
        "once in a lifetime",
        "vows to",
        "catastrophy",
        "disaster",
        "destruction",
        "unprecedented",
        "declares",
        "displaced",
        "large scale",
        "urges response",
        "calls on",
        "world record",
        "world records",
        "kills",
        "dies",
        "dies at",
        "record",
        "historic",
        "faction",
        "existential",
        # INDUSTRY
        "automotive",
        "manufacturing",
        "microchip",
        "microprocessor",
        "processor",
        "travel",
        "flight",
        "airliner",
        # SCIENCE
        "science",
        "archaeologists",
        "biologists",
        "scientists",
        "habitable",
        "mission",
        "launches",
        "quantum",
        "once-in",
        "mechanical",
        "engineering",
        "interstellar",
        "discovers",
        "element",
        "uap",
        "ufo",
        "anomaly",
        "cern",
        "large hadron",
        "metaphysics",
        # TRADE
        "trade",
        "export",
        "import",
        "exports",
        "imports",
        "sanctions",
        "seize",
        "closing locations",
        "trade war",
        "impose tarrifs",
        "port",
        "union",
        "accept bid",
        "shortage",
        "braces",
        "tariffs",
        "global trade",
        "tarrif",
        "manufacturing",
        "supply chain",
        "tsmc",
        "shippers",
        "shipping",
        "route",
        "distribution",
        "transportation",
        "workforce",
        "forecast",
        "free trade",
        "restrictions",
        # TECHNOLOGY
        "technology",
        "innovation",
        "artifical intelligence",
        "ai",
        "machine learning",
        "chatgpt",
        "openai",
        "anthropic",
        "claude 3.5",
        "decision intelligence",
        "data mapping",
        "autonomous",
        "bleeding edge",
        "next generation",
        "revolutionary",
        "visionary",
        "data",
        "engineering",
        "software",
        "saas",
        "robot",
        "robots",
        "robotics",
        "technology",
        "satellite",
        "comet",
        "space",
        "nasa",
        "scientists",
        "rocket",
        "launch",
        "spacecraft",
        "expedition",
        "pioneer",
        "astrophysics",
        "astronomy",
        "radiation",
        # PEOPLE
        "warren buffet",
        "musk",
        "bill gates",
        "tim cook",
        "bezos",
        "sam altman",
        "powell",
        "gensler",
        "zelenky",
        "zelenskiy",
        "zelinskyy",
        "putin",
        "kim jung",
        "xi",
        "merkel",
        "ken griffin",
        "macron",
        "trudeau",
        "brian may",
        # PEOPLE CATEGORIES
        "boomers",
        "gen-z",
        "gen z",
        "millenials",
        # POLICY
        "policy",
        "supreme court",
        "legistlation",
        "committee",
        "directive",
        "legislature",
        "laws",
        "precedent",
        # POLITICS
        "government",
        "political",
        "pundit",
        "election",
        "leader",
        "president",
        "state",
        "nation",
        "global",
        "regional",
        "worldwide",
        "presidency",
        "prime minister",
        "foreign minister",
        "syndicate",
        "speech",
        "incumbent",
        "constituent",
        "border",
        # POLITICS - US
        "biden",
        "harris",
        "trump",
        "vance",
        "democracy",
        "republican",
        "democrat",
        "liberal",
        "gop",
        "far-right",
        "far-left",
        # POLITICS - WORLD
        "geopolitical",
        "politics",
        "campaign",
        "world leaders",
        "peace",
        "international relations",
        "diplomacy",
        "historic",
        "diplomatic",
        "accord",
        "international waters",
        "international airspace",
        "prince",
        "king",
        "queen",
        "princess",
        # REGULATION
        "outlaw",
        "censor",
        "censored",
        "censorship",
        "regulation",
        # REGIONAL
        "hemisphere",
        "united states",
        "united kingdom",
        "africa",
        "israel",
        "gaza",
        "lebanon",
        "iran",
        "turkey",
        "eu",
        "europe",
        "north korea",
        "saudi",
        "asia",
        "middle east",
        "russia",
        "ukraine",
        "china",
        "india",
        "taiwan",
        "south america",
        "mexico",
        "north korea",
        # UNREST
        "revolution",
        "protest",
        "protestors",
        "crisis",
        "turmoil",
        "looting",
        # WAR & CONFLICT
        "conflict",
        "war",
        "war against",
        "war on",
        "battleground",
        "weapons",
        "weapons material",
        "intelligence agencies",
        "intelligence agency",
        "raid",
        "radical",
        "revolt",
        "caliphate",
        "insurgent",
        "fugitive",
        "intercepts",
        "deploys",
        "captured",
        "destablizing",
        "tensions",
        "millitary action",
        "independence",
        "projectiles",
        "elliminate",
        "terrorist",
        "faction",
        "soldiers",
        "troops",
        "drills",
        "front line",
        "warplane",
        "warship",
        "shelling",
        "bombing",
        "air attack",
        "expel",
        "condemns",
        "peacekeepers",
        "pressure",
        "asylum",
        "migrant",
        "migratory",
        "attack",
        "attacks",
        "deadly",
        "military",
        "army",
        "siege",
        "embezzle",
        "embezzling",
        "coup",
        "combat",
        "fighting",
        "infighting",
        "hostage",
        "negotiate",
        "militia",
        "anti-missile",
        "relations",
        "assassination",
        "war crime",
        "genocide",
    ]

    text = f"{title} {content}".lower()
    return sum(1 for keyword in priority_keywords if keyword in text)

tag_bank = {
    # business
    "Business": [
        "saas",
        "llc",
        "business",
        "enterprise",
        "corporate",
        "executive",
        "executives",
        "jobs",
        "layoffs",
        "quarter",
        "institution",
        "institutional",
        "delaware",
        "offshore",
        "show profits",
        "anti-trust",
        "antitrust",
        "workers",
        "hires",
        "fires",
        "employees",
        "market",
        "advertising",
        "advertisement",
        "ads",
        "return-to-office",
        "wfh",
        "remote policy",
        "office",
        "offices",
    ],
    "Startups": [
        "startup",
        "startups",
        "start-up",
        "start-ups",
        "accelerators",
        "incubator",
        "funding round",
        "venture capital",
        "vc-backed",
        "private equity",
        "seed round",
        "series-a",
        "angel investors",
    ],
    "Big Tech": [
        "meta",
        "amazon",
        "apple",
        "netflix",
        "google",
        "alphabet",
        "microsoft",
        "nvidia",
        "tesla",
        "spacex",
        "musk",
        "altman",
        "tim cook",
        "bezos",
        "pichai",
        "alex karp",
        "jensen huang",
        "lisa su",
        "mark zuckerberg",
        "bill gates",
        "greg peters",
        "ted sarandos",
        "SpaceX",
        "big tech",
        "anthropic",
        "ibm",
        "dell",
        "palentir",
        "openai",
        "mag7",
        "magnificent 7",
        "magnificent-7",
        "mag-7",
        "magnificent seven",
    ],
    "Layoffs": [
        "layoffs",
        "lay-offs",
        "laid off",
        "laid-off",
        "firing",
        "lets go",
        "employees",
        "boss",
        "laying off",
    ],
    # data, technology
    "AI": [
        "ai",
        "AI",
        "a.i.",
        "A.I.",
        "artificial intelligence",
        "generative",
        "gpu",
        "genai",
        "tsmc",
        "machine learning",
        "algorithms",
        "matrix operations",
        "parellel processing",
        "pdn",
        "power delivery network",
        "neural network",
        "deep learning",
        "chatgpt",
        "openai",
        "anthropic",
        "claude 3.5",
        "ollama",
    ],
    "Cyber Security": [
        "cybersecurity",
        "hacker",
        "information security",
        "infosec",
        "cyber criminal",
        "hacking",
        "cyber crime",
        "backdoor",
        "zero day",
        "zeroday",
        "bug bounty",
        "black hat",
        "red hat",
        "white hat",
        "cyber attack",
        "data breach",
        "hack",
        "cyber",
        "data leak",
        "hackers",
        "vulnerability",
    ],
    "Data": [
        "data",
        "metadata",
        "behavior",
        "analysis",
        "deviation",
        "etl",
        "database",
        "metric",
        "metrics",
        "breach",
        "hack",
        "cyber",
        "information",
        "infographic",
        "trend",
        "average",
        "input",
        "study",
        "math",
        "mathematics",
    ],
    "Decision Intelligence": [
        "decision intelligence",
        "stanford protege",
        "protégé",
        "ontology",
        "data mapping",
        "metric",
        "metrics",
        "kpi",
    ],
    "Technology": [
        "information technology",
        "technology",
        "tech",
        "computer",
        "innovation",
        "computers",
        "processor",
        "test flight",
        "processors",
        "microprocessors",
        "screen",
        "laptop",
        "tablet",
        "phone",
        "internet",
        "graphical",
        "ai",
        "artifical intelligence",
        "software",
        "engineer",
        "engineering",
        "engineers",
        "software developers",
        "computer program",
        "saas",
        "paas",
        "decision intelligence",
        "etl",
        "analytics",
        "network",
        "web",
        "iot",
        "internet of things",
        "automation",
        "automations",
        "reactor",
        "reactors",
        "cyber",
        "workflows",
    ],
    # economics & finance
    "Trade": [
        "trade",
        "trade war",
        "tarrif",
        "tarrifs",
        "import",
        "imports",
        "export",
        "exports",
        "embargo",
    ],
    "Supply Chain": [
        "headwinds",
        "refinery",
        "refineries",
        "inventory",
        "tsmc",
        "inventories",
        "factory",
        "mine",
        "mining",
        "taiwan",
        "lithium",
        "logistics",
        "supply network",
        "delivery",
        "transportation",
        "production chain",
        "manufacturing chain",
        "distributor",
        "standstill",
        "on strike",
        "union",
        "shipping",
        "supply chain",
        "shortage",
        "disrupt",
        "containers",
        "goods",
        "warehouses",
        "vessel",
        "distribution",
        "transportation",
        "port",
        "cargo",
    ],
    "Economy": [
        "economy",
        "economic",
        "gdp",
        "inflation",
        "recession",
        "fomc",
        "federal reserve",
        "central bank",
        "imf",
        "ecb",
        "fed",
        "rate cuts",
        "stimulus",
        "traders",
        "markets",
        "stock",
        "booming",
        "monetary",
        "banks",
        "fomc",
        "ecb",
        "powell",
        "jerome powell",
        "yellen",
        "janet yellen",
    ],
    "Finance": [
        "finance",
        "stock market",
        "stake",
        "investment",
        "banking",
        "investors",
        "black rock",
        "blackrock",
        "blacklake",
        "banks",
        "borrowers",
        "stocks",
        "shares",
        "quarter",
        "buyback",
        "earnings",
        "wall street",
        "equities",
        "etf",
        "bull",
        "bear",
        "pre-market",
        "after-market",
        "futures",
        "commodities",
        "options market",
        "loans",
        "institutional",
        "candlestick",
    ],
    "Commodoties": [
        "gold",
        "silver",
        "silicon",
        "germanium",
        "gallium",
        "arsenide",
        "idium phosphide",
        "wheat",
        "grain",
        "farms",
        "farmers",
        "farm land",
        "commodoties",
        "oil",
        "gasoline",
        "petroleum",
        "propane",
        "natural gas",
        "lithium",
        "brent crude",
        "copper",
    ],
    "Crypto": [
        "crypto",
        "cryptocurrency",
        "bitcoin",
        "dogecoin",
        "shiba inu",
        "xrp",
        "ripple",
        "ethereum",
        "cdbc",
        "satoshi",
        "defi",
    ],
    # energy
    "Nuclear": [
        "nuclear",
        "plutonium",
        "atomic power",
        "beta particle",
        "alpha particle",
        "fission",
        "thermonuclear",
        "atomic mass",
        "gamma radiation",
    ],
    "Energy": [
        "energy",
        "oil",
        "renewable energy",
        "fossil fuels",
        "solar",
        "watts",
        "wind",
        "petroleum",
        "gasoline",
        "nuclear power",
        "electric grid",
        "power grid",
        "blackout",
        "blackouts",
        "brownout",
        "brownouts",
        "without water",
        "without power",
        "without electricity",
        "electricity",
        "generator",
        "nuclear reactor",
    ],
    # environment, climate, and weather
    "Climate": [
        "climate change",
        "environment",
        "climate",
        "climatological",
        "climatology",
        "ocean",
        "climatologists",
        "sustainability",
        "nature",
        "natural disaster",
        "wildfires",
        "wildfire",
        "fema",
        "disaster",
        "ocean current",
        "ocean currents",
        "pollutant",
        "pollution",
        "atmosphere",
        "air quality",
        "smog",
        "ozone",
        "aroura",
        "borealis",
        "northern lights",
    ],
    "Weather": [
        "weather",
        "meteorological",
        "meteorologists",
        "storm",
        "gulf of mexico",
        "snowstorm",
        "low prssure system",
        "inclimate",
        "flooding",
        "typhoon",
        "landfall",
        "floods",
        "torrential",
        "hurricane",
        "drought",
        "heat",
        "temperature",
        "temperatures",
        "wind",
        "winds",
        "hail",
        "tornado",
        "monsoon",
        "el niño",
        "el niñna",
    ],
    # government, politics, and regulation
    "Regulation": [
        "government restriction",
        "taxes",
        "tax",
        "monopoly",
        "Five Eyes",
        "five eyes",
        "watchdog",
        "bans",
        "fines",
        "anti-trust",
        "antitrust",
        "committee",
        "directive",
        "tax",
        "taxes",
        "capital gains",
        "ftc",
        "supreme court",
        "legislature",
        "law",
        "regulation",
    ],
    "Politics": [
        "politics",
        "election",
        "political",
        "government",
        "policy",
        "ballot",
        "president",
        "elected",
        "vote",
        "leader",
        "congress",
        "senate",
        "stimulus",
        "ministry",
        "minister",
        "monarchy",
        "king",
        "queen",
        "princess",
        "prince",
        "ending ties",
        "democracy",
        "communist",
        "communism",
        "communists",
        "abortion",
        "deportation",
        "border",
        "policy",
        "immigration",
        "presidential",
        "coalition",
        "obama",
        "obamas",
        "clinton",
        "trump",
        "harris",
        "biden",
        "vance",
        "walz",
        "kennedy",
        "pundit",
        "mcconnell",
    ],
    "Geopolitics": [
        "geopolitics",
        "nato",
        "international relations",
        "diplomacy",
        "world leaders",
        "diplomat",
        "middle east",
        "israel",
        "russia",
        "ukraine",
        "china",
        "korea",
        "taiwan",
    ],
    # health
    "Health": [
        "health",
        "healthcare",
        "medical",
        "pandemic",
        "virus",
        "world health",
        "vaccine",
        "hospitals",
        "doctors",
        "cdc",
        "spreading rapidly",
        "drugs",
        "drug",
        "weight loss",
        "patients",
        "drug trial",
        "addiction",
    ],
    # industry
    "Automotive": [
        "automotive",
        "cars",
        "car dealer",
        "automotive manufacturor",
        "automotive manufacturors",
        "carmaker",
        "auto sector",
        "automaker",
        "automotive manufacturing",
        "used vehicles",
        "used vehicle",
        "vehicle",
        "vehicles",
        "roads",
        "roadway",
        "roadways",
        "motorcar",
        "motorcycle",
    ],
    "Banking": [
        "bank",
        "banks",
        "banking",
        "loan",
        "loans",
        "interest",
        "debt",
        "lending",
        "deposit",
        "capital",
        "bridging loan",
        "collateral",
        " deficit",
        "moneylending",
    ],
    "Housing": [
        "houses",
        "homes",
        "mortgage",
        "mortgages",
        "property",
        "home loan",
        "heloc",
        "housing",
        "home loans",
        "bonds",
        "lending",
        "deed",
        "remortgage",
        "home equity",
    ],
    "Communications": [
        "radio",
        "cellular",
        "fiber",
        "telecommunications",
        "media",
        "transmissions",
        "broadcasting",
        "correspondence",
        "telecom",
        "isp",
        "internet",
        "cable",
        "ftc",
    ],
    "Microchips": [
        "microchips",
        "AI chips",
        "chips",
        "chip stocks",
        "cpu",
        "gpu",
        "tpu",
        "fpga",
        "processor",
        "microprocessors",
        "qualcomm",
        "graphcore",
        "groq",
        "mediatek",
        "amd",
        "nvidia",
        "tenstorrent",
        "hardware acceleration components",
        "intel",
    ],
    # infrastructure
    "Infrastructure": [
        "infrastructure",
        "roads",
        "roadways",
        "bridge",
        "bridges",
        "tunnel",
        "tunnels",
        "building",
        "buildings",
        "park",
        "parks",
        "public space",
        "subway",
        "transit",
        "train",
        "trains",
        "locomotive",
        "highway",
        "highways",
        "streets",
        "facilities",
        "facility",
        "city",
        "cities",
        "town",
        "towns",
        "water supply",
        "electric grid",
        "power grid",
        "without water",
        "metropolis",
        "capitol",
        "stadium",
        "crowded",
    ],
    # regional
    "Africa": [
        "africa",
        "african nation",
        "sudan",
        "sudanese",
        "sahara",
        "south africa",
        "uganda",
        "tanzania",
        "namibia",
        "zimbabwe",
        "algeria",
        "botswana",
        "niger",
        "guinea",
    ],
    "APAC": [
        "apac",
        "china",
        "taiwain",
        "india",
        "korea",
        "nepal",
        "philippine",
        "philippines",
        "australia",
        "new zealand",
        "nz",
        "NZ",
    ],
    "Canada": ["canada", "canadian", "british columbia", "trudeau"],
    "EMEA": [
        "europe",
        "european",
        "eu",
        "euro",
        "eurozone",
        "emea",
        "pan-emea",
        "pan emea",
        "panemea",
        "nato",
        "UN",
        "United Nations",
        "ecb",
        "spain",
        "barcelona",
        "portugal",
        "france",
        "italy",
        "israel",
        "isreali",
        "iran",
        "iranian",
        "iraq",
        "qatar",
        "yemen",
        "gaza",
        "palestine",
        "palestinian",
        "germany",
        "switzerland",
        "scicily",
        "monaco",
        "turkey",
        "poland",
        "czech republic",
        "slovakia",
        "greece",
        "greek",
        "romania",
        "albania",
        "bulgaria",
        "latvia",
        "norway",
        "sweden",
        "finland",
        "hungary",
        "croatia",
        "moldova",
        "macedonia",
        "denmark",
        "amsterdam" "paris",
        "berlin",
        "munich",
        "rome",
    ],
    "Central America": [
        "mexico",
        "mexican",
        "guatemala",
        "belize",
        "el salvador",
        "honduras",
        "panama",
        "buenos aires",
        "costa rica",
        "nicaragua",
        "puerto rico",
        "cuba",
        "barbados",
        "st. lucia",
    ],
    "South America": [
        "south america",
        "south american",
        "latino",
        "brazil",
        "argentina",
        "chile",
        "peru",
        "columbia",
        "ecuador",
        "venezuala",
        "guyana",
        "paraguay",
        "uraguay",
    ],
    "Russia": [
        "russia",
        "kremlin",
        "moscow",
        "putin",
        "tsar",
        "ruissian",
        "russians",
        "ussr",
    ],
    "Ukraine": ["ukraine", "ukrainian", "zelensky", "zelenkey", "zelenskyy"],
    "United States": [
        "united states",
        "u.s.",
        "u.s.a.",
        "usa",
        "east coast",
        "west coast",
        "washington",
        "new york",
        "los angeles",
        "san franciso",
        "US House",
        "senate",
        "capitol hill",
        "fbi",
        "cia",
        "oval office",
        "biden",
        "harris",
        "trump",
        "vance",
        "federal reserve",
        "federal",
    ],
    "United Kingdom": [
        "united kingdom",
        "uk",
        "UK",
        "U.K.",
        "brexit",
        "british",
        "britain",
        "london",
        "scottland",
        "wales",
    ],
    # science
    "Space": [
        "nasa",
        "space station",
        "satellite",
        "rocket",
        "planet",
        "planetary",
        "cosmos",
        "universe",
        "constellation",
        "NASA",
        "moon",
        "expedition",
        "launchpad",
        "astronaut",
        "cosmonaut",
        "light year",
        "orbit",
        "flare",
        "sun",
        "galaxy",
        "meteor",
        "comet",
        "asteroid",
        "gravitational",
    ],
    # unrest
    "Conflict": [
        "at war",
        "in war",
        "war",
        "military",
        "troops",
        "army",
        "navy",
        "air force",
        "terrorist",
        "strikes",
        "strike on",
        "ballistic",
        "armed conflict",
        "seige",
        "soldiers",
        "rebellion",
        "siege",
        "hostage",
        "militia",
        "NATO",
        "international waters",
        "bomb threat",
        "bomb",
        "bombs",
        "bomber",
        "raid",
        "refugee",
        "strike",
        "prisoner",
        "plot",
        "bombers",
        "bullets",
        "gunman",
        "gunmen",
        "disputed territory",
        "international airspace",
        "attack",
        "hospitalized",
        "antisemitic",
        "tensions",
        "border",
        "batallion",
        "front line",
    ],
    "Disaster": [
        "disaster",
        "catastrophy",
        "left dead",
        "catastrophic",
        "killed or missing",
        "destruction",
        "evacuation",
        "imminent risk",
        "famine",
    ],
    "Espionage": [
        "espionage",
        "double agent",
        "intelligence agency",
        "spy",
        "surveilance",
        "infiltration",
        "infiltrated",
        "secret service",
        "intelligence",
        "cia",
        "sleuthing",
        "assassination",
        "assassin",
        "plot to kill",
        "plot to",
    ],
    "Misinformation": [
        "disinformation",
        "misinformation",
        "red herring",
        "gossip",
        "fiction",
        "deception",
        "misleading",
        "hype",
        "lie",
        "rumour",
        "deception",
        "propoganda",
        "china",
        "russia",
    ],
    "SaaS": [
        "enterprise software",
        "software as a service",
        "software-as-a-service",
        "saas",
    ],
}

# Normalize the tag_bank keywords to lowercase
tag_bank_lower = {
    tag: [kw.lower() for kw in keywords] for tag, keywords in tag_bank.items()
}

# Precompile patterns for tag bank
tag_patterns = {}
for tag, keywords in tag_bank_lower.items():
    patterns = [re.compile(r"\b" + re.escape(kw) + r"\b") for kw in keywords]
    tag_patterns[tag] = patterns

countries = {country.name.lower() for country in pycountry.countries}
for country in pycountry.countries:
    if hasattr(country, "official_name"):
        countries.add(country.official_name.lower())
    if hasattr(country, "common_name"):
        countries.add(country.common_name.lower())

# Build a list of tuples with country names and compiled patterns
country_patterns = [
    (country, re.compile(r"\b" + re.escape(country) + r"\b")) for country in countries
]

meta_tag_stopwords = set(stopwords.words("english")).union({"sponsor"})


def aggregate_headlines_and_generate_tags(clustered_articles):
    logging.info("Aggregating headlines and generating meta tags...")
    aggregated_headlines = []
    stop_words = set(stopwords.words('english'))

    # Define get_source_name function here
    def get_source_name(url):
        ext = tldextract.extract(url)
        domain = ext.domain
        # Handle common cases for better names
        domain_mappings = {
            "nytimes": "New York Times",
            "bbc": "BBC",
            "cnn": "CNN",
            "theguardian": "The Guardian",
            "wsj": "WSJ",
            "ft": "Financial Times",
            "latimes": "LA Times",
            "npr": "NPR",
            "apnews": "Associated Press",
            "reuters": "Reuters",
            "forbes": "Forbes",
            "bloomberg": "Bloomberg",
            "coindesk": "CoinDesk",
            "businessinsider": "Business Insider",
            "techcrunch": "TechCrunch",
            "cnbc": "CNBC",
            "nypost": "NY Post",
            "thehill": "The Hill",
            "ndtv": "Adani Group",
            "marketwatch": "MarketWatch",
            "investopedia": "Investopedia",
            "seekingalpha": "Seeking Alpha",
            "firstpost": "Firstpost",
            "Lemonde": "Le Monde",
            "dw": "Deutsche Welle",
            "feedburner": "FeedBurner",
            "feedx": "X",
            "co": "CO",
            "msn": "MSN",
            "qz": "Quartz",
            "nbcnews": "NBC News",
            "arstechnica": "Ars Technica",
            "cbsnews": "CBS News",
            "abcnews": "ABC News",
            "huffpost": "Huffington Post",
            "axios": "Axios",
            "politico": "Politico",
            "washingtonpost": "Washington Post",
            "firstpost": "Firstpost",
            "go": "ABC News",
            "theregister": "The Register",
            "aljazeera": "Al Jazeera",
            "krebsonsecurity": "Krebs On Security",
            "sans": "SANS Internet Storm Center",
            #blacklisted outlets
            "dnyuz": "!blacklisted outlet!",
            # Add more mappings as needed
        }

        source_name = domain_mappings.get(domain, domain.capitalize())
        return source_name


    for cluster_idx, cluster in clustered_articles.items():
        article_count = len(cluster)
        if article_count < 3:
            logging.info(
                f"Skipping aggregated headline with {article_count} articles: {cluster[0]['title']}"
            )
            continue

        titles = [article["title"] for article in cluster if article["title"]]
        if not titles:
            logging.info(f"No titles found in cluster {cluster_idx}, skipping.")
            continue

        # Combine titles into one text
        combined_titles = ' '.join(titles)

        # Generate a coherent headline using the summarizer
        aggregated_headline = generate_headline(combined_titles)

        if not is_valid_headline(aggregated_headline):
            logging.info(f"Skipping invalid headline: {aggregated_headline}")
            continue

        combined_text = aggregated_headline
        combined_text_lower = combined_text.lower()

        meta_tags = []
        tag_counter = defaultdict(int)

        # Use precompiled patterns for tag bank matching
        for tag, patterns in tag_patterns.items():
            for pattern in patterns:
                if pattern.search(combined_text_lower):
                    tag_counter[tag] += 1  # Increment by 1 to avoid overcounting

        # Use precompiled patterns for country matching
        for country_name, pattern in country_patterns:
            if pattern.search(combined_text_lower):
                tag_counter[country_name.title()] += 1

        most_common_tags = sorted(
            tag_counter.items(), key=lambda x: x[1], reverse=True
        )[:5]
        for tag, _ in most_common_tags:
            if tag.lower() not in meta_tag_stopwords and len(tag) > 1:
                meta_tags.append(f"#{tag.replace(' ', '')}")

        meta_tags = list(dict.fromkeys(meta_tags))[:5]

        publish_dates = [
            article.get("publish_datetime")
            for article in cluster
            if article.get("publish_datetime")
        ]
        if publish_dates:
            latest_date = max(publish_dates)
            latest_article = max(
                cluster, key=lambda x: x.get("publish_datetime", date.min)
            )
            latest_publish_date = latest_article.get("publish_datetime")
            try:
                if isinstance(latest_article.get("publish_date"), str):
                    latest_datetime = date_parser.parse(
                        latest_article.get("publish_date")
                    ).astimezone(ZoneInfo("America/Chicago"))
                else:
                    latest_datetime = datetime.combine(
                        latest_publish_date, datetime.min.time()
                    ).astimezone(ZoneInfo("America/Chicago"))
            except Exception as e:
                logging.error(
                    f"Error processing publish date for cluster '{aggregated_headline}': {e}"
                )
                latest_datetime = None
            time_display = (
                latest_datetime.strftime("%-I:%M%p") if latest_datetime else ""
            )
        else:
            time_display = ""
            latest_datetime = None  # Ensure latest_datetime is defined

        # Use the source_links block to create hyperlinked source names
        source_links = []
        seen_sources = set()
        for article in cluster:
            article_url = article.get("url", "#")
            source_name = get_source_name(article_url)
            if source_name not in seen_sources:
                seen_sources.add(source_name)
                # Create a hyperlink for the source name
                source_link = f'<a href="{article_url}">{source_name}</a>'
                source_links.append(source_link)
            if len(source_links) == 3:
                break

        sources_str = "; ".join(source_links)

        if latest_datetime:
            day_date = latest_datetime.strftime("%A, %B %d, %Y")
        else:
            if latest_publish_date:
                day_date = latest_publish_date.strftime("%A, %B %d, %Y")
            else:
                day_date = "Unknown Day, Unknown Date"

        # Calculate priority score using the aggregated headline
        priority_score = prioritize_headline(aggregated_headline, combined_text)

        # Update the headline in the aggregated_headlines
        aggregated_headlines.append(
            {
                "headline": aggregated_headline,
                "meta_tags": meta_tags,
                "articles": cluster,
                "time": time_display,
                "sources_str": sources_str,  # Store the hyperlinked source names
                "publish_datetime": latest_datetime if latest_datetime else None,
                "day_date": day_date,
                "headline_count": article_count,
                "priority_score": priority_score,
            }
        )

    logging.info(f"Aggregated {len(aggregated_headlines)} headlines")
    return aggregated_headlines


def generate_headline(text):
    try:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        if not hasattr(generate_headline, "model"):
            generate_headline.tokenizer = AutoTokenizer.from_pretrained("facebook/bart-large-cnn")
            generate_headline.model = AutoModelForSeq2SeqLM.from_pretrained("facebook/bart-large-cnn").to(device)
        
        input_ids = generate_headline.tokenizer.encode(
            text,
            return_tensors="pt",
            max_length=512,
            truncation=True
        ).to(device)
        
        outputs = generate_headline.model.generate(
            input_ids,
            max_length=30,
            min_length=10,
            length_penalty=1.0,
            num_beams=4,
            early_stopping=True,
            no_repeat_ngram_size=3
        )
        headline = generate_headline.tokenizer.decode(outputs[0], skip_special_tokens=True)
        headline = fix_text(headline)
        headline = headline.strip().rstrip('.')
        return headline
    except Exception as e:
        logging.error(f"Error generating headline: {e}")
        return 'Untitled Headline'


def group_headlines(aggregated_headlines: List[Dict]) -> Dict:
    """
    Groups aggregated headlines by day of the week and date.

    Parameters:
    - aggregated_headlines (List[Dict]): The list of aggregated headlines.

    Returns:
    - Dict: A dictionary with keys as "Day, Date" and values as lists of headlines.
    """
    logging.info("Grouping headlines by day of the week and date...")
    grouped_headlines = defaultdict(list)

    for item in aggregated_headlines:
        if "publish_datetime" in item and item["publish_datetime"]:
            day_of_week = item["publish_datetime"].strftime("%A")
            date_str = item["publish_datetime"].strftime("%B %d, %Y")
        else:
            # Fallback in case 'publish_datetime' is missing or None
            if "day_date" in item and ", " in item["day_date"]:
                day_of_week = item["day_date"].split(", ")[0]
                date_str = item["day_date"].split(", ")[1]
            else:
                day_of_week = "Unknown Day"
                date_str = "Unknown Date"
        key = f"{day_of_week}, {date_str}"
        grouped_headlines[key].append(item)

    # Sort headlines within each day by headline_count and priority_score
    for day, headlines in grouped_headlines.items():
        grouped_headlines[day] = sorted(
            headlines,
            key=lambda x: (x.get("headline_count", 0), x.get("priority_score", 0)),
            reverse=True,
        )

    logging.info(f"Grouped headlines into {len(grouped_headlines)} days")
    return grouped_headlines


# Define the keyword banks for sentiment, impact, and action
# SENTIMENT_KEYWORDS = {
#     'positive': ['improvement', 'growth', 'success', 'benefit', 'gain', 'achievement', 'progress', 'win', 'increase'],
#     'negative': ['disaster', 'failure', 'loss', 'risk', 'collapse', 'destruction', 'downturn', 'catastrophy', 'trouble', 'issue'],
# }

IMPACT_KEYWORDS = {
    "high": [
        "major",
        "drugs to combat",
        "to develop",
        "gains momentum",
        "chain reaction",
        "drug to combat",
        "package for",
        "affects businesses",
        "rate",
        "rates",
        "prices",
        "strike",
        "strikes",
        "refinery",
        "refineries",
        "affects",
        "affecting",
        "push to",
        "microchips",
        "stocks",
        "manufacturing",
        "jobs",
        "inflation",
        "almanac predicts",
        "votes for",
        "fuels",
        "votes against",
        "resign",
        "finally moves",
        "off shelves",
        "wins",
        "victory",
        "fed",
        "cuts",
        "rate",
        "interest",
        "fed cuts",
        "loses",
        "attacks",
        "white house",
        "powell",
        "trump",
        "soars",
        "sinks",
        "plumets",
        "canceled loans",
        "million",
        "million",
        "billion",
        "invests",
        "investigating",
        "public",
        "workers",
        "administration",
        "rates",
        "new rule",
        "new law",
        "legislation",
        "fomc",
        "nuclear",
        "implement",
        "banks",
        "turns to",
        "will close",
        "bankruptcy",
        "nuclear power",
        "nuclear reactor",
        "low growth",
        "high debt",
        "significant",
        "xi says",
        "trump says",
        "harris says",
        "gensler",
        "buffett",
        "powell",
        "swing state",
        "swing states",
        "global",
        "widespread",
        "leaves company",
        "brink of",
        "revolutionary",
        "impeachement",
        "warning",
        "major trend",
        "disruptive",
        "launches",
        "rocket",
        "spacex",
        "nasa",
        "moon",
        "raise rates",
        "cut rates",
        "rate cut",
        "gasoline tanker",
        "frontline",
        "climate",
        "deserting",
        "downtsream",
        "github",
        "source code",
        "tanker",
        "critical",
        "rapidly",
        "spreading rapidly",
        "never before seen",
        "leaves company to",
        "fuel tanker",
        "shipping",
        "supply chain",
        "tarrif",
        "embargo",
        "exports",
        "imports",
        "leak",
        "leaking",
        "breach",
        "hack",
        "plans to",
        "strike",
        "union",
        "standstill",
        "frozen",
        "diplomats",
        "diplomat",
        "deteriorating",
        "improving",
        "deadlock",
        "shut down",
        "implications",
        "expands offensive",
        "accidentally",
        "what that could mean",
        "erupt",
        "erupts",
        "launches",
        "launching",
        "ecplore the",
        "group of migrants",
        "judge blocks",
        "hit by",
        "seizes",
        "following",
        "shocked",
        "appoints",
        "victory plan",
        "surprises",
    ],
    "low": [
        "minor",
        "small",
        "insignificant",
        "local",
        "limited",
        "contained",
        "manageable",
        "narrow",
        "fulfilling wish",
        "wish",
        "wishes",
        "says",
        "what went",
    ],
}

ACTION_KEYWORDS = {
    "high_action": [
        "urgent",
        "warning",
        "important",
        "urge people",
        "is coming",
        "immediate",
        "necessary",
        "take action",
        "act now",
        "call to action",
        "debate",
        "vote",
        "ballot",
        "election",
        "evacuate",
        "evacuation",
        "use caution",
        "awareness",
        "refuse",
        "voter",
        "voters",
        "stock",
        "earnings",
        "investors",
        "imminent",
        "markets",
        "worry",
        "impact",
        "landfall",
        "brewing",
        "correlation",
        "warning",
        "sirens",
        "siren",
        "wildfire",
        "spreading",
        "contagious",
        "beware",
        "beneficial for",
        "dangerous",
        "affect",
        "recall",
        "alert",
        "forecasts",
        "downstream",
        "swing state",
        "swing states",
    ],
    "low_action": [
        "optional",
        "not necessary",
        "delayed",
        "wait",
        "minimal",
        "preorder",
        "tattoos",
        "paused",
        "halted",
        "standstill",
        "neutral",
        "tepid",
        "claims",
        "consider",
        "evaluate",
        "review",
        "rescued",
        "ignore",
        "bland",
    ],
}

# Compile patterns for impact high keywords
impact_patterns_high = [
    re.compile(r"\b" + re.escape(kw.lower()) + r"\b") for kw in IMPACT_KEYWORDS["high"]
]

# Compile patterns for impact low keywords
impact_patterns_low = [
    re.compile(r"\b" + re.escape(kw.lower()) + r"\b") for kw in IMPACT_KEYWORDS["low"]
]

# Compile patterns for action high keywords
action_patterns_high = [
    re.compile(r"\b" + re.escape(kw.lower()) + r"\b")
    for kw in ACTION_KEYWORDS["high_action"]
]

# Compile patterns for action low keywords
action_patterns_low = [
    re.compile(r"\b" + re.escape(kw.lower()) + r"\b")
    for kw in ACTION_KEYWORDS["low_action"]
]

def calculate_scores_for_headline(headline_text):
    # Use VADER for sentiment analysis
    sentiment = sentiment_analyzer.polarity_scores(headline_text)
    compound_score = sentiment[
        "compound"
    ]  # VADER returns a compound score between -1 and 1

    # Scale the compound score to a range from -5 to 5
    sentiment_score = compound_score * 5

    # Initialize impact and action scores
    impact_score = 0
    action_score = 0

    # Convert headline to lowercase for case-insensitive matching
    headline_lower = headline_text.lower()

    # Match impact high keywords using precompiled patterns
    for pattern in impact_patterns_high:
        if pattern.search(headline_lower):
            impact_score += 1  # Increment by 1 per keyword found

    # Match impact low keywords using precompiled patterns
    for pattern in impact_patterns_low:
        if pattern.search(headline_lower):
            impact_score -= 1  # Decrement by 1 per keyword found

    # Normalize impact score to -5 to 5 range
    impact_score = max(min(impact_score, 5), -5)

    # Match action high keywords using precompiled patterns
    for pattern in action_patterns_high:
        if pattern.search(headline_lower):
            action_score += 1  # Increment by 1 per keyword found

    # Match action low keywords using precompiled patterns
    for pattern in action_patterns_low:
        if pattern.search(headline_lower):
            action_score -= 1  # Decrement by 1 per keyword found

    # Normalize action score to -5 to 5 range
    action_score = max(min(action_score, 5), -5)

    return sentiment_score, impact_score, action_score

    # Commented out keyword matching logic for reference
    """
    # Previous keyword matching code
    # sentiment_score = 0
    # doc = nlp(headline_text)
    # for token in doc:
    #     if token.text.lower() in SENTIMENT_KEYWORDS['positive']:
    #         sentiment_score += 1
    #     elif token.text.lower() in SENTIMENT_KEYWORDS['negative']:
    #         sentiment_score -= 1
    # sentiment_score = max(min(sentiment_score, 5), -5)
    """


def generate_summaries(text_list: List[str], batch_size: int = 8) -> List[str]:
    try:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        if not hasattr(generate_summaries, "model"):
            generate_summaries.tokenizer = AutoTokenizer.from_pretrained("t5-small")
            generate_summaries.model = AutoModelForSeq2SeqLM.from_pretrained("t5-small").to(device)
        
        summaries = []
        for i in range(0, len(text_list), batch_size):
            batch_texts = text_list[i:i+batch_size]
            inputs = generate_summaries.tokenizer(
                ["summarize: " + text for text in batch_texts],
                return_tensors="pt",
                max_length=512,
                truncation=True,
                padding=True
            ).to(device)
            
            outputs = generate_summaries.model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_length=80,  
                min_length=40,
                length_penalty=1.5,
                num_beams=4,
                early_stopping=True,
                no_repeat_ngram_size=3
            )
            
            batch_summaries = [
                generate_summaries.tokenizer.decode(output, skip_special_tokens=True)
                for output in outputs
            ]
            
            # Post-process summaries
            batch_summaries = [fix_text(summary).strip() for summary in batch_summaries]
            summaries.extend(batch_summaries)
        
        return summaries
    
    except Exception as e:
        logging.error(f"Error generating summaries: {e}")
        return ['' for _ in text_list]

async def generate_summaries_async(text_list: List[str], batch_size: int = 8, timeout: int = 60) -> List[str]:
    try:
        summaries = await asyncio.wait_for(
            asyncio.to_thread(generate_summaries, text_list, batch_size),
            timeout=timeout
        )
        return summaries
    except asyncio.TimeoutError:
        logging.error("Summarization timed out.")
        return ['Summary not available.' for _ in text_list]


def fix_text(text: str) -> str:
    # Fix contractions and capitalization
    text = contractions.fix(text)
    text = re.sub(r'\s+([?.!,"])', r'\1', text)
    sentences = nltk.sent_tokenize(text)
    sentences = [s.capitalize() for s in sentences]
    # Capitalize proper nouns
    text = capitalize_proper_nouns(' '.join(sentences))
    return text.strip()

    
def preprocess_article_content(content: str, max_length: int = 10000) -> str:
    # Remove HTML tags
    clean_text = re.sub('<.*?>', '', content)
    # Remove URLs
    clean_text = re.sub(r'http\S+', '', clean_text)
    # Normalize whitespace
    clean_text = ' '.join(clean_text.split())
    # Truncate to maximum length
    if len(clean_text) > max_length:
        clean_text = clean_text[:max_length] + "..."
    return clean_text


#def parse_feed_content(feed_content):
#    articles = []
#    for entry in feed_content.entries:
#        article = {
#            'title': entry.get('title', ''),
#            'url': entry.get('link', ''),
#            'publish_date': entry.get('published', ''),
#            # Fetch the full content if available
#            'content': entry.get('content', [{'value': ''}])[0]['value'] if 'content' in entry else entry.get('summary', ''),
#            # ... other fields ...
#        }
#        articles.append(article)
#    return articles


async def prepare_email_content(grouped_headlines: Dict) -> str:
    logging.info("Preparing HTML email content...")
    email_content = ""

    def divider():
        return "<hr style='border:1px solid #ccc;'>\n"

    def clean_headline(headline_text):
        if " - " in headline_text:
            headline_text = headline_text[: headline_text.rfind(" - ")]
        return headline_text

    current_day = datetime.now(ZoneInfo("America/Chicago")).strftime("%A")
    days_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    today_index = days_order.index(current_day) if current_day in days_order else 0
    ordered_days = days_order[today_index:] + days_order[:today_index]

    def parse_day_date(x):
        try:
            return datetime.strptime(x.split(", ")[1], "%B %d, %Y")
        except ValueError:
            try:
                date_without_year = datetime.strptime(x.split(", ")[1], "%B %d")
                # Assign current year
                date_with_year = date_without_year.replace(year=datetime.now().year)
                return date_with_year
            except ValueError:
                logging.error(
                    f"Unable to parse date for key '{x}'. Assigning default date."
                )
                return datetime.min

    try:
        sorted_keys = sorted(
            grouped_headlines.keys(), key=lambda x: parse_day_date(x), reverse=True
        )
    except Exception as e:
        logging.error(f"Error during sorting: {e}")
        sorted_keys = grouped_headlines.keys()

    if not sorted_keys:
        logging.error("No sorted keys found for headlines.")
    else:
        logging.info(f"Preparing content for {len(sorted_keys)} headline groups.")

    for key in sorted_keys:
        headlines = grouped_headlines[key]
        headline_count = len(headlines)
        
        if headline_count == 0:
            logging.warning(f"No headlines to display for key {key}")
            continue
        
        email_content += f"<h2>{key} ({headline_count} highlights)</h2>\n"
        email_content += divider()
        email_content += "<br>"
        
        # Collect texts and items for batch processing
        texts_to_summarize = []
        items_to_summarize = []

        for item in headlines:
            headline = clean_headline(item["headline"])
            meta_tags = " ".join(item["meta_tags"]) if item["meta_tags"] else ""
            article_count = len(item["articles"])
            sources_str = item["sources_str"] if item["sources_str"] else "N/A"
            
            # Collect and preprocess contents of the top 3 articles
            combined_content = ""
            top_articles = item["articles"][:3]
            for article in top_articles:
                content = article.get('preprocessed_content', '')
                if content:
                    clean_content = preprocess_article_content(content)
                    combined_content += ' ' + clean_content
            
            # Prepare for batch summarization
            if combined_content.strip():
                texts_to_summarize.append(combined_content)
                items_to_summarize.append({
                    "headline": headline,
                    "meta_tags": meta_tags,
                    "article_count": article_count,
                    "sources_str": sources_str
                })
            else:
                logging.warning(f"No content available for headline: {headline}")
                items_to_summarize.append({
                    "headline": headline,
                    "meta_tags": meta_tags,
                    "article_count": article_count,
                    "sources_str": sources_str,
                    "summary": "Summary not available."
                })
        
        # Generate summaries in batches asynchronously
        if texts_to_summarize:
            summaries = await generate_summaries_async(texts_to_summarize)
            for item, summary in zip(items_to_summarize, summaries):
                item["summary"] = summary

        # Build the email content with summaries
        for item in items_to_summarize:
            headline = item["headline"]
            summary = item.get('summary', 'Summary not available.')
            meta_tags = item["meta_tags"]
            article_count = item["article_count"]
            sources_str = item["sources_str"]

            # Calculate sentiment, impact, and action scores
            sentiment_score, impact_score, action_score = calculate_scores_for_headline(
                headline
            )
            
            # Build the email content
            email_content += f"<p>"
            email_content += f"<strong>{headline}</strong><br>"
            email_content += f"{summary}<br>"
            if meta_tags:
                email_content += f"{meta_tags}<br>"
            email_content += f"Related Articles: {sources_str} [{article_count}]<br>"
            email_content += f"Sentiment: {sentiment_score:.2f}, Impact: {impact_score}, Action: {action_score}"
            email_content += f"</p>"

    if not email_content.strip():
        logging.error("Email content is empty after processing all headlines.")

    logging.info("Email content prepared successfully")
    return email_content



def send_email(email_content):
    logging.info("Preparing to send email...")
    sender_email = "YOUREMAILHERE@EMAILDOTCOM"
    receiver_email = "YOUREMAILHERE@EMAILDOTCOM"
    password = os.environ.get("EMAIL_PASSWORD")

    if not password:
        logging.error(
            "Email password not found. Please set the EMAIL_PASSWORD environment variable."
        )
        return False

    try:
        validate_email(sender_email)
        validate_email(receiver_email)
    except EmailNotValidError as e:
        logging.error(f"Email validation error: {e}")
        return False

    message = MIMEMultipart("alternative")
    current_datetime = datetime.now(ZoneInfo("America/Chicago")).strftime(
        "%A, %B %d, %Y"
    )
    message["Subject"] = f"Meridian Insights // {current_datetime}"
    message["From"] = sender_email
    message["To"] = receiver_email

    part = MIMEText(email_content, "html")
    message.attach(part)

    logging.info("Sending email...")
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 465

        context = ssl.create_default_context()

        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        logging.info("Email sent successfully.")
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False


def main():
    initialize_resources()

    articles_content = process_feeds(rss_feeds)

    filtered_articles = filter_and_preprocess_articles(articles_content)

    clustered_articles = cluster_articles(filtered_articles)

    aggregated_headlines = aggregate_headlines_and_generate_tags(clustered_articles)

    grouped_headlines = group_headlines(aggregated_headlines)

    email_content = asyncio.run(prepare_email_content(grouped_headlines))

    email_sent = send_email(email_content)

    if email_sent:
        logging.info("Script execution completed successfully.")
    else:
        logging.error("Script execution completed with errors.")

if __name__ == "__main__":
    main()
