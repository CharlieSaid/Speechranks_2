import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime
import json
import os

def parse_tournament_date(date_str, year):
    """
    Convert tournament date strings to YYYY-MM-DD format
    
    Handles formats:
    - Single day: "Jan 4" -> "2009-01-04"
    - Same month range: "Jan 4-5" -> "2009-01-04"
    - Cross month range: "Apr 28-May 1" -> "2009-04-28"
    
    Args:
        date_str (str): Date string from tournament listing
        year (str): Year of tournament (e.g. '2009')
    
    Returns:
        str: Date in YYYY-MM-DD format (start date if range)
    """
    try:
        # Remove any whitespace
        date_str = date_str.strip()
        
        # Handle cross-month format (e.g. "Apr 28-May 1")
        if '-' in date_str and len(date_str.split('-')[1].split()) == 2:
            start_date = date_str.split('-')[0]
            return datetime.strptime(f"{start_date} {year}", "%b %d %Y").strftime("%Y-%m-%d")
            
        # Handle same-month range or single day
        month = date_str.split()[0]
        day = date_str.split()[1].split('-')[0]  # Take first day if range
        
        return datetime.strptime(f"{month} {day} {year}", "%b %d %Y").strftime("%Y-%m-%d")
        
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        return None

def scrape_tournament_page(url):
    """
    Scrape detailed information from a tournament's page
    
    Args:
        url (str): URL of tournament page
        
    Returns:
        dict: Tournament details including location, dates, and events
    """
    # Set up headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find tournament details table
        details = {}
        details_table = soup.find('table', class_='summary')
        if details_table:
            rows = details_table.find_all('tr')
            for row in rows:
                th = row.find('th')
                td = row.find('td')
                if th and td:
                    label = th.text.strip().lower()
                    value = td.text.strip()
                    
                    if 'location' in label:
                        details['location'] = value
                    elif 'start date' in label:
                        details['start_date'] = value
                    elif 'end date' in label:
                        details['end_date'] = value
        
        # Find events table
        events = []
        events_table = soup.find('table', class_='listing')
        if events_table:
            rows = events_table.find_all('tr')[1:]  # Skip header
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    event = {
                        'name': cells[0].text.strip(),
                        'population': cells[1].text.strip()
                    }
                    events.append(event)
        
        details['events'] = events
        return details
        
    except requests.RequestException as e:
        print(f"Error accessing tournament page {url}: {e}")
    except Exception as e:
        print(f"Error processing tournament page {url}: {e}")
    
    return None

def scrape_tournament_list(year):
    """
    Scrape tournament list and details for a given year
    
    Args:
        year (str): Year to scrape (e.g. '2009')
    """
    url = f"http://www.speechranks.com/{year}/tournaments"
    
    # Create tournament_files directory if it doesn't exist
    os.makedirs('tournament_files', exist_ok=True)
    
    # Initialize data structure as a list instead of dict
    tournaments = []
    
    # Set up headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print('Received tournament list response')
        
        soup = BeautifulSoup(response.text, 'html.parser')
        tournament_list = soup.find('ul', id='tournament-list')
        
        if tournament_list:
            for tournament in tournament_list.find_all('li'):
                link = tournament.find('a')
                if link:
                    date_str = tournament.get_text().split(': ')[-1]
                    tournament_data = {
                        'name': link.text.strip(),
                        'url': f"http://www.speechranks.com{link['href']}",
                        'state': tournament.get('class', [''])[0].split('-')[0],
                        'date': parse_tournament_date(date_str, year),
                        'date_raw': date_str
                    }
                    
                    # Scrape detailed tournament page
                    print(f"Scraping details for {year}: {tournament_data['name']}")
                    details = scrape_tournament_page(tournament_data['url'])
                    if details:
                        tournament_data.update(details)
                    
                    tournaments.append(tournament_data)
                    time.sleep(0.5)  # Polite delay between requests
        
        # Save to JSON file in tournament_files directory
        filename = os.path.join('tournament_files', f'tournaments_{year}.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(tournaments, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(tournaments)} tournaments to {filename}")
        
    except requests.RequestException as e:
        print(f"Error accessing {url}: {e}")
    except Exception as e:
        print(f"Error processing data: {e}")

if __name__ == "__main__":
    
    target_years = [2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]

    for year in target_years:
        scrape_tournament_list(year)