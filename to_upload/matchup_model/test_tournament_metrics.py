#!/usr/bin/env python3
"""
Test script to debug tournament metrics calculation for a few teams.
"""

import pandas as pd
import json
import os
import re
from typing import Dict, List, Any, Optional

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

def calculate_tournament_metrics_debug(team_data: Dict[str, Any], tournament_data: Dict[str, Any], team_num: int) -> Dict[str, Any]:
    """
    Debug version of calculate_tournament_metrics that shows detailed output.
    """
    print(f"\n=== DEBUG TEAM #{team_num} ===")
    print(f"Team: {team_data.get('debater1', {}).get('name', 'Unknown')} & {team_data.get('debater2', {}).get('name', 'Unknown')}")
    print(f"Year: {team_data.get('year', 'Unknown')}")
    print(f"Team JSON data:")
    print(json.dumps(team_data, indent=2)[:1500] + "..." if len(json.dumps(team_data)) > 1500 else json.dumps(team_data, indent=2))
    print(f"\nAvailable tournament data keys (first 5): {list(tournament_data.keys())[:5]}")
    print(f"Total tournaments in data: {len(tournament_data)}")
    print(f"\nProcessing {len(team_data.get('tournaments', []))} tournaments for this team:")
    
    if not team_data or not team_data.get('tournaments'):
        print("No tournaments found for this team!")
        return {
            'national_exposure': None,
            'avg_tournament_size': None,
            'tournament_points': None
        }
    
    states_visited = set()
    tournament_sizes = []
    total_tournament_points = 0
    matched_tournaments = 0
    
    for i, tournament in enumerate(team_data.get('tournaments', [])):
        tournament_name = tournament.get('name', '')
        place = tournament.get('place', '')
        
        print(f"\n  Tournament {i+1}: '{tournament_name}' (Place: {place})")
        
        # Find matching tournament in tournament data with flexible matching
        tournament_info = None
        
        # First try exact match
        for name, info in tournament_data.items():
            if tournament_name == name:
                tournament_info = info
                print(f"    ✓ Exact match found: '{name}'")
                break
        
        # If no exact match, try flexible matching
        if not tournament_info:
            # Extract key words from tournament name (remove common words)
            def extract_key_words(name):
                # Remove year, common words, and normalize
                name = re.sub(r'\b(20\d{2}|tournament|invitational|classic|championship|forum|of|the|and|in|at)\b', '', name.lower())
                name = re.sub(r'[^\w\s]', ' ', name)  # Remove punctuation
                words = [w.strip() for w in name.split() if len(w) > 2]  # Remove short words
                return set(words)
            
            tournament_key_words = extract_key_words(tournament_name)
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
            if tournament_info:
                print(f"    ✓ Fuzzy match found: '{best_match_name}' (score: {best_score:.2f})")
                print(f"      Match data: {tournament_info}")
            else:
                print(f"    ✗ No match found")
        
        if tournament_info:
            matched_tournaments += 1
            
            # National Exposure: collect unique states
            state = tournament_info.get('state', '')
            if state:
                states_visited.add(state)
                print(f"      State: {state}")
            
            # Average Tournament Size: collect population sizes
            population = tournament_info.get('population', 0)
            if population > 0:
                tournament_sizes.append(population)
                print(f"      Population: {population}")
                
                # Tournament Points: population / place
                try:
                    place_num = int(place) if place and str(place).isdigit() else None
                    if place_num and place_num > 0:
                        tournament_points = population / place_num
                        total_tournament_points += tournament_points
                        print(f"      Tournament points: {population}/{place_num} = {tournament_points:.2f}")
                    else:
                        print(f"      Invalid place: '{place}'")
                except (ValueError, ZeroDivisionError) as e:
                    print(f"      Error calculating points: {e}")
    
    # Calculate final metrics
    national_exposure = len(states_visited) if states_visited else None
    avg_tournament_size = sum(tournament_sizes) / len(tournament_sizes) if tournament_sizes else None
    tournament_points = total_tournament_points if total_tournament_points > 0 else None
    
    print(f"\n  FINAL METRICS:")
    print(f"  - National Exposure: {national_exposure} states")
    print(f"  - Average Tournament Size: {avg_tournament_size}")
    print(f"  - Tournament Points: {tournament_points}")
    print(f"  - Matched tournaments: {matched_tournaments}/{len(team_data.get('tournaments', []))}")
    print("=" * 50)
    
    return {
        'national_exposure': national_exposure,
        'avg_tournament_size': avg_tournament_size,
        'tournament_points': tournament_points
    }

def test_tournament_metrics():
    """Test tournament metrics calculation for a few teams."""
    print("Loading year data for 2018...")
    
    # Load year file
    year_file_path = "to_upload/year_files/debate_teams_2018.json"
    if not os.path.exists(year_file_path):
        print(f"Error: {year_file_path} not found")
        return
    
    with open(year_file_path, 'r', encoding='utf-8') as f:
        year_data = json.load(f)
    
    print(f"Loaded {len(year_data)} teams from year file")
    
    # Load tournament data
    print("Loading tournament data for 2018...")
    tournament_data = load_tournament_data(2018)
    print(f"Loaded {len(tournament_data)} tournaments")
    
    # Test with first 3 teams that have tournaments
    teams_tested = 0
    for i, team in enumerate(year_data):
        if team.get('tournaments') and len(team.get('tournaments', [])) > 0:
            teams_tested += 1
            metrics = calculate_tournament_metrics_debug(team, tournament_data, teams_tested)
            
            if teams_tested >= 3:  # Test only 3 teams
                break
    
    print(f"\nTested {teams_tested} teams")

if __name__ == "__main__":
    test_tournament_metrics() 