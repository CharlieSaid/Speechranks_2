from debate_scraper import scrape_year
from datetime import datetime, timedelta

def read_last_update():
    """Read the last update timestamp from file"""
    try:
        with open('last_update.txt', 'r') as f:
            content = f.read().strip()
            if content.startswith('Last update: '):
                date_str = content[13:]  # Remove "Last update: " prefix
                time = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                return time
            return None  # Return None if content doesn't match expected format
    except (FileNotFoundError, ValueError):
        return None  # Return None if file doesn't exist or date is invalid

def write_last_update(timestamp):
    """Write the current timestamp to file"""
    with open('last_update.txt', 'w') as f:
        f.write(f'Last update: {timestamp.strftime("%Y-%m-%d %H:%M:%S")}')

def write_last_attempt(timestamp):
    """Write the current timestamp to file"""
    with open('last_attempt.txt', 'w') as f:
        f.write(f'Last attempt: {timestamp.strftime("%Y-%m-%d %H:%M:%S")}')

def update_years(years_to_scrape):
    """
    Update data for specified years if enough time has passed
    
    Args:
        years_to_scrape (list): List of years to scrape (e.g., ['2023', '2024'])
    """
    current_time = datetime.now()
    last_update = read_last_update()
    print(last_update)
    
    # # If last_update.txt doesn't exist or is invalid, proceed with update
    # if last_update is None:
    #     print("No valid last update time found. Proceeding with update.")
    # else:
    #     # Check if 1 day has passed
    #     time_since_update = current_time - last_update
    #     if time_since_update < timedelta(days=1):
    #         print(f"Only {time_since_update.total_seconds()/3600} hours since last update. Skipping.")
    #         write_last_attempt(current_time)
    #         return
    
    print(f"Starting data update for years: {', '.join(years_to_scrape)}")
    
    # Get current year
    current_year = str(current_time.year + 1 if current_time.month >= 10 else current_time.year)
    
    # Override with specific year if needed
    target_years = years_to_scrape  # Modify this list to scrape specific years
    
    for year in target_years:
        print(year)
        print(f"\nScraping data for {year}...")
        scrape_year(year)
    
    # Update the timestamp
    write_last_update(current_time)
    print(f"Update complete. Next update available after: {(current_time + timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    
    target_years = ['2025']
    
    update_years(target_years)