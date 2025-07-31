import pandas as pd
import time
from googleapiclient.discovery import build
import re
from collections import Counter
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get API keys
API_KEY = os.getenv('YOUTUBE_API_KEY_SAM')  # General API key variable name
YOUTUBE_API = build('youtube', 'v3', developerKey=API_KEY)

# Database CSV filename
DATABASE_CSV = 'youtube_channels_database.csv'

# Statistics tracking
stats = {
    'total_channels_found': 0,
    'channels_skipped': 0,
    'channels_updated': 0,
    'skip_reasons': Counter(),
    'api_calls_search': 0,
    'api_calls_batch': 0,
    'quota_used': 0
}

# Define all possible columns for the database
ALL_COLUMNS = [
    'Username',
    'Subscribers',
    'Total Views',
    'Video Count',
    'Avg Views Per Video',
    'Country',
    'Channel URL',
    'Search Niche',
    'Channel_Image_URL',
    'Views_Last_28_Days',
    'Subs_Last_28_Days',
    'Estimated_Rev_Last_28_Days',
    'Long_Views',
    'Short_Views',
    'ViewStats_Profile_URL'
]


def load_or_create_database():
    """Load existing database or create new one with all columns"""
    if os.path.exists(DATABASE_CSV):
        df = pd.read_csv(DATABASE_CSV)
        print(f"📊 Loaded existing database with {len(df)} channels")

        # Add missing columns if they don't exist
        for col in ALL_COLUMNS:
            if col not in df.columns:
                df[col] = ''

        # Reorder columns to match ALL_COLUMNS
        df = df[ALL_COLUMNS]
        return df
    else:
        print("📝 Creating new database...")
        df = pd.DataFrame(columns=ALL_COLUMNS)
        return df


def save_database(df):
    """Save database to CSV"""
    df.to_csv(DATABASE_CSV, index=False)
    print(f"💾 Database saved with {len(df)} channels")


def find_existing_channel(username, channel_url, df):
    """Find existing channel in database and return its index"""
    # Check by username (case-insensitive)
    username_match = df['Username'].str.lower() == username.lower()

    # Check by channel URL
    url_match = df['Channel URL'] == channel_url

    # Return the index of the first match found
    combined_match = username_match | url_match
    if combined_match.any():
        return df[combined_match].index[0]
    return None


def add_niche_to_existing(existing_niches, new_niche):
    """Add new niche to existing niches, avoiding duplicates"""
    if pd.isna(existing_niches) or existing_niches == '':
        return new_niche

    # Split existing niches into words
    existing_words = set(existing_niches.lower().split())
    new_words = set(new_niche.lower().split())

    # Find truly new words that aren't already present
    unique_new_words = new_words - existing_words

    if unique_new_words:
        # Add the new unique words to the existing niches
        return existing_niches + ' ' + ' '.join(sorted(unique_new_words))
    else:
        # No new words to add
        return existing_niches


def search_channels_by_keyword(query, page_token=None, max_results=50):
    """Search for channels by keyword/niche using YouTube API"""
    params = {
        'part': 'snippet',
        'q': query,
        'type': 'channel',
        'maxResults': max_results,
        'order': 'relevance',
        'relevanceLanguage': 'en'
    }

    if page_token:
        params['pageToken'] = page_token

    request = YOUTUBE_API.search().list(**params)
    response = request.execute()
    stats['api_calls_search'] += 1
    stats['quota_used'] += 100  # Search calls cost 100 units
    return response


def get_channels_batch_optimized(channel_ids):
    """Optimized batch fetching of channel details"""
    if not channel_ids:
        return []

    batch_size = 50
    all_channels = []

    for i in range(0, len(channel_ids), batch_size):
        batch_ids = channel_ids[i:i + batch_size]
        request = YOUTUBE_API.channels().list(
            part='snippet,statistics',
            id=','.join(batch_ids)
        )
        response = request.execute()
        all_channels.extend(response.get('items', []))
        stats['api_calls_batch'] += 1
        stats['quota_used'] += 1  # Channel details cost 1 unit

        if i + batch_size < len(channel_ids):
            time.sleep(0.1)  # Small delay between batches

    return all_channels


def get_proper_channel_url(channel_item):
    """Get the proper YouTube channel URL"""
    channel_id = channel_item['id']
    custom_url = channel_item['snippet'].get('customUrl', '')

    if custom_url:
        if custom_url.startswith('@'):
            return f'https://www.youtube.com/{custom_url}'
        else:
            return f'https://www.youtube.com/@{custom_url}'
    else:
        return f'https://www.youtube.com/channel/{channel_id}'


def get_channel_image_url(channel_item):
    """Extract the best quality channel image URL from YouTube API response"""
    try:
        thumbnails = channel_item['snippet'].get('thumbnails', {})

        # Try to get the highest quality thumbnail available
        # Priority: high -> medium -> default
        if 'high' in thumbnails:
            return thumbnails['high']['url']
        elif 'medium' in thumbnails:
            return thumbnails['medium']['url']
        elif 'default' in thumbnails:
            return thumbnails['default']['url']
        else:
            return ''
    except (KeyError, TypeError):
        return ''


def process_channel_data(channel_item):
    """Process individual channel data with proper URL handling"""
    try:
        statistics = channel_item.get('statistics', {})
        subs = int(statistics.get('subscriberCount', '0'))
        total_views = int(statistics.get('viewCount', '0'))
        video_count = int(statistics.get('videoCount', '0'))

        custom_url = channel_item['snippet'].get('customUrl', '')
        if custom_url:
            username = f"@{custom_url}" if not custom_url.startswith('@') else custom_url
        else:
            username = channel_item['snippet']['title']

        channel_url = get_proper_channel_url(channel_item)
        channel_image_url = get_channel_image_url(channel_item)

        return {
            'username': username,
            'subscribers': subs,
            'total_views': total_views,
            'video_count': video_count,
            'channel_id': channel_item['id'],
            'channel_url': channel_url,
            'channel_image_url': channel_image_url,
            'country': channel_item['snippet'].get('country', 'Unknown')
        }
    except (ValueError, KeyError) as e:
        return None


def create_database_row(channel_details, niche):
    """Create a new row for the database with all columns"""
    video_count = channel_details['video_count']
    total_views = channel_details['total_views']
    avg_views_per_video = total_views / video_count if video_count > 0 else 0

    # Create row with all columns, populate YouTube data and leave ViewStats data empty
    row = {}
    for col in ALL_COLUMNS:
        if col == 'Username':
            row[col] = channel_details['username']
        elif col == 'Subscribers':
            row[col] = channel_details['subscribers']
        elif col == 'Total Views':
            row[col] = total_views
        elif col == 'Video Count':
            row[col] = video_count
        elif col == 'Avg Views Per Video':
            row[col] = round(avg_views_per_video, 2)
        elif col == 'Country':
            row[col] = channel_details['country']
        elif col == 'Channel URL':
            row[col] = channel_details['channel_url']
        elif col == 'Search Niche':
            row[col] = niche
        elif col == 'Channel_Image_URL':
            row[col] = channel_details['channel_image_url']
        else:
            # ViewStats columns - leave empty for now
            row[col] = ''

    return row


def scrape_channels_by_niche(niche, min_subs, max_subs, country_filter=None, target_creators=10):
    """Main scraping function that searches channels by niche with quota optimization"""
    # Load existing database
    database_df = load_or_create_database()

    next_page_token = None
    new_results = []
    updated_channels = 0
    pages_searched = 0
    max_pages = 15  # Limit pages to control quota usage
    channels_processed = 0

    print(f"🎯 Searching for channels in niche: {niche}")
    print(f"📊 Target: {target_creators} NEW channels with {min_subs:,} - {max_subs:,} subscribers")
    if country_filter:
        print(f"🌍 Country filter: {country_filter}")

    while len(new_results) < target_creators and pages_searched < max_pages:
        print(f"🔍 Searching page {pages_searched + 1}... (Quota used: {stats['quota_used']})")

        try:
            response = search_channels_by_keyword(niche, page_token=next_page_token, max_results=50)
            pages_searched += 1

            channel_items = response.get('items', [])
            if not channel_items:
                print("❌ No more channels found")
                break

            # Extract channel IDs from search results
            channel_ids = [item['id']['channelId'] for item in channel_items]
            stats['total_channels_found'] += len(channel_ids)

            if not channel_ids:
                print("⚠️ No valid channel IDs found on this page")
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                continue

            # Get detailed channel information in batches
            detailed_channels = get_channels_batch_optimized(channel_ids)

            for channel_item in detailed_channels:
                channels_processed += 1
                channel_details = process_channel_data(channel_item)

                if not channel_details:
                    stats['channels_skipped'] += 1
                    stats['skip_reasons']['Processing Error'] += 1
                    continue

                # Check if channel already exists in database
                existing_index = find_existing_channel(channel_details['username'], channel_details['channel_url'],
                                                       database_df)

                if existing_index is not None:
                    # Channel exists - update niche instead of skipping
                    existing_niches = database_df.at[existing_index, 'Search Niche']
                    updated_niches = add_niche_to_existing(existing_niches, niche)

                    if updated_niches != existing_niches:
                        database_df.at[existing_index, 'Search Niche'] = updated_niches
                        updated_channels += 1
                        print(f"🔄 Updated: {channel_details['username']} - added '{niche}' to niches")
                    else:
                        print(
                            f"ℹ️  No update needed: {channel_details['username']} - niche already contains all keywords")

                    continue

                # Apply subscriber filter
                if not (min_subs <= channel_details['subscribers'] <= max_subs):
                    stats['channels_skipped'] += 1
                    stats['skip_reasons']['Subscribers outside range'] += 1
                    continue

                # Apply country filter if specified
                if country_filter and channel_details['country'].upper() != country_filter.upper():
                    stats['channels_skipped'] += 1
                    stats['skip_reasons']['Country mismatch'] += 1
                    continue

                # Create database row for new channel
                print(f"✅ Found NEW: {channel_details['username']} ({channel_details['subscribers']:,} subs)")
                database_row = create_database_row(channel_details, niche)
                new_results.append(database_row)

                # Check if we've found enough creators
                if len(new_results) >= target_creators:
                    print(f"🎉 Found {target_creators} new matching channels!")
                    break

            # Early exit if we have enough results
            if len(new_results) >= target_creators:
                break

            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                print("📄 No more pages available")
                break

        except Exception as e:
            print(f"❌ Error during search: {e}")
            break

    # Add new results to database
    if new_results:
        new_df = pd.DataFrame(new_results)

        # Fix for pandas FutureWarning - check if database is empty
        if database_df.empty:
            updated_database = new_df
        else:
            updated_database = pd.concat([database_df, new_df], ignore_index=True)

        database_df = updated_database

    # Save database (whether we added new channels or just updated existing ones)
    if new_results or updated_channels > 0:
        save_database(database_df)
        if new_results:
            print(f"✅ Added {len(new_results)} new channels to database")
        if updated_channels > 0:
            print(f"🔄 Updated niches for {updated_channels} existing channels")

    # Update stats
    stats['channels_updated'] = updated_channels

    print(f"\n📊 Search completed:")
    print(f"   - Channels processed: {channels_processed}")
    print(f"   - NEW channels found: {len(new_results)}")
    print(f"   - Existing channels updated: {updated_channels}")
    print(f"   - Channels skipped: {stats['channels_skipped']}")
    print(f"   - Total quota used: {stats['quota_used']} units")

    if stats['skip_reasons']:
        print(f"   - Skip reasons: {dict(stats['skip_reasons'])}")

    return new_results


def print_statistics(results):
    """Print statistics about the scraping process"""
    print(f"\n📊 SCRAPING STATISTICS")
    print(f"=" * 50)

    total_api_calls = stats['api_calls_search'] + stats['api_calls_batch']
    print(f"🔍 API calls: {total_api_calls} ({stats['api_calls_search']} search + {stats['api_calls_batch']} batch)")
    print(f"💰 Quota used: {stats['quota_used']} units")
    print(f"📦 NEW Channels: {len(results)} added")
    print(f"🔄 Updated Channels: {stats['channels_updated']} niche updates")
    print(f"⏭️  Skipped Channels: {stats['channels_skipped']}")

    if stats['skip_reasons']:
        print(f"⚠️  Skip reasons: {dict(stats['skip_reasons'])}")

    if len(results) > 0:
        print(f"💡 Quota efficiency: {len(results)}/{stats['quota_used']} new channels per quota unit")


def get_popular_niches():
    """Return a list of popular YouTube niches for reference"""
    return [
        "Gaming", "Fashion", "Beauty", "Fitness", "Cooking", "Travel", "Tech Reviews",
        "Music", "Comedy", "Education", "Sports", "DIY", "Lifestyle", "Art",
        "Photography", "Business", "Finance", "Health", "Parenting", "Pets",
        "Cars", "Movies", "Books", "Science", "History", "News", "Politics"
    ]


def sanitize_filename(text):
    """Clean filename for safe file saving"""
    return re.sub(r'[^a-zA-Z0-9_]', '_', text)


if __name__ == '__main__':
    print("🚀 Universal YouTube Channel Scraper v4.0")
    print("=" * 60)
    print("📝 This scraper works with ANY niche: Gaming, Fashion, Sports, Tech, etc.")

    # Show some popular niches as examples
    popular_niches = get_popular_niches()
    print(f"💡 Popular niches: {', '.join(popular_niches[:10])}...")
    print()

    niche = input("Enter your target niche/keyword (e.g., 'fashion', 'gaming', 'cooking'): ").strip()
    min_subs = int(input("Minimum subscriber count: "))
    max_subs = int(input("Maximum subscriber count: "))
    country_filter = input("2-letter country code (or Enter to skip): ").strip().upper()
    target_creators = int(input("How many NEW creators to find: "))

    # Estimate quota usage
    estimated_quota = (target_creators * 8) + 500  # Rough estimate
    print(f"\n📊 Estimated quota usage: ~{estimated_quota} units")
    print(f"💾 Database file: {DATABASE_CSV}")
    print(f"🔄 Note: Existing channels will have their niches updated, not skipped")
    confirm = input("Continue? (y/n): ").strip().lower()

    if confirm != 'y':
        print("Operation cancelled.")
        exit()

    print(f"\n🔍 Searching for {target_creators} NEW channels in '{niche}' niche...")

    try:
        results = scrape_channels_by_niche(niche, min_subs, max_subs, country_filter, target_creators)

        if results or stats['channels_updated'] > 0:
            print(f"🎉 Success!")
            if results:
                print(f"   - Found {len(results)} NEW channels and added to database")
            if stats['channels_updated'] > 0:
                print(f"   - Updated niches for {stats['channels_updated']} existing channels")
            print_statistics(results)
        else:
            print("❌ No new matching channels found and no existing channels updated.")
            print("Try different search terms or criteria.")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Please check your API key and internet connection.")