
# YouTube Channel Scraper with ViewStats

This repository includes two Python scripts that help you discover YouTube UGC (user-generated content) creators in any niche and enrich them with public analytics from ViewStats. Together, they enable rapid accumulation of niche-relevant CCs (content creators), complete with key metrics like subs, views, country, and estimated earnings. Ideal for building databases for marketing platforms, research tools, or SaaS apps, this system supports scalable UGC discovery and enrichment for use in creator outreach, influencer marketing, or audience analysis. Easily customizable for integration into your own workflows or applications.

* `youtube_scraper.py`: Scrapes YouTube channels using the YouTube Data API v3 based on search keywords and filters.
* `viewstats_scraper.py`: Uses Selenium to fetch additional analytics like views, revenue, and subscriber growth from [viewstats.com](https://www.viewstats.com).

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/nikosgravos/yt-creator-scraper.git
```

### 2. Install Dependencies

```
pip install pandas google-api-python-client python-dotenv selenium webdriver-manager
```

### 3. Add YouTube API Key

Create a `.env` file in the project root directory and add your API key:

```env
YOUTUBE_API_KEY=your_youtube_api_key_here
```

You can obtain an API key from the [Google Developers Console](https://console.developers.google.com/).

## How to Use

### 1. Scrape YouTube Channels

* Run `youtube_scraper.py`
* Follow the prompts on the console
* The script will save the results to a CSV database `youtube_channels_database.csv`

### 2. Enrich with ViewStats Data

* Run `python viewstats_scraper.py`
* This script will:
  * Open Chrome using Selenium
  * Navigate to each channel's ViewStats page (if available)
  * Scrape views, subs, revenue, and content type breakdown
  * Save the updated results back to `youtube_channels_database.csv`

## Output

All channel data is stored in: `youtube_channels_database.csv`

### Columns

* `Username`
* `Subscribers`
* `Total Views`
* `Video Count`
* `Avg Views Per Video`
* `Country`
* `Channel URL`
* `Search Niche`
* `Channel_Image_URL`
* `ViewStats_Profile_URL`
* `Views_Last_28_Days`
* `Subs_Last_28_Days`
* `Estimated_Rev_Last_28_Days`
* `Long_Views`
* `Short_Views`

## Important

* Ensure you comply with YouTube and ViewStats terms of service before using this tool.
* The YouTube Data API has usage quotas, each project has a daily limit of 10,000 units. The units you spend are estimated before running the script.
* Always use your own API key for accessing the YouTube API. Do not share or hardcode keys in public repositories. Secure them using environment variables or .env files.
* Avoid excessive automated requests, especially when scraping ViewStats, as this may lead to IP bans or temporary blocks.


## Authors

GitHub: [@nikosgravos](https://github.com/nikosgravos)
[@VasilisVas1](https://github.com/VasilisVas1)
Feel free to open issues or suggest improvements!
