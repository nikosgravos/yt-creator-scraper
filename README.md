
# YouTube Channel Scraper with ViewStats

This repository contains two Python scripts that together allow you to discover YouTube channels in any niche and enrich them with public analytics from ViewStats:

* `youtube_scraper.py`: Scrapes YouTube channels using the YouTube Data API v3 based on search keywords and filters.
* `viewstats_scraper.py`: Uses Selenium to fetch additional analytics like views, revenue, and subscriber growth from [ViewStats.com](https://www.viewstats.com).

## Features

### YouTube Scraper (`youtube_scraper.py`)

* Search for YouTube channels using niche-specific keywords.
* Filter channels by:

  * Subscriber count range
  * Country code (optional)
* Prevents duplicates by checking usernames and URLs.
* Appends new search keywords to existing entries' niche field.
* Tracks:

  * API quota usage
  * Number of API calls
  * Skipped reasons (e.g., wrong country, subs out of range)

### ViewStats Scraper (`viewstats_scraper.py`)

* Enriches channel data with:

  * Views from the last 28 days
  * Subscribers gained in the last 28 days
  * Estimated revenue
  * Long vs short views breakdown
* Uses `selenium` and `webdriver-manager` to automate Chrome.
* Detects and skips unavailable or untracked channels.

---

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/nikosgravos/yt-creator-scraper.git
```

### 2. Install Dependencies

```txt
pandas
google-api-python-client
python-dotenv
selenium
webdriver-manager
```

### 3. Add YouTube API Key

Create a `.env` file in the project root directory and add your API key:

```env
YOUTUBE_API_KEY=your_youtube_api_key_here
```

You can obtain an API key from the [Google Developers Console](https://console.developers.google.com/).

---

## How to Use

### 1. Scrape YouTube Channels

Run:

```bash
python youtube_scraper.py
```

You'll be prompted to enter:

* A niche keyword (e.g., `fitness`, `gaming`, `finance`)
* Minimum and maximum subscriber count
* Country filter (2-letter country code like `US`, optional)
* Number of new channels to discover

The script will:

* Use the YouTube API to find and filter matching channels
* Save the results to a CSV database (`youtube_channels_database.csv`)
* Update existing entries with new niche keywords if needed

### 2. Enrich with ViewStats Data

Run:

```bash
python viewstats_scraper.py
```

This script will:

* Open Chrome using Selenium
* Navigate to each channel's ViewStats page (if available)
* Scrape views, subs, revenue, and content type breakdown
* Save the updated results back to `youtube_channels_database.csv`

> By default, the browser is visible. To run in headless mode, uncomment the `--headless` line in `viewstats_scraper.py`.

---

## Output

All channel data is stored in:

```
youtube_channels_database.csv
```

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

---

## Tips

* API quota usage is tracked and estimated before scraping starts.
* If a channel already exists, its niche will be updated rather than duplicated.
* ViewStats scraping includes retry logic and skips untrackable or broken pages.
* Delay and throttling are included to avoid bans during scraping.

---

## Warnings

* Ensure you comply with YouTube and ViewStats terms of service before using this tool.
* Avoid excessive automated requests to prevent IP bans or quota suspensions.
* Always use your own API key.

---

## Authors

GitHub: [@nikosgravos](https://github.com/nikosgravos)
[@VasilisVas1](https://github.com/VasilisVas1)
Feel free to open issues or suggest improvements!

---
