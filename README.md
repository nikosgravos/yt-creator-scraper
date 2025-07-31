# YouTube Channel Scraper and ViewStats Processor

## Overview

This project consists of two main scripts for YouTube channel research:

1. **YouTube Channel Scraper**: Searches for YouTube channels by niche/keyword and collects channel statistics using the YouTube API.
2. **ViewStats Processor**: Enhances the collected data by scraping additional metrics from ViewStats.com.

## Requirements

- Python 3.7+
- Google Cloud Platform account with YouTube Data API v3 enabled
- Required Python packages (install via `pip install -r requirements.txt`)

## Setup Instructions

1. **YouTube API Key**:
   - Create a project in Google Cloud Console
   - Enable the YouTube Data API v3
   - Create an API key
   - Save the key in a `.env` file as `YOUTUBE_API_KEY=your_api_key_here`

2. **Environment Setup**:
   ```
   pip install pandas python-dotenv google-api-python-client selenium webdriver-manager
   ```

## YouTube Channel Scraper Usage

### How It Works

1. The script searches YouTube for channels matching your specified niche/keyword
2. It collects:
   - Channel name and URL
   - Subscriber count
   - Total views
   - Video count
   - Country
   - Channel image URL
3. Results are saved to a CSV database (`youtube_channels_database.csv`)

### Running the Scraper

1. Execute the script: `python youtube_scraper.py`
2. When prompted, enter:
   - Your target niche/keyword (e.g., "fashion", "gaming")
   - Minimum and maximum subscriber count range
   - Optional country filter (2-letter country code)
   - Number of new creators to find
3. The script will display progress and save results

## ViewStats Processor Usage

### How It Works

1. The script checks the database for channels missing ViewStats data
2. For each channel, it:
   - Attempts to find the channel on ViewStats.com
   - Scrapes additional metrics:
     - Views in last 28 days
     - Subscribers gained in last 28 days
     - Estimated revenue
     - Long vs. short view percentages
3. Updates the database with the collected information

### Running the Processor

1. Execute the script: `python viewstats_processor.py`
2. Confirm you want to process missing ViewStats data
3. The script will automatically:
   - Launch a Chrome browser (visible by default)
   - Process each channel one by one
   - Save progress every 10 records
4. Results are saved back to the same CSV file

## Important Notes

- The YouTube API has quota limits (approx. 10,000 units/day)
- ViewStats scraping requires manual browser interaction if CAPTCHAs appear
- For large datasets, consider running the ViewStats processor in batches
- The database CSV will be created automatically on first run

## Output File

All data is saved to `youtube_channels_database.csv` with these columns:

- Basic YouTube data: Username, Subscribers, Total Views, etc.
- ViewStats data: 28-day metrics, revenue estimates, view types
- Channel URLs and search niches

## Troubleshooting

- If ViewStats scraping fails, try:
  - Running in non-headless mode (visible browser)
  - Adding manual delays if your internet is slow
  - Checking for CAPTCHAs and solving them manually
- For YouTube API issues:
  - Verify your API key is correct and has quota remaining
  - Check your Google Cloud project has the API enabled
