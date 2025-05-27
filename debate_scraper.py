"""
Debate Team Data Scraper

This script scrapes debate team and debater information from speechranks.com.
It collects comprehensive data including team records, individual speech events.
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import re
from datetime import datetime

###########################################
# Constants and Configuration
###########################################

# Request headers to mimic browser behavior
BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Error handling configuration
MAX_CONSECUTIVE_404s = 100
consecutive_404_count = 0

# Base URLs
BASE_URL = "http://www.speechranks.com"
TEAM_URL_TEMPLATE = f"{BASE_URL}/profile/entry/"

# Words to remove from club names for standardization
CLUB_NAME_FILTERS = ['Speech and Debate', 'Speech', 'Debate', 'Forensics', 'Club', '&']

# Request delay (in seconds) to be polite to the server
REQUEST_DELAY = 0.5

###########################################
# Utility Functions
###########################################

def extract_year_from_range(text):
    """
    Extracts the latter year from a year range (e.g., '2009-2010' returns '2010')
    
    Args:
        text (str): Text containing year or year range
    Returns:
        str: Extracted year, or None if no year found
    """
    return text[5:9]

def clean_numeric_string(text):
    """
    Removes non-numeric characters from a string
    
    Args:
        text (str): String potentially containing numbers
    Returns:
        str: String containing only numeric characters
    """
    if not text:
        return ""
    return ''.join(char for char in text if char.isdigit())

def count_checkmarks(cell_content):
    """
    Counts checkmarks in a table cell
    Handles both individual marks (≤3) and multiplier notation (e.g., 'x4')
    
    Args:
        cell_content (BeautifulSoup): Table cell containing achievement marks
    Returns:
        int: Number of achievement marks
    """
    if not cell_content:
        return 0
        
    tick_images = cell_content.find_all('img')
    if not tick_images:
        return 0
        
    text_after = cell_content.get_text()
    if text_after and 'x' in text_after:
        try:
            return int(clean_numeric_string(text_after))
        except ValueError:
            return len(tick_images)
    
    return len(tick_images)

def standardize_club_name(club_name):
    """
    Removes common filler words from club names for consistency
    
    Args:
        club_name (str): Original club name
    Returns:
        str: Cleaned club name
    """
    cleaned_name = club_name
    for word in CLUB_NAME_FILTERS:
        cleaned_name = cleaned_name.replace(word, '')
    return cleaned_name.strip()

###########################################
# Individual Data Scraping
###########################################

def scrape_debater_profile(url):
    """
    Scrapes individual debater's profile for club and events
    
    Args:
        url (str): URL of debater's profile page
    Returns:
        dict: Debater's information including clubs and events
    """
    debater_data = {
        'debate_club': None,
        'speech_club': None,
        'speech_events': [],
        'debate_events': []
    }
    
    try:
        response = requests.get(url, headers=BROWSER_HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract club information
        clubs_table = soup.find('table', class_='summary')
        if clubs_table:
            for row in clubs_table.find_all('tr'):
                th, td = row.find('th'), row.find('td')
                if th and td:
                    label, value = th.text.strip(), td.text.strip()
                    
                    if "Debate Club:" in label:
                        debater_data['debate_club'] = standardize_club_name(value)
                    elif "Speech Club:" in label:
                        debater_data['speech_club'] = standardize_club_name(value)
        
        # Extract speech events
        events_table = soup.find('table', class_='listing')
        if events_table:
            for row in events_table.find_all('tr')[1:]:  # Skip header
                event_cell = row.find('td', class_='text')
                event_name = event_cell.text.strip().rsplit(' ', 1)[0]
                
                # Add defensive checks for numeric values
                try:
                    rank_cell = row.find_all('td', class_='number')[0].get_text()
                    rank = clean_numeric_string(rank_cell)
                    if not rank:  # If empty string, use "0"
                        rank = "0"
                except (IndexError, AttributeError):
                    rank = "0"
                
                event_data = {
                    'name': event_name,
                    'rank': rank,  # Now guaranteed to be a string with numbers or "0"
                    'points': row.find_all('td', class_='number')[2].get_text().strip(),
                    'partner': row.find_all('td')[-2].get_text().strip(),
                    'checkmarks': count_checkmarks(row.find_all('td')[-1])
                }
                
                if event_name in ['Parliamentary Debate', 'Team Policy Debate', 'Lincoln Douglas Debate']:
                    debater_data['debate_events'].append(event_data)
                else:
                    debater_data['speech_events'].append(event_data)
                    
    # except requests.RequestException as e:
    #     print(f"Error accessing debater page {url}: {e}")
    # except Exception as e:
    #     print(f"Error processing debater page {url}: {e}")
    
    finally:
        time.sleep(REQUEST_DELAY)
        return debater_data

###########################################
# Team Data Scraping
###########################################

def scrape_debate_page(entry_id):
    """
    Scrapes a team's debate page to collect team information
    
    Args:
        entry_id (int): Team's unique identifier
    Returns:
        dict: Complete team data including debater profiles and tournament history
    """
    url = f"{BASE_URL}/profile/entry/{entry_id}"
    global consecutive_404_count
    
    try:
        response = requests.get(url, headers=BROWSER_HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Reset the consecutive 404 count
        consecutive_404_count = 0

        # Find the body div
        body_div = soup.find('div', id='body')
        # Find the h1 in the body div
        page_title = body_div.find('h1')

        if 'Team Policy Debate' not in page_title.text:
            print(f"ID {entry_id} not TP")
            return None
        else:
            print(f"ID {entry_id} is TP - Proceeding")

        # Initialize team data structure
        team_data = {
            'team_id': entry_id,
            'url': url,
            'year': None,
            'state': None,
            'debater1': {'name': None, 'url': None},
            'debater2': {'name': None, 'url': None}
        }
            
        year_text = page_title.text.strip()
        team_data['year'] = extract_year_from_range(year_text)
        
        # Extract debater information
        debater_links = body_div.find_all('a')
        
        if len(debater_links) >= 2:
            # Get info for both debaters
            team_data['debater1']['name'] = debater_links[0].text.strip()
            team_data['debater1']['url'] = f"{BASE_URL}{debater_links[0]['href']}"
            team_data['debater2']['name'] = debater_links[1].text.strip()
            team_data['debater2']['url'] = f"{BASE_URL}{debater_links[1]['href']}"
            
            # Scrape individual debater pages
            print(f"Scraping data for {team_data['debater1']['name']}")
            if debater1_data := scrape_debater_profile(team_data['debater1']['url']):
                team_data['debater1'].update(debater1_data)
            
            print(f"Scraping data for {team_data['debater2']['name']}")
            if debater2_data := scrape_debater_profile(team_data['debater2']['url']):
                team_data['debater2'].update(debater2_data)
        
        # Extract team statistics
        if stats_table := soup.find('table', class_='summary'):
            for row in stats_table.find_all('tr'):
                th, td = row.find('th'), row.find('td')
                if th and td:
                    label = th.text.strip().lower()
                    value = td.text.strip()
                    
                    # Handle each statistic directly
                    if 'rank points' in label:
                        team_data['rank_points'] = value
                    elif 'total rounds won' in label:
                        team_data['total_wins'] = value
                    elif 'total rounds lost' in label:
                        team_data['total_losses'] = value
                    elif 'prelim rounds won' in label:
                        team_data['prelim_wins'] = value
                    elif 'prelim rounds lost' in label:
                        team_data['prelim_losses'] = value
                    elif 'national rank' in label:
                        team_data['national_rank'] = clean_numeric_string(value)
                    # Handle state rank
                    elif 'rank' in label and 'national' not in label:
                        team_data['state'] = label.split()[0].upper()
                        team_data['state_rank'] = clean_numeric_string(value)
        
        # Extract tournament results
        team_data['tournaments'] = []
        if tournament_table := soup.find('table', class_='listing'):
            for row in tournament_table.find_all('tr')[2:]:  # Skip headers
                cells = row.find_all('td')
                if len(cells) >= 6 and (tournament_link := cells[0].find('a')):
                    tournament = {
                        'name': tournament_link.text.strip(),
                        'url': f"{BASE_URL}{tournament_link['href']}",
                        'place': clean_numeric_string(cells[1].text.strip()),
                        'prelim_record': cells[2].text.strip(),
                        'overall_record': cells[3].text.strip(),
                        'points': cells[4].text.strip(),
                        'checkmarks': count_checkmarks(cells[5])
                    }
                    team_data['tournaments'].append(tournament)
        
        return team_data
        
    except requests.exceptions.RequestException as e:
        if '404' in str(e):
            consecutive_404_count += 1
            print(f"404 error at {url}")
        return None
    # except Exception as e:
    #     print(f"Error processing {url}: {e}")
    #     return None
    finally:
        time.sleep(REQUEST_DELAY)

def scrape_year(target_year):
    """
    Scrapes all Team Policy Debate teams for a specific academic year
    
    Args:
        target_year (str): Year to scrape (e.g., '2024')
    Returns:
        list: Collection of team data for the specified year
    """
    global consecutive_404_count
    consecutive_404_count = 0
    
    # Load year-to-ID mapping
    with open('year_dict.txt', 'r') as f:
        year_dict = dict(line.split(':') for line in f)
    
    # Determine ID range for year
    start_id = int(year_dict[target_year])
    try:
        end_id = int(year_dict[str(int(target_year) + 1)])
    except KeyError:
        end_id = 1000000
    
    teams_data = []
    
    # Scrape teams within ID range
    for entry_id in range(start_id, end_id):
        if consecutive_404_count >= MAX_CONSECUTIVE_404s:
            print(f"\nStopping early: {MAX_CONSECUTIVE_404s} consecutive 404 errors")
            break
        
        if team_data := scrape_debate_page(entry_id):
            teams_data.append(team_data)
    
    # Save year data
    output_path = f'to_upload/year_files/debate_teams_{target_year}.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(teams_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nScraped {len(teams_data)} teams. Data saved to {output_path}")
    return teams_data

def main():
    """Controls the scraping process based on current date or manual override"""
    
    # Determine target year based on current date
    current_date = datetime.now()
    current_year = str(current_date.year + 1 if current_date.month >= 10 else current_date.year)
    
    # Override with specific year if needed
    target_years = [current_year]  # Modify this list to scrape specific years
    
    for year in target_years:
        scrape_year(year)
    # scrape_range(101969, 101975)

def scrape_range(start_id, end_id):
    """
    Scrape Team Policy Debate teams between specified ID range.
    Used for testing scraper functionality.
    
    Args:
        start_id (int): Starting team ID to scrape
        end_id (int): Ending team ID to scrape
    """
    teams_data = []
    
    # Scrape IDs in the specified range
    for entry_id in range(start_id, end_id):
        team_data = scrape_debate_page(entry_id)
        if team_data:
            teams_data.append(team_data)
            print(f"Finished scraping team at ID {entry_id}")
        else:
            print(f"No team found at ID {entry_id}")
    
    # Save collected data to testing file
    with open('testing_data.json', 'w', encoding='utf-8') as f:
        json.dump(teams_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nScraped {len(teams_data)} teams between IDs {start_id}-{end_id}.")
    print("Data saved to testing_data.json")
    
    return teams_data

if __name__ == "__main__":
    main() 