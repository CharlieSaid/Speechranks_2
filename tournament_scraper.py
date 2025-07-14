import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import json
import os

# Constants
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
BASE_URL = "http://www.speechranks.com"
REQUEST_DELAY = 0.5

def parse_tournament_date(date_str, year):
    """Convert tournament date to YYYY-MM-DD format, taking start date if range."""
    try:
        # Take everything before first '-' (handles both single dates and ranges)
        start_part = date_str.split('-')[0].strip()
        return datetime.strptime(f"{start_part} {year}", "%b %d %Y").strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        return None

def get_tournament_year(date_str, season_year):
    """Determine actual calendar year for tournament based on month."""
    try:
        first_part = date_str.split('-')[0].strip()  # Get "Jan 4" from "Jan 4-5"
        month = first_part.split()[0]  # Get "Jan" from "Jan 4"
        
        # For academic year: Oct/Nov/Dec = previous calendar year
        if month in ['Oct', 'Nov', 'Dec']:
            return int(season_year) - 1
        else:
            return int(season_year)
    except Exception as e:
        print(f"Error determining year for date '{date_str}': {e}")
        return int(season_year)

def make_request(url):
    """Make HTTP request with error handling."""
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.RequestException as e:
        print(f"Error accessing {url}: {e}")
        return None

def extract_tournament_details(soup):
    """Extract tournament details from soup."""
    details = {'events': []}
    
    # Extract basic details
    details_table = soup.find('table', class_='summary')
    if details_table:
        for row in details_table.find_all('tr'):
            th, td = row.find('th'), row.find('td')
            if th and td:
                label = th.text.strip().lower()
                value = td.text.strip()
                if 'location' in label:
                    details['location'] = value
                elif 'start date' in label:
                    details['start_date'] = value
                elif 'end date' in label:
                    details['end_date'] = value
    
    # Extract events
    events_table = soup.find('table', class_='listing')
    if events_table:
        for row in events_table.find_all('tr')[1:]:  # Skip header
            cells = row.find_all('td')
            if len(cells) >= 2:
                details['events'].append({
                    'name': cells[0].text.strip(),
                    'population': cells[1].text.strip()
                })
    
    return details

def save_tournaments(tournaments, year):
    """Save tournament data to JSON file."""
    os.makedirs('tournament_files', exist_ok=True)
    filename = os.path.join('tournament_files', f'tournaments_{year}.json')
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(tournaments, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(tournaments)} tournaments to {filename}")

def scrape_tournament_list(year):
    """Scrape all tournaments for a given year."""
    url = f"{BASE_URL}/{int(year)-1}/tournaments"
    tournaments = []
    
    soup = make_request(url)
    if not soup:
        return
    
    print('Received tournament list response')
    tournament_list = soup.find('ul', id='tournament-list')
    if not tournament_list:
        print(f"No tournament list found for {year}")
        return
    
    for tournament in tournament_list.find_all('li'):
        link = tournament.find('a')
        if not link:
            continue

        date_str = tournament.get_text().split(': ')[-1]
        tournament_year = get_tournament_year(date_str, year)
        
        tournament_data = {
            'name': link.text.strip(),
            'url': f"{BASE_URL}{link['href']}",
            'state': tournament.get('class', [''])[0].split('-')[0],
            'date': parse_tournament_date(date_str, tournament_year)
        }
        
        # Get detailed info
        print(f"Scraping details for {year}: {tournament_data['name']}, tournament year: ({tournament_year})")
        detail_soup = make_request(tournament_data['url'])
        if detail_soup:
            tournament_data.update(extract_tournament_details(detail_soup))
        
        tournaments.append(tournament_data)
        time.sleep(REQUEST_DELAY)
    
    # Save results
    save_tournaments(tournaments, year)

if __name__ == "__main__":
    target_years = [str(year) for year in range(2010, 2026)]
    #update protocol: target current year.
    #target_years = [str(datetime.now().year)]

    for year in target_years:
        scrape_tournament_list(year)