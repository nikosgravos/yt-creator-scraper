import pandas as pd
import time
import random
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# Database CSV filename
DATABASE_CSV = 'youtube_channels_database.csv'


def load_database():
    """Load the database CSV"""
    if not os.path.exists(DATABASE_CSV):
        print(f"❌ Database file '{DATABASE_CSV}' not found!")
        print("Please ensure you have a CSV file with YouTube channel data.")
        return None

    df = pd.read_csv(DATABASE_CSV)
    print(f"📊 Loaded database with {len(df)} channels")
    return df


def save_database(df):
    """Save the updated database"""
    df.to_csv(DATABASE_CSV, index=False)
    print(f"💾 Database updated and saved")


def get_channels_to_process(df):
    """Get channels that need ViewStats processing"""
    # Check for channels where ViewStats_Profile_URL is empty or NaN
    mask = (df['ViewStats_Profile_URL'].isna()) | (df['ViewStats_Profile_URL'] == '') | (
            df['ViewStats_Profile_URL'] == 'N/A')
    channels_to_process = df[mask].copy()

    print(f"🎯 Found {len(channels_to_process)} channels that need ViewStats processing")
    return channels_to_process


def extract_username_from_channel_url(channel_url):
    """Extract username from YouTube channel URL for ViewStats lookup"""
    if pd.isna(channel_url) or not channel_url:
        return None

    # Handle different URL formats
    if '@' in channel_url:
        # Extract @username from URL like https://www.youtube.com/@username
        parts = channel_url.split('@')
        if len(parts) > 1:
            username = parts[1].split('/')[0]  # Remove any trailing path
            return username
    elif '/channel/' in channel_url:
        # For channel ID URLs, we can't easily get the username
        # ViewStats might not work with channel IDs
        return None
    elif '/c/' in channel_url:
        # Extract custom URL from /c/ format
        parts = channel_url.split('/c/')
        if len(parts) > 1:
            username = parts[1].split('/')[0]
            return username
    elif '/user/' in channel_url:
        # Extract from old /user/ format
        parts = channel_url.split('/user/')
        if len(parts) > 1:
            username = parts[1].split('/')[0]
            return username

    return None


def setup_driver():
    """Setup Chrome driver with optimized options"""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # Performance optimizations
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")  # Don't load images for faster loading
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=VizDisplayCompositor")

    # Set page load strategy to 'eager' for faster loading
    options.page_load_strategy = 'eager'

    # Uncomment the next line for headless mode (faster)
    # options.add_argument("--headless")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # Set longer timeouts to handle slow loading pages
    driver.set_page_load_timeout(30)  # Increased timeout for page loads
    driver.implicitly_wait(5)  # Increased implicit wait

    # Hide automation indicators
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def check_if_channel_not_tracked(driver):
    """Check if ViewStats shows that the channel is not being tracked"""
    try:
        # Check page title for "Not Found"
        title = driver.title.lower()
        if "not found" in title:
            return True, "Page shows 'Not Found' in title"

        # Check for the specific "not tracking" message
        try:
            not_tracking_elements = driver.find_elements(By.XPATH,
                                                         "//*[contains(text(), \"Looks like we aren't tracking this channel\") or " +
                                                         "contains(text(), \"aren't tracking this channel\") or " +
                                                         "contains(text(), \"Track Channel\")]")

            if not_tracking_elements:
                return True, "Channel not tracked by ViewStats"
        except:
            pass

        # Check for 404 or error indicators in page content
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            if ("404" in body_text or
                    "page not found" in body_text or
                    "not found" in body_text or
                    "error" in body_text):
                return True, "Page contains error indicators"
        except:
            pass

        return False, None

    except Exception as e:
        return True, f"Error checking page status: {str(e)}"


def scrape_viewstats_data(driver, username, channel_url, row_index, total_channels):
    """Scrape ViewStats data for a single channel"""
    print(f"Processing {row_index + 1}/{total_channels}: {username}")

    # Try to extract a better username from the channel URL if needed
    if not username or username == 'Unknown':
        extracted_username = extract_username_from_channel_url(channel_url)
        if extracted_username:
            username = extracted_username
        else:
            print(f"  ❌ Cannot extract username - SKIPPING")
            return {
                "ViewStats_Profile_URL": "no username available",
                "Views_Last_28_Days": "",
                "Subs_Last_28_Days": "",
                "Estimated_Rev_Last_28_Days": "",
                "Long_Views": "",
                "Short_Views": ""
            }

    viewstats_url = f"https://www.viewstats.com/{username}/channelytics"
    print(f"  🔍 Navigating to: {viewstats_url}")

    try:
        # Navigate to the page
        driver.get(viewstats_url)

        # Wait a bit for the page to load
        time.sleep(3)

        # Check if the channel is not tracked by ViewStats
        is_not_tracked, reason = check_if_channel_not_tracked(driver)
        if is_not_tracked:
            print(f"  ❌ {reason} - SKIPPING")
            return {
                "ViewStats_Profile_URL": "no viewstats page available",
                "Views_Last_28_Days": "",
                "Subs_Last_28_Days": "",
                "Estimated_Rev_Last_28_Days": "",
                "Long_Views": "",
                "Short_Views": ""
            }

        # Initialize data storage
        viewstats_data = {
            "ViewStats_Profile_URL": viewstats_url,
            "Views_Last_28_Days": "",
            "Subs_Last_28_Days": "",
            "Estimated_Rev_Last_28_Days": "",
            "Long_Views": "",
            "Short_Views": ""
        }

        # Step 1: Try to get the main views data (critical success indicator)
        print("  🔄 Looking for views data...")
        try:
            views_element = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "p.card-value-views"))
            )
            viewstats_data["Views_Last_28_Days"] = views_element.text.strip()
            print(f"  ✅ Views found: {viewstats_data['Views_Last_28_Days']}")

        except TimeoutException:
            print(f"  ⏳ Views data taking longer to load, trying alternative selectors...")
            # Try alternative selectors for views
            try:
                views_alt = driver.find_element(By.CSS_SELECTOR, "[class*='card-value'][class*='views']")
                viewstats_data["Views_Last_28_Days"] = views_alt.text.strip()
                print(f"  ✅ Views found (alt): {viewstats_data['Views_Last_28_Days']}")
            except NoSuchElementException:
                print(f"  ❌ No views data found after extended wait - SKIPPING")
                viewstats_data["ViewStats_Profile_URL"] = "no viewstats data available"
                return viewstats_data

        # Step 2: Collection of remaining data with longer waits
        print("  🔄 Collecting additional data...")

        # Subscribers (try multiple selectors)
        try:
            # Wait for subscribers data
            subs_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "p.card-value"))
            )
            viewstats_data["Subs_Last_28_Days"] = subs_element.text.strip()
            print(f"    ✓ Subs: {viewstats_data['Subs_Last_28_Days']}")
        except TimeoutException:
            print("    ⏳ No subs data found")

        # Revenue
        try:
            est_rev_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "p.card-rev"))
            )
            viewstats_data["Estimated_Rev_Last_28_Days"] = est_rev_element.text.strip()
            print(f"    ✓ Revenue: {viewstats_data['Estimated_Rev_Last_28_Days']}")
        except TimeoutException:
            print("    ⏳ No revenue data found")

        # Long vs Short views
        try:
            print("    🔄 Looking for long/short views data...")
            stats_blocks = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".longs-vs-shorts-stats-value"))
            )

            for block in stats_blocks:
                try:
                    parent = block.find_element(By.XPATH, "..")
                    label = parent.find_element(By.CLASS_NAME, "vsvs-text-gray").text
                    if "Long Views" in label:
                        viewstats_data["Long_Views"] = block.text.strip()
                        print(f"    ✓ Long views: {viewstats_data['Long_Views']}")
                    elif "Short Views" in label:
                        viewstats_data["Short_Views"] = block.text.strip()
                        print(f"    ✓ Short views: {viewstats_data['Short_Views']}")
                except:
                    continue

        except TimeoutException:
            print("    ⏳ No long/short views data found")

        print(f"  ✅ SUCCESS for {username}")
        return viewstats_data

    except WebDriverException as e:
        print(f"  ❌ WebDriver error: {e}")
        return {
            "ViewStats_Profile_URL": "webdriver error",
            "Views_Last_28_Days": "",
            "Subs_Last_28_Days": "",
            "Estimated_Rev_Last_28_Days": "",
            "Long_Views": "",
            "Short_Views": ""
        }
    except Exception as e:
        print(f"  ❌ Error: {type(e).__name__}: {e}")
        return {
            "ViewStats_Profile_URL": "error occurred",
            "Views_Last_28_Days": "",
            "Subs_Last_28_Days": "",
            "Estimated_Rev_Last_28_Days": "",
            "Long_Views": "",
            "Short_Views": ""
        }


def process_viewstats_data():
    """Main function to process ViewStats data for channels in database"""
    # Load database
    df = load_database()
    if df is None:
        return

    # Ensure ViewStats columns exist and have correct data types
    viewstats_columns = [
        'ViewStats_Profile_URL',
        'Views_Last_28_Days',
        'Subs_Last_28_Days',
        'Estimated_Rev_Last_28_Days',
        'Long_Views',
        'Short_Views'
    ]

    for col in viewstats_columns:
        if col not in df.columns:
            df[col] = ''
        df[col] = df[col].astype('object')  # Allow any data type

    # Get channels that need processing
    channels_to_process = get_channels_to_process(df)

    if len(channels_to_process) == 0:
        print("✅ All channels already have ViewStats data processed!")
        return

    print(f"🚀 Starting ViewStats scraping for {len(channels_to_process)} channels...")

    # Setup driver
    driver = setup_driver()

    processed_count = 0
    successful_count = 0
    failed_count = 0

    try:
        for idx, (_, row) in enumerate(channels_to_process.iterrows()):
            username = row.get('Username', 'Unknown')
            channel_url = row.get('Channel URL', '')

            # Get the original index in the full dataframe
            original_index = row.name

            # Scrape ViewStats data
            viewstats_data = scrape_viewstats_data(driver, username, channel_url, idx, len(channels_to_process))

            # Update the main dataframe
            for key, value in viewstats_data.items():
                df.at[original_index, key] = value

            processed_count += 1

            if (viewstats_data["ViewStats_Profile_URL"] != "no viewstats page available" and
                    viewstats_data["ViewStats_Profile_URL"] != "no username available" and
                    viewstats_data["ViewStats_Profile_URL"] != "webdriver error" and
                    viewstats_data["ViewStats_Profile_URL"] != "error occurred" and
                    viewstats_data["ViewStats_Profile_URL"] != "no viewstats data available"):
                successful_count += 1
            else:
                failed_count += 1

            # Random delay between requests (1-3 seconds)
            delay = random.uniform(1, 3)
            print(f"  ⏳ Delay: {delay:.1f}s before next channel...")
            time.sleep(delay)

            # Save progress every 10 records
            if (idx + 1) % 10 == 0:
                save_database(df)
                print(f"  💾 Progress saved at {idx + 1} records")

    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    finally:
        # Close browser
        driver.quit()

        # Save final results
        save_database(df)

    print(f"\n✅ ViewStats scraping complete!")
    print(f"📊 Processed: {processed_count} channels")
    print(f"✅ Successful: {successful_count} channels")
    print(f"❌ Failed/No page: {failed_count} channels")
    print(f"💾 Database updated: {DATABASE_CSV}")


if __name__ == '__main__':
    print("🚀 General ViewStats Scraper v4.0")
    print("=" * 50)

    confirm = input("Process ViewStats data for channels missing this information? (y/n): ").strip().lower()

    if confirm != 'y':
        print("Operation cancelled.")
        exit()

    try:
        process_viewstats_data()
        print("\n🎉 Script completed!")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Please check your setup and try again.")