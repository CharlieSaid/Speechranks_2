#!/usr/bin/env python3
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

class NameNormalizer:
    """
    Flexible name normalization system that applies configurable transformations.
    This replaces hard-coded normalization rules with a data-driven approach.
    """
    
    def __init__(self, config_file: str = "name_normalization_config.json"):
        # Load configuration from file
        self.config = self._load_config(config_file)
        
        # Set up transformation rules based on config
        self.transformation_rules = []
        if self.config.get('transformation_settings', {}).get('enable_whitespace_normalization', True):
            self.transformation_rules.append(('whitespace_normalization', self._normalize_whitespace))
        if self.config.get('transformation_settings', {}).get('enable_case_normalization', True):
            self.transformation_rules.append(('case_normalization', self._normalize_case))
        if self.config.get('transformation_settings', {}).get('enable_surname_prefix_normalization', True):
            self.transformation_rules.append(('surname_prefix_normalization', self._normalize_surname_prefixes))
        if self.config.get('transformation_settings', {}).get('enable_punctuation_normalization', True):
            self.transformation_rules.append(('punctuation_normalization', self._normalize_punctuation))
        if self.config.get('transformation_settings', {}).get('enable_unicode_normalization', True):
            self.transformation_rules.append(('unicode_normalization', self._normalize_unicode))
        
        # Load mappings from config
        self.surname_prefixes = self.config.get('surname_prefixes', {}).get('rules', {})
        self.punctuation_replacements = self.config.get('punctuation_replacements', {}).get('rules', {})
        self.unicode_map = self.config.get('unicode_replacements', {}).get('rules', {})
    
    def _load_config(self, config_file: str) -> dict:
        """Load configuration from JSON file with fallback to defaults."""
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"Config file {config_file} not found, using defaults")
        except Exception as e:
            print(f"Error loading config file {config_file}: {e}, using defaults")
        
        # Fallback to minimal defaults if config file fails
        return {
            "surname_prefixes": {"rules": {"de la": "dela", "van der": "vander", "mac": "mc"}},
            "punctuation_replacements": {"rules": {"'": "", "-": "", ".": ""}},
            "unicode_replacements": {"rules": {"ñ": "n", "ç": "c"}},
            "transformation_settings": {
                "enable_case_normalization": True,
                "enable_whitespace_normalization": True,
                "enable_surname_prefix_normalization": True,
                "enable_punctuation_normalization": True,
                "enable_unicode_normalization": True,
                "enable_space_removal_variation": True,
                "enable_initials_variation": True,
                "enable_case_preserved_variation": True
            }
        }
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace: strip, collapse multiple spaces to single space."""
        return ' '.join(text.split())
    
    def _normalize_case(self, text: str) -> str:
        """Convert to lowercase for case-insensitive matching."""
        return text.lower()
    
    def _normalize_surname_prefixes(self, text: str) -> str:
        """Normalize common surname prefixes using configurable rules."""
        normalized = text
        for original, replacement in self.surname_prefixes.items():
            # Handle prefix at start, middle, or end of string
            patterns = [
                f' {original} ',  # middle: " de la "
                f' {original}',   # end: " de la"
                f'{original} ',   # start: "de la "
            ]
            for pattern in patterns:
                normalized = normalized.replace(pattern, f' {replacement}')
        return normalized
    
    def _normalize_punctuation(self, text: str) -> str:
        """Remove or replace punctuation marks."""
        normalized = text
        for char, replacement in self.punctuation_replacements.items():
            normalized = normalized.replace(char, replacement)
        return normalized
    
    def _normalize_unicode(self, text: str) -> str:
        """Normalize unicode characters to ASCII equivalents."""
        normalized = text
        for unicode_char, ascii_char in self.unicode_map.items():
            normalized = normalized.replace(unicode_char, ascii_char)
            normalized = normalized.replace(unicode_char.upper(), ascii_char.upper())
        return normalized
    
    def normalize(self, name: str) -> str:
        """
        Apply all normalization transformations to a name.
        
        Args:
            name: The name to normalize
            
        Returns:
            Normalized name string
        """
        if not name:
            return ""
        
        normalized = str(name).strip()
        
        # Apply each transformation rule in order
        for rule_name, transform_func in self.transformation_rules:
            try:
                normalized = transform_func(normalized)
            except Exception as e:
                print(f"Warning: Normalization rule '{rule_name}' failed for '{name}': {e}")
                continue
        
        return normalized
    
    def generate_name_variations(self, name: str) -> List[str]:
        """
        Generate multiple variations of a name for matching.
        
        Args:
            name: The original name
            
        Returns:
            List of name variations including original, normalized, space-removed, etc.
        """
        if not name:
            return [""]
        
        variations = set()
        original = str(name).strip()
        settings = self.config.get('transformation_settings', {})
        
        # Add original
        variations.add(original)
        
        # Add normalized version
        normalized = self.normalize(original)
        variations.add(normalized)
        
        # Add space-collapsed version (configurable)
        if settings.get('enable_space_removal_variation', True):
            no_spaces = normalized.replace(' ', '')
            variations.add(no_spaces)
        
        # Add version with spaces normalized but case preserved (configurable)
        if settings.get('enable_case_preserved_variation', True):
            case_preserved = self._normalize_whitespace(original)
            variations.add(case_preserved)
        
        # Add initials variation (configurable)
        if settings.get('enable_initials_variation', True):
            parts = normalized.split()
            if len(parts) >= 2:
                # First initial + last name
                variations.add(f"{parts[0][0]} {parts[-1]}")
                # First name + last initial
                variations.add(f"{parts[0]} {parts[-1][0]}")
        
        return list(variations)
    
    def add_custom_rule(self, rule_type: str, original: str, replacement: str):
        """
        Add a custom normalization rule at runtime.
        
        Args:
            rule_type: Type of rule ('surname_prefixes', 'punctuation_replacements', 'unicode_replacements')
            original: The original text to match
            replacement: The replacement text
        """
        if rule_type == 'surname_prefixes':
            self.surname_prefixes[original] = replacement
        elif rule_type == 'punctuation_replacements':
            self.punctuation_replacements[original] = replacement
        elif rule_type == 'unicode_replacements':
            self.unicode_map[original] = replacement
        else:
            print(f"Unknown rule type: {rule_type}")
    
    def save_config(self, config_file: str = "name_normalization_config.json"):
        """Save current configuration to file."""
        config_to_save = {
            "surname_prefixes": {"comment": "Map complex surname prefixes to simplified versions", "rules": self.surname_prefixes},
            "punctuation_replacements": {"comment": "Characters to remove or replace", "rules": self.punctuation_replacements},
            "unicode_replacements": {"comment": "Map accented characters to ASCII equivalents", "rules": self.unicode_map},
            "transformation_settings": self.config.get('transformation_settings', {})
        }
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
            print(f"Configuration saved to {config_file}")
        except Exception as e:
            print(f"Error saving configuration: {e}")

# Global normalizer instance
name_normalizer = NameNormalizer()

def normalize_name(name):
    """
    Legacy function wrapper for backwards compatibility.
    Now uses the flexible NameNormalizer class.
    """
    return name_normalizer.normalize(name)

def load_year_file(year: int, year_files_dir: str = "to_upload/year_files") -> Dict[str, Any]:
    """Load the JSON data for a specific year and create comprehensive mapping."""
    filename = f"debate_teams_{year}.json"
    filepath = os.path.join(year_files_dir, filename)
    
    if not os.path.exists(filepath):
        print(f"Warning: Year file {filename} not found")
        return {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create mapping with multiple key variations using the new normalizer
        team_dict = {}
        for team in data:
            debater1_name = team.get('debater1', {}).get('name', '')
            debater2_name = team.get('debater2', {}).get('name', '')
            
            if debater1_name and debater2_name:
                # Generate all variations for both debaters
                debater1_variations = name_normalizer.generate_name_variations(debater1_name)
                debater2_variations = name_normalizer.generate_name_variations(debater2_name)
                
                # Create keys for all combinations of variations in both orders
                for d1_var in debater1_variations:
                    for d2_var in debater2_variations:
                        if d1_var and d2_var:  # Skip empty variations
                            # Both orders
                            key1 = f"{d1_var}|{d2_var}"
                            key2 = f"{d2_var}|{d1_var}"
                            team_dict[key1] = team
                            team_dict[key2] = team
                
        return team_dict
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return {}

def create_team_key(team_data: Dict[str, Any]) -> str:
    """Create a standardized team key from team data."""
    debater1_name = team_data.get('debater1', {}).get('name', '')
    debater2_name = team_data.get('debater2', {}).get('name', '')
    
    # Sort names to ensure consistent key regardless of order
    names = sorted([debater1_name, debater2_name])
    return f"{names[0]}|{names[1]}"

def create_team_mapping_from_rounds(rounds_df: pd.DataFrame) -> Dict[str, Dict[str, List[str]]]:
    """Create year-specific team code to member names mapping from rounds data with multiple variations."""
    mapping = {}
    
    # Group by year to create year-specific mappings
    for year in rounds_df['Year'].unique():
        year_rounds = rounds_df[rounds_df['Year'] == year]
        year_mapping = {}
        
        # Process Team1 mappings for this year
        team1_data = year_rounds[['Team1_Code', 'Team1_Member1_Name', 'Team1_Member2_Name']].drop_duplicates()
        for _, row in team1_data.iterrows():
            team_code = row['Team1_Code']
            member1 = row['Team1_Member1_Name']
            member2 = row['Team1_Member2_Name']
            
            if pd.notna(member1) and pd.notna(member2):
                member1_str = str(member1).strip()
                member2_str = str(member2).strip()
                
                # Generate all name variations for both members
                member1_variations = name_normalizer.generate_name_variations(member1_str)
                member2_variations = name_normalizer.generate_name_variations(member2_str)
                
                # Create keys for all combinations in both orders
                all_keys = set()
                for m1_var in member1_variations:
                    for m2_var in member2_variations:
                        if m1_var and m2_var:  # Skip empty variations
                            all_keys.add(f"{m1_var}|{m2_var}")
                            all_keys.add(f"{m2_var}|{m1_var}")
                
                year_mapping[team_code] = list(all_keys)
        
        # Process Team2 mappings for this year
        team2_data = year_rounds[['Team2_Code', 'Team2_Member1_Name', 'Team2_Member2_Name']].drop_duplicates()
        for _, row in team2_data.iterrows():
            team_code = row['Team2_Code']
            member1 = row['Team2_Member1_Name']
            member2 = row['Team2_Member2_Name']
            
            if pd.notna(member1) and pd.notna(member2):
                member1_str = str(member1).strip()
                member2_str = str(member2).strip()
                
                # Generate all name variations for both members
                member1_variations = name_normalizer.generate_name_variations(member1_str)
                member2_variations = name_normalizer.generate_name_variations(member2_str)
                
                # Create keys for all combinations in both orders
                all_keys = set()
                for m1_var in member1_variations:
                    for m2_var in member2_variations:
                        if m1_var and m2_var:  # Skip empty variations
                            all_keys.add(f"{m1_var}|{m2_var}")
                            all_keys.add(f"{m2_var}|{m1_var}")
                
                # Only add if not already present (avoid duplicates)
                if team_code not in year_mapping:
                    year_mapping[team_code] = list(all_keys)
        
        mapping[year] = year_mapping
    
    return mapping

def find_team_data(team_keys: List[str], year_teams: Dict[str, Any]) -> Dict[str, Any]:
    """Find team data by trying all possible key variations."""
    for key in team_keys:
        if key in year_teams:
            return year_teams[key]
    return {}

def calculate_team_stats(team_data: Dict[str, Any], tournament_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Calculate team statistics from year data including tournament metrics."""
    stats = {
        'total_wins': None,
        'total_losses': None,
        'prelim_wins': None,
        'prelim_losses': None,
        'num_tournaments': None,
        'rank_points': None,
        'national_rank': None,
        'state_rank': None,
        'win_rate': None,
        'prelim_win_rate': None,
        'total_rounds': None,
        'avg_points_per_tournament': None,
        'national_exposure': None,
        'avg_tournament_size': None,
        'tournament_points': None
    }
    
    if not team_data:
        return stats
    
    # Extract basic stats
    stats['total_wins'] = int(team_data.get('total_wins', 0))
    stats['total_losses'] = int(team_data.get('total_losses', 0))
    stats['prelim_wins'] = int(team_data.get('prelim_wins', 0))
    stats['prelim_losses'] = int(team_data.get('prelim_losses', 0))
    stats['rank_points'] = float(team_data.get('rank_points', 0))
    
    # Handle ranks (could be None or string)
    national_rank = team_data.get('national_rank')
    state_rank = team_data.get('state_rank')
    stats['national_rank'] = int(national_rank) if national_rank and str(national_rank).isdigit() else None
    stats['state_rank'] = int(state_rank) if state_rank and str(state_rank).isdigit() else None
    
    # Calculate derived stats
    total_rounds = stats['total_wins'] + stats['total_losses']
    prelim_rounds = stats['prelim_wins'] + stats['prelim_losses']
    
    stats['total_rounds'] = total_rounds
    stats['win_rate'] = stats['total_wins'] / total_rounds if total_rounds > 0 else 0.0
    stats['prelim_win_rate'] = stats['prelim_wins'] / prelim_rounds if prelim_rounds > 0 else 0.0
    
    # Tournament statistics
    tournaments = team_data.get('tournaments', [])
    stats['num_tournaments'] = len(tournaments)
    
    if tournaments:
        total_points = sum(float(t.get('points', 0)) for t in tournaments)
        stats['avg_points_per_tournament'] = total_points / len(tournaments)
    else:
        stats['avg_points_per_tournament'] = None
    
    # Calculate new tournament metrics if tournament data is available
    if tournament_data:
        tournament_metrics = calculate_tournament_metrics(team_data, tournament_data)
        stats.update(tournament_metrics)
    
    return stats

def load_tournament_data(year: int, tournament_files_dir: str = "tournament_files") -> Dict[str, Any]:
    """Load tournament data for a specific year."""
    filename = f"tournaments_{year}.json"
    filepath = os.path.join(tournament_files_dir, filename)
    
    if not os.path.exists(filepath):
        print(f"Warning: Tournament file {filename} not found")
        return {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tournaments = json.load(f)
        
        # Create a mapping from tournament name to tournament data
        tournament_dict = {}
        for tournament in tournaments:
            # Extract Team Policy Debate population
            tp_population = None
            for event in tournament.get('events', []):
                if 'Team Policy Debate' in event.get('name', ''):
                    tp_population = int(event.get('population', 0))
                    break
            
            # Only include tournaments that have Team Policy Debate
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

def calculate_tournament_metrics(team_data: Dict[str, Any], tournament_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate tournament-based metrics for a team.
    
    Args:
        team_data: Team data from year files
        tournament_data: Tournament data for the year
        
    Returns:
        Dictionary with national_exposure, avg_tournament_size, and tournament_points
    """
    # Global counter for debugging
    if not hasattr(calculate_tournament_metrics, 'debug_count'):
        calculate_tournament_metrics.debug_count = 0
    
    if not team_data or not team_data.get('tournaments'):
        return {
            'national_exposure': None,
            'avg_tournament_size': None,
            'tournament_points': None
        }
    
    states_visited = set()
    tournament_sizes = []
    total_tournament_points = 0
    matched_tournaments = 0
    
    # Debug output for first 5 teams
    is_debug = calculate_tournament_metrics.debug_count < 5
    if is_debug:
        calculate_tournament_metrics.debug_count += 1
        print(f"\n=== DEBUG TEAM #{calculate_tournament_metrics.debug_count} ===")
        print(f"Team: {team_data.get('debater1', {}).get('name', 'Unknown')} & {team_data.get('debater2', {}).get('name', 'Unknown')}")
        print(f"Year: {team_data.get('year', 'Unknown')}")
        print(f"Team JSON data:")
        import json
        print(json.dumps(team_data, indent=2)[:1000] + "..." if len(json.dumps(team_data)) > 1000 else json.dumps(team_data, indent=2))
        print(f"\nAvailable tournament data keys (first 5): {list(tournament_data.keys())[:5]}")
        print(f"Total tournaments in data: {len(tournament_data)}")
        print(f"\nProcessing {len(team_data.get('tournaments', []))} tournaments for this team:")
    
    for i, tournament in enumerate(team_data.get('tournaments', [])):
        tournament_name = tournament.get('name', '')
        place = tournament.get('place', '')
        
        if is_debug:
            print(f"\n  Tournament {i+1}: '{tournament_name}' (Place: {place})")
        
        # Find matching tournament in tournament data with flexible matching
        tournament_info = None
        
        # First try exact match
        for name, info in tournament_data.items():
            if tournament_name == name:
                tournament_info = info
                if is_debug:
                    print(f"    ✓ Exact match found: '{name}'")
                break
        
        # If no exact match, try flexible matching
        if not tournament_info:
            # Extract key words from tournament name (remove common words)
            def extract_key_words(name):
                # Remove year, common words, and normalize
                import re
                name = re.sub(r'\b(20\d{2}|tournament|invitational|classic|championship|forum|of|the|and|in|at)\b', '', name.lower())
                name = re.sub(r'[^\w\s]', ' ', name)  # Remove punctuation
                words = [w.strip() for w in name.split() if len(w) > 2]  # Remove short words
                return set(words)
            
            tournament_key_words = extract_key_words(tournament_name)
            
            if is_debug:
                print(f"    Key words from '{tournament_name}': {tournament_key_words}")
            
            # Try to match by key words overlap
            best_match = None
            best_score = 0
            best_match_name = ""
            
            for name, info in tournament_data.items():
                name_key_words = extract_key_words(name)
                
                if tournament_key_words and name_key_words:
                    # Calculate Jaccard similarity (intersection over union)
                    intersection = len(tournament_key_words & name_key_words)
                    union = len(tournament_key_words | name_key_words)
                    score = intersection / union if union > 0 else 0
                    
                    # Also give bonus if any exact word matches
                    if intersection > 0 and score > best_score and score > 0.3:  # At least 30% similarity
                        best_match = info
                        best_score = score
                        best_match_name = name
            
            tournament_info = best_match
            if is_debug and tournament_info:
                print(f"    ✓ Fuzzy match found: '{best_match_name}' (score: {best_score:.2f})")
                print(f"      Match data: {tournament_info}")
            elif is_debug:
                print(f"    ✗ No match found")
        
        if tournament_info:
            matched_tournaments += 1
            
            # National Exposure: collect unique states
            state = tournament_info.get('state', '')
            if state:
                states_visited.add(state)
                if is_debug:
                    print(f"      State: {state}")
            
            # Average Tournament Size: collect population sizes
            population = tournament_info.get('population', 0)
            if population > 0:
                tournament_sizes.append(population)
                if is_debug:
                    print(f"      Population: {population}")
                
                # Tournament Points: population / place
                try:
                    place_num = int(place) if place and str(place).isdigit() else None
                    if place_num and place_num > 0:
                        tournament_points = population / place_num
                        total_tournament_points += tournament_points
                        if is_debug:
                            print(f"      Tournament points: {population}/{place_num} = {tournament_points:.2f}")
                    elif is_debug:
                        print(f"      Invalid place: '{place}'")
                except (ValueError, ZeroDivisionError) as e:
                    if is_debug:
                        print(f"      Error calculating points: {e}")
    
    # Calculate final metrics
    national_exposure = len(states_visited) if states_visited else None
    avg_tournament_size = sum(tournament_sizes) / len(tournament_sizes) if tournament_sizes else None
    tournament_points = total_tournament_points if total_tournament_points > 0 else None
    
    if is_debug:
        print(f"\n  FINAL METRICS:")
        print(f"  - National Exposure: {national_exposure} states")
        print(f"  - Average Tournament Size: {avg_tournament_size}")
        print(f"  - Tournament Points: {tournament_points}")
        print(f"  - Matched tournaments: {matched_tournaments}/{len(team_data.get('tournaments', []))}")
        print("=" * 50)
    
    # Debug: print matching rate for first few teams
    total_tournaments = len(team_data.get('tournaments', []))
    if total_tournaments > 0:
        match_rate = matched_tournaments / total_tournaments
        # Uncomment the line below to see matching details for debugging
        # print(f"Tournament matching: {matched_tournaments}/{total_tournaments} ({match_rate:.2%})")
    
    return {
        'national_exposure': national_exposure,
        'avg_tournament_size': avg_tournament_size,
        'tournament_points': tournament_points
    }

def join_rounds_with_team_data():
    """Main function to join rounds with team statistics."""
    print("Loading rounds data...")
    
    # Load rounds data
    try:
        rounds_df = pd.read_csv("to_upload/matchup_model/rounds_extracted.csv")
        print(f"Loaded {len(rounds_df)} rounds")
    except Exception as e:
        print(f"Error loading rounds_extracted.csv: {e}")
        return
    
    # Create team mapping from rounds data
    print("Creating team mapping from rounds data...")
    team_mapping = create_team_mapping_from_rounds(rounds_df)
    
    # Calculate total mappings across all years
    total_mappings = sum(len(year_mapping) for year_mapping in team_mapping.values())
    print(f"Created {total_mappings} team mappings across {len(team_mapping)} years")
    
    # Get unique years from rounds data
    years = sorted(rounds_df['Year'].unique())
    print(f"Found years: {years}")
    
    # Load year data for all years
    year_data = {}
    tournament_data = {}
    for year in years:
        print(f"Loading year {year}...")
        year_data[year] = load_year_file(year)
        print(f"Loaded {len(year_data[year])} teams for {year}")
        
        print(f"Loading tournament data for {year}...")
        tournament_data[year] = load_tournament_data(year)
        print(f"Loaded {len(tournament_data[year])} tournaments for {year}")
    
    # Initialize new columns for team statistics
    team1_cols = [
        'Team1_Total_Wins', 'Team1_Total_Losses', 'Team1_Prelim_Wins', 'Team1_Prelim_Losses',
        'Team1_Num_Tournaments', 'Team1_Rank_Points', 'Team1_National_Rank', 'Team1_State_Rank',
        'Team1_Win_Rate', 'Team1_Prelim_Win_Rate', 'Team1_Total_Rounds', 'Team1_Avg_Points_Per_Tournament',
        'Team1_National_Exposure', 'Team1_Avg_Tournament_Size', 'Team1_Tournament_Points'
    ]
    
    team2_cols = [
        'Team2_Total_Wins', 'Team2_Total_Losses', 'Team2_Prelim_Wins', 'Team2_Prelim_Losses',
        'Team2_Num_Tournaments', 'Team2_Rank_Points', 'Team2_National_Rank', 'Team2_State_Rank',
        'Team2_Win_Rate', 'Team2_Prelim_Win_Rate', 'Team2_Total_Rounds', 'Team2_Avg_Points_Per_Tournament',
        'Team2_National_Exposure', 'Team2_Avg_Tournament_Size', 'Team2_Tournament_Points'
    ]
    
    # Initialize columns with default values
    for col in team1_cols + team2_cols:
        rounds_df[col] = None
    
    # Process each round
    print("Processing rounds...")
    matches_found = 0
    for idx, row in rounds_df.iterrows():
        if idx % 100 == 0:
            print(f"Processing round {idx + 1}/{len(rounds_df)}")
        
        year = row['Year']
        team1_code = row['Team1_Code']
        team2_code = row['Team2_Code']
        
        # Get team keys from mapping
        team1_keys = team_mapping.get(year, {}).get(team1_code, [])
        team2_keys = team_mapping.get(year, {}).get(team2_code, [])
        
        # Get year data and tournament data for this year
        year_teams = year_data.get(year, {})
        year_tournaments = tournament_data.get(year, {})
        
        # Get team data and calculate stats for Team 1
        team1_data = find_team_data(team1_keys, year_teams)
        team1_stats = calculate_team_stats(team1_data, year_tournaments)
        if team1_data:
            matches_found += 1
        
        # Get team data and calculate stats for Team 2
        team2_data = find_team_data(team2_keys, year_teams)
        team2_stats = calculate_team_stats(team2_data, year_tournaments)
        if team2_data:
            matches_found += 1
        
        # Update dataframe with Team 1 stats
        for i, col in enumerate(team1_cols):
            stat_key = col.replace('Team1_', '').lower()
            rounds_df.at[idx, col] = team1_stats.get(stat_key)
        
        # Update dataframe with Team 2 stats
        for i, col in enumerate(team2_cols):
            stat_key = col.replace('Team2_', '').lower()
            rounds_df.at[idx, col] = team2_stats.get(stat_key)
    
    # Save the joined data
    output_file = "to_upload/matchup_model/rounds_joined.csv"
    print(f"Saving joined data to {output_file}...")
    rounds_df.to_csv(output_file, index=False)
    print(f"Successfully saved {len(rounds_df)} rounds with team statistics to {output_file}")
    
    # Print summary statistics
    print("\n=== Summary Statistics ===")
    print(f"Total rounds processed: {len(rounds_df)}")
    print(f"Years covered: {min(years)} - {max(years)}")
    print(f"Team matches found: {matches_found}")
    
    # Check for missing data
    missing_team1 = rounds_df['Team1_Total_Rounds'].isna().sum()
    missing_team2 = rounds_df['Team2_Total_Rounds'].isna().sum()
    print(f"Rounds with missing Team 1 data: {missing_team1}")
    print(f"Rounds with missing Team 2 data: {missing_team2}")
    
    if missing_team1 > 0 or missing_team2 > 0:
        print("\nSample of rounds with missing data:")
        missing_mask = rounds_df['Team1_Total_Rounds'].isna() | rounds_df['Team2_Total_Rounds'].isna()
        sample_missing = rounds_df[missing_mask][['Team1_Code', 'Team2_Code', 'Year', 'Team1_Member1_Name', 'Team1_Member2_Name', 'Team2_Member1_Name', 'Team2_Member2_Name']]#.head()
        print(sample_missing.to_string(index=False))
        
        # Debug: Show some team mapping examples
        # print("\nSample team mappings:")
        # for year_idx, (year, mapping) in enumerate(list(team_mapping.items())[:2]):  # Show first 2 years
        #     print(f"  Year {year}:")
        #     for team_idx, (code, keys) in enumerate(list(mapping.items())[:3]):  # Show first 3 teams per year
        #         print(f"    {code}: {keys}")
        #     if team_idx >= 2:  # If there are more teams, indicate it
        #         remaining = len(mapping) - 3
        #         if remaining > 0:
        #             print(f"    ... and {remaining} more teams")
        
        # # Debug: Show some year data examples for 2018
        # if 2018 in year_data:
        #     print(f"\nSample year data keys for 2018 (first 5):")
        #     sample_keys = list(year_data[2018].keys())[:5]
        #     for key in sample_keys:
        #         print(f"  {key}")

if __name__ == "__main__":
    join_rounds_with_team_data() 