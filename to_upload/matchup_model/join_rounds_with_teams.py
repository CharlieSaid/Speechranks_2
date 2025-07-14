"""
Join rounds data with team statistics from year files.

This script opens rounds_extracted.csv, finds the year for each round,
opens the corresponding year file, and adds team statistics such as
win rate, number of tournaments, and debate rounds to the data.
"""

import pandas as pd
import json
import os
import re
from typing import Dict, List, Any, Optional

def normalize_name(name: str) -> str:
    """Normalize a name for matching by removing punctuation, extra spaces, and converting to lowercase."""
    if not name:
        return ""
    
    # Convert to lowercase and strip
    normalized = str(name).strip().lower()
    
    # Remove punctuation and normalize spaces
    normalized = re.sub(r'[\'.\-]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Handle common surname prefixes
    prefixes = {'de la': 'dela', 'van der': 'vander', 'mac': 'mc'}
    for original, replacement in prefixes.items():
        normalized = normalized.replace(f' {original} ', f' {replacement} ')
        normalized = normalized.replace(f' {original}', f' {replacement}')
        normalized = normalized.replace(f'{original} ', f'{replacement} ')
    
    return normalized.strip()

def generate_name_variations(name: str) -> List[str]:
    """Generate multiple variations of a name for flexible matching."""
    if not name:
        return [""]
    
    variations = set()
    original = str(name).strip()
    normalized = normalize_name(original)
    
    # Add original, normalized, and no-spaces versions
    variations.add(original)
    variations.add(normalized)
    variations.add(normalized.replace(' ', ''))
    
    # Add initials variations
    parts = normalized.split()
    if len(parts) >= 2:
        variations.add(f"{parts[0][0]} {parts[-1]}")  # First initial + last name
        variations.add(f"{parts[0]} {parts[-1][0]}")  # First name + last initial
    
    return list(filter(None, variations))  # Remove empty strings

def load_year_file(year: int, year_files_dir: str = "to_upload/year_files") -> Dict[str, Any]:
    """Load the JSON data for a specific year and create team mapping."""
    filename = f"debate_teams_{year}.json"
    filepath = os.path.join(year_files_dir, filename)
    
    if not os.path.exists(filepath):
        print(f"Warning: Year file {filename} not found")
        return {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create mapping with name variations
        team_dict = {}
        for team in data:
            debater1_name = team.get('debater1', {}).get('name', '')
            debater2_name = team.get('debater2', {}).get('name', '')
            
            if debater1_name and debater2_name:
                # Generate all variations for both debaters
                debater1_variations = generate_name_variations(debater1_name)
                debater2_variations = generate_name_variations(debater2_name)
                
                # Create keys for all combinations in both orders
                for d1_var in debater1_variations:
                    for d2_var in debater2_variations:
                        if d1_var and d2_var:
                            team_dict[f"{d1_var}|{d2_var}"] = team
                            team_dict[f"{d2_var}|{d1_var}"] = team
                
        return team_dict
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return {}

def create_team_mapping_from_rounds(rounds_df: pd.DataFrame) -> Dict[str, Dict[str, List[str]]]:
    """Create year-specific team code to member names mapping from rounds data."""
    mapping = {}
    
    for year in rounds_df['Year'].unique():
        year_rounds = rounds_df[rounds_df['Year'] == year]
        year_mapping = {}
        
        # Process both Team1 and Team2 data
        for team_prefix in ['Team1', 'Team2']:
            team_data = year_rounds[[f'{team_prefix}_Code', f'{team_prefix}_Member1_Name', f'{team_prefix}_Member2_Name']].drop_duplicates()
            
            for _, row in team_data.iterrows():
                team_code = row[f'{team_prefix}_Code']
                member1 = row[f'{team_prefix}_Member1_Name']
                member2 = row[f'{team_prefix}_Member2_Name']
                
                if pd.notna(member1) and pd.notna(member2):
                    member1_variations = generate_name_variations(str(member1))
                    member2_variations = generate_name_variations(str(member2))
                    
                    # Create all combination keys
                    all_keys = set()
                    for m1_var in member1_variations:
                        for m2_var in member2_variations:
                            if m1_var and m2_var:
                                all_keys.add(f"{m1_var}|{m2_var}")
                                all_keys.add(f"{m2_var}|{m1_var}")
                    
                    if team_code not in year_mapping:
                        year_mapping[team_code] = list(all_keys)
        
        mapping[year] = year_mapping
    
    return mapping

def load_tournament_data(year: int, tournament_files_dir: str = "tournament_files") -> Dict[str, Any]:
    """Load tournament data for a specific year."""
    filename = f"tournaments_{year}.json"
    filepath = os.path.join(tournament_files_dir, filename)
    
    if not os.path.exists(filepath):
        return {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tournaments = json.load(f)
        
        tournament_dict = {}
        for tournament in tournaments:
            # Find Team Policy Debate population
            tp_population = None
            for event in tournament.get('events', []):
                if 'Team Policy Debate' in event.get('name', ''):
                    tp_population = int(event.get('population', 0))
                    break
            
            if tp_population:
                tournament_dict[tournament['name']] = {
                    'state': tournament.get('state', ''),
                    'population': tp_population,
                    'date': tournament.get('date', ''),
                    'url': tournament.get('url', '')
                }
        
        return tournament_dict
    except Exception as e:
        print(f"Error loading tournament file {filename}: {e}")
        return {}

def match_tournament_name(tournament_name: str, tournament_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find matching tournament using exact match first, then fuzzy matching."""
    # Try exact match first
    if tournament_name in tournament_data:
        return tournament_data[tournament_name]
    
    # Extract key words for fuzzy matching
    def extract_key_words(name):
        name = re.sub(r'\b(20\d{2}|tournament|invitational|classic|championship|forum|of|the|and|in|at)\b', '', name.lower())
        name = re.sub(r'[^\w\s]', ' ', name)
        return set(w.strip() for w in name.split() if len(w) > 2)
    
    tournament_key_words = extract_key_words(tournament_name)
    if not tournament_key_words:
        return None
    
    # Find best fuzzy match
    best_match = None
    best_score = 0
    
    for name, info in tournament_data.items():
        name_key_words = extract_key_words(name)
        if name_key_words:
            intersection = len(tournament_key_words & name_key_words)
            union = len(tournament_key_words | name_key_words)
            score = intersection / union if union > 0 else 0
            
            if score > best_score and score > 0.3:  # At least 30% similarity
                best_match = info
                best_score = score
    
    return best_match

def calculate_tournament_metrics(team_data: Dict[str, Any], tournament_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate tournament-based metrics for a team.""" 
    if not team_data or not team_data.get('tournaments'):
        return {'national_exposure': None, 'avg_tournament_size': None, 'tournament_points': None}
    
    states_visited = set()
    tournament_sizes = []
    total_tournament_points = 0
    
    for tournament in team_data.get('tournaments', []):
        tournament_name = tournament.get('name', '')
        place = tournament.get('place', '')
        
        tournament_info = match_tournament_name(tournament_name, tournament_data)
        
        if tournament_info:
            # Collect state for national exposure
            state = tournament_info.get('state', '')
            if state:
                states_visited.add(state)
            
            # Collect population for average tournament size
            population = tournament_info.get('population', 0)
            if population > 0:
                tournament_sizes.append(population)
                
                # Calculate tournament points (population / place)
                try:
                    place_num = int(place) if place and str(place).isdigit() else None
                    if place_num and place_num > 0:
                        total_tournament_points += population / place_num
                except (ValueError, ZeroDivisionError):
                    pass
    
    return {
        'national_exposure': len(states_visited) if states_visited else None,
        'avg_tournament_size': sum(tournament_sizes) / len(tournament_sizes) if tournament_sizes else None,
        'tournament_points': total_tournament_points if total_tournament_points > 0 else None
    }

def calculate_team_stats(team_data: Dict[str, Any], tournament_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Calculate team statistics from year data."""
    if not team_data:
        return {key: None for key in [
            'total_wins', 'total_losses', 'prelim_wins', 'prelim_losses', 'num_tournaments',
            'rank_points', 'national_rank', 'state_rank', 'win_rate', 'prelim_win_rate',
            'total_rounds', 'avg_points_per_tournament', 'national_exposure', 
            'avg_tournament_size', 'tournament_points'
        ]}
    
    # Extract basic stats
    total_wins = int(team_data.get('total_wins', 0))
    total_losses = int(team_data.get('total_losses', 0))
    prelim_wins = int(team_data.get('prelim_wins', 0))
    prelim_losses = int(team_data.get('prelim_losses', 0))
    rank_points = float(team_data.get('rank_points', 0))
    
    # Handle ranks
    national_rank = team_data.get('national_rank')
    state_rank = team_data.get('state_rank')
    national_rank = int(national_rank) if national_rank and str(national_rank).isdigit() else None
    state_rank = int(state_rank) if state_rank and str(state_rank).isdigit() else None
    
    # Calculate derived stats
    total_rounds = total_wins + total_losses
    prelim_rounds = prelim_wins + prelim_losses
    win_rate = total_wins / total_rounds if total_rounds > 0 else 0.0
    prelim_win_rate = prelim_wins / prelim_rounds if prelim_rounds > 0 else 0.0
    
    # Tournament statistics
    tournaments = team_data.get('tournaments', [])
    num_tournaments = len(tournaments)
    avg_points_per_tournament = None
    if tournaments:
        total_points = sum(float(t.get('points', 0)) for t in tournaments)
        avg_points_per_tournament = total_points / len(tournaments)
    
    # Calculate tournament metrics
    tournament_metrics = calculate_tournament_metrics(team_data, tournament_data) if tournament_data else {}
    
    return {
        'total_wins': total_wins,
        'total_losses': total_losses,
        'prelim_wins': prelim_wins,
        'prelim_losses': prelim_losses,
        'num_tournaments': num_tournaments,
        'rank_points': rank_points,
        'national_rank': national_rank,
        'state_rank': state_rank,
        'win_rate': win_rate,
        'prelim_win_rate': prelim_win_rate,
        'total_rounds': total_rounds,
        'avg_points_per_tournament': avg_points_per_tournament,
        **tournament_metrics
    }

def find_team_data(team_keys: List[str], year_teams: Dict[str, Any]) -> Dict[str, Any]:
    """Find team data by trying all possible key variations."""
    for key in team_keys:
        if key in year_teams:
            return year_teams[key]
    return {}

def join_rounds_with_team_data():
    """Main function to join rounds with team statistics."""
    print("Loading rounds data...")
    
    try:
        rounds_df = pd.read_csv("to_upload/matchup_model/rounds_extracted.csv")
        print(f"Loaded {len(rounds_df)} rounds")
    except Exception as e:
        print(f"Error loading rounds_extracted.csv: {e}")
        return
    
    # Create team mappings and load data for all years
    print("Creating team mapping and loading year data...")
    team_mapping = create_team_mapping_from_rounds(rounds_df)
    years = sorted(rounds_df['Year'].unique())
    print(f"Found years: {years}")
    
    year_data = {}
    tournament_data = {}
    for year in years:
        year_data[year] = load_year_file(year)
        tournament_data[year] = load_tournament_data(year)
        print(f"Loaded {len(year_data[year])} teams and {len(tournament_data[year])} tournaments for {year}")
    
    # Initialize new columns
    stat_columns = [
        'Total_Wins', 'Total_Losses', 'Prelim_Wins', 'Prelim_Losses', 'Num_Tournaments',
        'Rank_Points', 'National_Rank', 'State_Rank', 'Win_Rate', 'Prelim_Win_Rate',
        'Total_Rounds', 'Avg_Points_Per_Tournament', 'National_Exposure', 
        'Avg_Tournament_Size', 'Tournament_Points'
    ]
    
    for team in ['Team1', 'Team2']:
        for col in stat_columns:
            rounds_df[f'{team}_{col}'] = None
    
    # Process each round
    print("Processing rounds...")
    matches_found = 0
    
    for idx, row in rounds_df.iterrows():
        if idx % 1000 == 0:
            print(f"Processing round {idx + 1}/{len(rounds_df)}")
        
        year = row['Year']
        year_teams = year_data.get(year, {})
        year_tournaments = tournament_data.get(year, {})
        
        # Process both teams
        for team_num in [1, 2]:
            team_code = row[f'Team{team_num}_Code']
            team_keys = team_mapping.get(year, {}).get(team_code, [])
            
            team_data = find_team_data(team_keys, year_teams)
            team_stats = calculate_team_stats(team_data, year_tournaments)
            
            if team_data:
                matches_found += 1
            
            # Update dataframe with stats
            for col in stat_columns:
                stat_key = col.lower()
                rounds_df.at[idx, f'Team{team_num}_{col}'] = team_stats.get(stat_key)
    
    # Save results
    output_file = "to_upload/matchup_model/rounds_joined.csv"
    print(f"Saving joined data to {output_file}...")
    rounds_df.to_csv(output_file, index=False)
    print(f"Successfully saved {len(rounds_df)} rounds with team statistics")
    
    # Print summary
    print(f"\nSummary: {len(rounds_df)} rounds processed, {matches_found} team matches found")
    missing_team1 = rounds_df['Team1_Total_Rounds'].isna().sum()
    missing_team2 = rounds_df['Team2_Total_Rounds'].isna().sum()
    print(f"Missing data: Team1={missing_team1}, Team2={missing_team2}")

if __name__ == "__main__":
    join_rounds_with_team_data() 