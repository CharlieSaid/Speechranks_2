import numpy as np
import pandas as pd
import re
import os
import fitz  # PyMuPDF

def extract_rounds_from_text(text, filename=None):
    """
    Extract debate round results from the cumulative text file using a team-experience-based approach.
    
    Strategy:
    1. Extract year from filename (first 4 characters) if provided, otherwise fall back to page break lines
    2. Split text by team experiences (ending with " - " pattern between two integers)
    3. Remove page break lines from each team experience
    4. Parse each team experience individually:
       - Line 1: Team Member 1 name
       - Line 2: Team code (first word) + organization
       - Line 3: Team Member 2 name
       - Remaining lines: Round data (speaker points, opponent, side, result)
    """
    
    def is_page_break_line(line):
        """Check if line is a page break header"""
        page_break_indicators = ["Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", 
                               "Monday", "Page", "Team Policy", "Preliminary Round Results"]
        
        # Check for standard page break indicators
        if any(indicator in line for indicator in page_break_indicators):
            return True
            
        # Check if line contains a 4-digit year (20XX) - this indicates it's a page break line
        if re.search(r'\b(20\d{2})\b', line):
            return True
            
        return False
    
    def extract_year_from_filename(filename):
        """Extract year from filename (first 4 characters)"""
        if filename and len(filename) >= 4:
            try:
                year_str = filename[:4]
                # Validate that it's a reasonable year (20XX)
                if year_str.startswith('20') and year_str.isdigit():
                    return year_str
            except:
                pass
        return None
    
    def extract_tournament_info_from_text(text):
        """Extract tournament name and year from page break lines in the text"""
        lines = text.split('\n')
        year = None
        tournament_name = None
        
        # First pass: look for year in any page break line
        for line in lines:
            line = line.strip()
            if is_page_break_line(line):
                # Look for 4-digit year in the line
                year_match = re.search(r'\b(20\d{2})\b', line)
                if year_match:
                    year = year_match.group(1)
                    # Check if this line also has tournament name (everything else in the line)
                    potential_tournament = line.replace(year, '').strip()
                    # If there's meaningful text besides the year, use it as tournament name
                    if potential_tournament and not any(day in potential_tournament for day in 
                                                      ["Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Monday"]):
                        tournament_name = potential_tournament
                    break
        
        # Second pass: if we didn't find tournament name with year, look for it separately
        if year and not tournament_name:
            for line in lines:
                line = line.strip()
                if is_page_break_line(line):
                    # Skip lines that contain year or day of week
                    if (not re.search(r'\b(20\d{2})\b', line) and 
                        not any(day in line for day in ["Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Monday"]) and
                        not any(indicator in line for indicator in ["Page", "Team Policy", "Preliminary Round Results"]) and
                        len(line.strip()) > 0):
                        tournament_name = line.strip()
                        break
        
        # If we still don't have tournament name, use a default
        if not tournament_name:
            tournament_name = "Unknown Tournament"
            
        return tournament_name, year
    
    # Extract year from filename first (preferred method)
    year = extract_year_from_filename(filename)
    
    # Extract tournament info from the text
    tournament_name, fallback_year = extract_tournament_info_from_text(text)
    
    # Use filename year if available, otherwise fall back to text year
    if year:
        print(f"Using year from filename: {year}")
    else:
        year = fallback_year
        print(f"Using year from text content: {year}")
        
    if year:
        print(f"Detected tournament: {tournament_name} ({year})")
    else:
        print("No tournament info detected")
        tournament_name = "Unknown Tournament"
        year = "Unknown"
    
    def split_by_team_experiences(text):
        """
        Split text into individual team experiences.
        Each team experience ends with a summary line like "2 - 4" (wins - losses).
        """
        lines = text.split('\n')
        team_experiences = []
        current_team = []
        
        for line in lines:
            line = line.strip()
            current_team.append(line)
            
            # Check if this line is a team summary (ONLY " - " between two integers, nothing else)
            if re.match(r'^\d+\s*-\s*\d+$', line.strip()):
                team_experiences.append(current_team)
                current_team = []
        
        # Add any remaining lines as the last team (in case file doesn't end with summary)
        if current_team != []:
            team_experiences.append(current_team)
            
        return team_experiences
    
    def clean_team_experience(team_lines):
        """
        Remove page break lines and empty lines from a team experience.
        """
        cleaned = []
        for line in team_lines:
            if line and not is_page_break_line(line):
                cleaned.append(line)
        return cleaned
    
    def split_team_into_round_experiences(team_lines):
        """
        Split a team experience into individual round experiences.
        Each round experience ends with W, L, BYE, or FORFEIT.
        """
        
        # Since sometimes, page header info and page break info mix together with team_info,
        # we need to identify the team info by identifying the first round experience and working backwards.
        # We know that the first round experience ends with W, L, BYE, or FORFEIT.
        # If the first round experience is a W or L, then there are 6 lines of round info between the W/L and the team info.
        # If the first round experience is a BYE, then there are only 4 lines of round info between the BYE and the team info.
        # If the first round experience is a FORFEIT, then there are only 3 lines of round info between the FORFEIT and the team info.
        # We can use this to identify the team info.

        # Find the first round experience
 
        for i in range(len(team_lines)):
            if team_lines[i] in ['W', 'L', 'BYE', 'FORFEIT']:
                first_round_experience = i
                break

        if team_lines[first_round_experience] == "BYE":
            offset = 4
        elif team_lines[first_round_experience] == "FORFEIT":
            offset = 3
        else:
            offset = 6

        # Then move backwards from that line until we find the team info.
        # Make team info the three lines above the first round experience - offset.
        team_info = team_lines[first_round_experience - offset - 3:first_round_experience - offset]
        round_lines = team_lines[first_round_experience - offset:]

        # # First 3 lines are team info
        # team_info = team_lines[:3]
        # round_lines = team_lines[3:]
        
        round_experiences = []
        current_round = []
        
        for line in round_lines:
            if not line:  # Skip empty lines
                continue
                
            current_round.append(line)
            
            # Check if this line ends a round experience
            if line in ['W', 'L', 'BYE', 'FORFEIT']:
                if current_round:
                    round_experiences.append(team_info + current_round)
                    current_round = []
        
        # # Add any remaining lines as the last round (in case it doesn't end properly)
        # if current_round:
        #     round_experiences.append(team_info + current_round)
            
        return round_experiences
    
    def parse_round_experience(round_lines, tournament_name, year):
        """
        Parse a single round experience into round data.
        
        Expected structure:
        - Line 0: Team Member 1 name
        - Line 1: Team code + organization  
        - Line 2: Team Member 2 name
        - Lines 3-6: 4 speaker points
        - Line 7: Opponent code OR BYE OR FORFEIT
        - Line 8 (if regular): Side (Aff/Neg)
        - Line 9 (if regular): Result (W/L)
        """

        # Extract team information
        member1_name = round_lines[0]
        team_code_line = round_lines[1]
        member2_name = round_lines[2]
        
        # Extract team code (first word of line 1)
        team_code = team_code_line.split()[0] if team_code_line.split() else None
        if not team_code:
            return None
        
        # Extract the result of the round
        result = round_lines[-1] # This is the last line of the round experience
        if result not in ['W', 'L', 'BYE', 'FORFEIT']:
            return None
        
        if result == "FORFEIT":
            side = "Aff"  # Default to Aff for BYE rounds
            result = "L"
            print(f"FOREIT round found for team {team_code}")
            
            member1_points = 0
            member1_rank = 4
            member2_points = 0
            member2_rank = 4

            opponent_code = "FORFEIT"

        elif result == "BYE":
            side = "Aff"  # Default to Aff for FORFEIT rounds
            result = "W"

            member1_points = float(round_lines[3].rstrip('*'))
            member1_rank = int(round_lines[4].rstrip('*'))
            member2_points = float(round_lines[5].rstrip('*'))
            member2_rank = int(round_lines[6].rstrip('*'))

            opponent_code = "BYE"

        elif result == "W" or result == "L":
            side = round_lines[8]
            result = round_lines[9]

            member1_points = float(round_lines[3].rstrip('*'))
            member1_rank = int(round_lines[4].rstrip('*'))
            member2_points = float(round_lines[5].rstrip('*'))
            member2_rank = int(round_lines[6].rstrip('*'))
        
        # Extract opponent
            opponent_code = round_lines[7]
        
        
        # Create round record
        round_record = {
            'Team_Code': team_code,
            'Tournament_Name': tournament_name,
            'Year': year,
            'Member1_Name': member1_name,
            'Member2_Name': member2_name,
            'Member1_Points': member1_points,
            'Member1_Rank': member1_rank,
            'Member2_Points': member2_points,
            'Member2_Rank': member2_rank,
            'Opponent_Code': opponent_code,
            'Side': side,
            'Result': result,
            'Won': 1 if result == 'W' else 0
        }
        
        return round_record
    
    def parse_team_experience(team_lines, tournament_name, year):
        """
        Parse a single team's experience into rounds data using the new round-based approach.
        """
        # Split team experience into individual round experiences
        round_experiences = split_team_into_round_experiences(team_lines)
        
        rounds_data = []
        round_num = 1
        
        for round_exp in round_experiences:
            round_record = parse_round_experience(round_exp, tournament_name, year)
            if round_record:
                round_record['Round'] = round_num
                rounds_data.append(round_record)
                round_num += 1
            else:
                # Log parsing issues for debugging
                team_code = round_exp[1].split()[0] if len(round_exp) > 1 and round_exp[1].split() else "UNKNOWN"
                print(f"Failed to parse round for team {team_code}: {round_exp[3:] if len(round_exp) > 3 else round_exp}")
                
        return rounds_data
    
    # Main parsing logic
    print("Splitting text by team experiences...")
    team_experiences = split_by_team_experiences(text)
    print(f"Found {len(team_experiences)} potential team experiences")
    
    all_rounds_data = []
    teams_found = []
    parsing_issues = []
    
    for idx, experience in enumerate(team_experiences):
        # Clean the team experience
        cleaned_lines = clean_team_experience(experience)
        
        if len(cleaned_lines) < 3:
            continue  # Skip incomplete team experiences
            
        # Parse this team's data
        team_rounds = parse_team_experience(cleaned_lines, tournament_name, year)
        
        if team_rounds:
            team_code = team_rounds[0]['Team_Code']
            teams_found.append(team_code)
            all_rounds_data.extend(team_rounds)
        else:
            # Log parsing issues for debugging
            if len(cleaned_lines) >= 3:
                potential_team_code = cleaned_lines[1].split()[0] if cleaned_lines[1].split() else "UNKNOWN"
                parsing_issues.append(f"Failed to parse team {potential_team_code}: {cleaned_lines[:3]}")
    
    # Print debug summary
    print(f"\nDEBUG SUMMARY:")
    print(f"Found {len(teams_found)} teams: {sorted(teams_found)}")
    print(f"Total rounds extracted: {len(all_rounds_data)}")
    
    if parsing_issues:
        print(f"\nParsing issues ({len(parsing_issues)}):")
        for issue in parsing_issues[:10]:  # Show first 10 issues
            print(f"  - {issue}")
        if len(parsing_issues) > 10:
            print(f"  ... and {len(parsing_issues) - 10} more issues")
    else:
        print("No parsing issues detected.")
    
    return all_rounds_data

def merge_duplicate_rounds(df):
    """
    Merge duplicate rounds where each round appears twice (once from each team's perspective).
    Creates a single row per round with both teams' data.
    
    Enhanced to handle:
    1. BYE rounds (no opponent data to merge)
    2. FORFEIT rounds (one team forfeits, opponent sees regular win)
    3. Missing opponent data (data inconsistencies)
    4. Tournament/year/source file mismatches
    """
    merged_rounds = []
    processed_pairs = set()
    unmatched_rounds = []
    
    # Group rounds by tournament, year, and source file for better matching
    df_grouped = df.groupby(['Tournament_Name', 'Year', 'Source_File'])
    
    for (tournament, year, source_file), group_df in df_grouped:
        print(f"Processing {len(group_df)} rounds from {tournament} ({year}) - {source_file}")
        
        for idx, row in group_df.iterrows():
            team_a = row['Team_Code']
            team_b = row['Opponent_Code']
            round_num = row['Round']
            
            # Handle BYE and FORFEIT rounds separately - they don't need merging
            if team_b in ['BYE', 'FORFEIT']:
                merged_round = {
                    'Round_Number': round_num,
                    'Tournament_Name': row['Tournament_Name'],
                    'Year': row['Year'],
                    'Source_File': row['Source_File'],
                    'Team1_Code': team_a,
                    'Team1_Side': row['Side'],
                    'Team1_Member1_Name': row['Member1_Name'],
                    'Team1_Member2_Name': row['Member2_Name'],
                    'Team1_Member1_Points': row['Member1_Points'],
                    'Team1_Member1_Rank': row['Member1_Rank'],
                    'Team1_Member2_Points': row['Member2_Points'],
                    'Team1_Member2_Rank': row['Member2_Rank'],
                    'Team1_Won': row['Won'],
                    'Team2_Code': team_b,
                    'Team2_Side': 'Neg' if row['Side'] == 'Aff' else 'Aff',  # Opposite of Team1
                    'Team2_Member1_Name': '',
                    'Team2_Member2_Name': '',
                    'Team2_Member1_Points': 0,
                    'Team2_Member1_Rank': 0,
                    'Team2_Member2_Points': 0,
                    'Team2_Member2_Rank': 0,
                    'Team2_Won': 0 if team_b == 'FORFEIT' else 1,
                }
                merged_rounds.append(merged_round)
                continue
            
            # Create a sorted pair to avoid duplicates (A vs B is same as B vs A)
            pair_key = tuple(sorted([team_a, team_b]) + [round_num, tournament, year, source_file])
            
            if pair_key in processed_pairs:
                continue
                
            # Try multiple strategies to find the corresponding opponent row
            opponent_row = None
            
            # Strategy 1: Exact match (same tournament, year, source file)
            exact_match = group_df[
                (group_df['Team_Code'] == team_b) & 
                (group_df['Opponent_Code'] == team_a) & 
                (group_df['Round'] == round_num)
            ]
            
            if len(exact_match) == 1:
                opponent_row = exact_match.iloc[0]
            elif len(exact_match) > 1:
                # Multiple matches - take the first one and warn
                print(f"Warning: Multiple matches found for {team_a} vs {team_b} in round {round_num}, using first match")
                opponent_row = exact_match.iloc[0]
            else:
                # Strategy 2: Check if opponent team forfeited (they have FORFEIT as opponent)
                forfeit_check = group_df[
                    (group_df['Team_Code'] == team_b) & 
                    (group_df['Opponent_Code'] == 'FORFEIT') & 
                    (group_df['Round'] == round_num)
                ]
                
                if len(forfeit_check) == 1:
                    # Team B forfeited, so Team A gets a win against FORFEIT
                    # We need to create the opponent data manually
                    forfeit_opponent = forfeit_check.iloc[0]
                    
                    # Create a synthetic opponent row for the forfeiting team
                    opponent_row = forfeit_opponent.copy()
                    opponent_row['Opponent_Code'] = team_a  # Set opponent to team_a
                    opponent_row['Result'] = 'L'  # Forfeiting team loses
                    opponent_row['Won'] = 0
                    opponent_row['Member1_Points'] = 0
                    opponent_row['Member1_Rank'] = 4
                    opponent_row['Member2_Points'] = 0
                    opponent_row['Member2_Rank'] = 4
                    opponent_row['Side'] = 'Neg' if row['Side'] == 'Aff' else 'Aff'  # Opposite side
                    
                    print(f"Info: Found FORFEIT match for {team_a} vs {team_b} in round {round_num}")
                else:
                    # Strategy 3: Check if current team forfeited but opponent sees it as regular win
                    if row['Result'] == 'L' and row['Opponent_Code'] != 'FORFEIT':
                        # Check if there's a team that won against us in this round
                        potential_forfeit_winner = group_df[
                            (group_df['Team_Code'] == team_b) & 
                            (group_df['Round'] == round_num) &
                            (group_df['Result'] == 'W')
                        ]
                        
                        # Check if our speaker points are 0 (indicating forfeit)
                        if (row['Member1_Points'] == 0 and row['Member2_Points'] == 0 and 
                            len(potential_forfeit_winner) == 1):
                            opponent_row = potential_forfeit_winner.iloc[0]
                            print(f"Info: Detected forfeit situation for {team_a} vs {team_b} in round {round_num}")
            
            if opponent_row is not None:
                # Team1 is always the current row, Team2 is the opponent
                team1 = row
                team2 = opponent_row
                
                # Create merged round data
                merged_round = {
                    'Round_Number': round_num,
                    'Tournament_Name': row['Tournament_Name'],
                    'Year': row['Year'],
                    'Source_File': row['Source_File'],
                    'Team1_Code': team1['Team_Code'],
                    'Team1_Side': team1['Side'],
                    'Team1_Member1_Name': team1['Member1_Name'],
                    'Team1_Member2_Name': team1['Member2_Name'],
                    'Team1_Member1_Points': team1['Member1_Points'],
                    'Team1_Member1_Rank': team1['Member1_Rank'],
                    'Team1_Member2_Points': team1['Member2_Points'],
                    'Team1_Member2_Rank': team1['Member2_Rank'],
                    'Team1_Won': 1 if team1['Result'] == 'W' else 0,
                    'Team2_Code': team2['Team_Code'],
                    'Team2_Side': team2['Side'],
                    'Team2_Member1_Name': team2['Member1_Name'],
                    'Team2_Member2_Name': team2['Member2_Name'],
                    'Team2_Member1_Points': team2['Member1_Points'],
                    'Team2_Member1_Rank': team2['Member1_Rank'],
                    'Team2_Member2_Points': team2['Member2_Points'],
                    'Team2_Member2_Rank': team2['Member2_Rank'],
                    'Team2_Won': 1 if team2['Result'] == 'W' else 0,
                }
                
                merged_rounds.append(merged_round)
                processed_pairs.add(pair_key)
            else:
                # Store unmatched round for later analysis
                unmatched_rounds.append({
                    'team_a': team_a,
                    'team_b': team_b,
                    'round_num': round_num,
                    'tournament': tournament,
                    'year': year,
                    'source_file': source_file,
                    'row': row
                })
    
    # Process unmatched rounds - try to create single-team entries or warn
    print(f"\nProcessing {len(unmatched_rounds)} unmatched rounds...")
    
    for unmatched in unmatched_rounds:
        row = unmatched['row']
        team_a = unmatched['team_a']
        team_b = unmatched['team_b']
        round_num = unmatched['round_num']
        tournament = unmatched['tournament']
        year = unmatched['year']
        source_file = unmatched['source_file']
        
        # Create a single-team entry with empty opponent data
        merged_round = {
            'Round_Number': round_num,
            'Tournament_Name': tournament,
            'Year': year,
            'Source_File': source_file,
            'Team1_Code': team_a,
            'Team1_Side': row['Side'],
            'Team1_Member1_Name': row['Member1_Name'],
            'Team1_Member2_Name': row['Member2_Name'],
            'Team1_Member1_Points': row['Member1_Points'],
            'Team1_Member1_Rank': row['Member1_Rank'],
            'Team1_Member2_Points': row['Member2_Points'],
            'Team1_Member2_Rank': row['Member2_Rank'],
            'Team1_Won': 1 if row['Result'] == 'W' else 0,
            'Team2_Code': team_b,
            'Team2_Side': 'Neg' if row['Side'] == 'Aff' else 'Aff',
            'Team2_Member1_Name': 'MISSING_DATA',
            'Team2_Member2_Name': 'MISSING_DATA',
            'Team2_Member1_Points': 0,
            'Team2_Member1_Rank': 0,
            'Team2_Member2_Points': 0,
            'Team2_Member2_Rank': 0,
            'Team2_Won': 0 if row['Result'] == 'W' else 1,
        }
        
        merged_rounds.append(merged_round)
        
        # Only warn for truly problematic cases (not FORFEIT-related)
        if team_b not in ['BYE', 'FORFEIT'] and row['Member1_Points'] > 0:
            print(f"Warning: No matching opponent found for {team_a} vs {team_b} in round {round_num} at {tournament} ({year})")
    
    print(f"Successfully merged {len(merged_rounds)} rounds ({len(merged_rounds) - len(unmatched_rounds)} matched pairs + {len(unmatched_rounds)} unmatched)")
    
    return pd.DataFrame(merged_rounds)

def main():
    print("Starting round extraction...")
    
    # Get all PDF files in the cumulatives folder
    cumulatives_dir = "to_upload/matchup_model/cumulatives"
    if not os.path.exists(cumulatives_dir):
        print(f"Directory not found: {cumulatives_dir}")
        exit()
    
    pdf_files = [f for f in os.listdir(cumulatives_dir) if f.endswith('.pdf')]
    
    if not pdf_files:
        print("No PDF files found in cumulatives directory")
        exit()
    
    print(f"Found {len(pdf_files)} PDF files: {pdf_files}")
    
    all_rounds_data = []
    
    # Process each PDF file
    for pdf_file in pdf_files:
        pdf_path = os.path.join(cumulatives_dir, pdf_file)
        print(f"\nProcessing {pdf_file}...")
        

        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text = text + page.get_text()
        doc.close()
        print(f"Text extracted from {pdf_file}")

        # # Write the text to a file
        # with open(f"matchup_model/cumulatives/{pdf_file}.txt", "w") as file:
        #     file.write(text)
        
        # Extract rounds data from this file
        file_rounds_data = extract_rounds_from_text(text, pdf_file)
        print(f"Extracted {len(file_rounds_data)} rounds from {pdf_file}")
        
        # Add file source information to each round
        for round_data in file_rounds_data:
            round_data['Source_File'] = pdf_file
        
        all_rounds_data.extend(file_rounds_data)
            
        # except Exception as e:
        #     print(f"Error processing {pdf_file}: {str(e)}")
        #     continue
    
    print(f"\nTotal rounds extracted from all files: {len(all_rounds_data)}")
    
    # Use the combined data for the rest of the processing
    rounds_data = all_rounds_data
    
    print(f"Extracted {len(rounds_data)} individual team rounds")
    
    # Create DataFrame
    df = pd.DataFrame(rounds_data)
    
    if len(df) > 0:
        # Save the original (duplicated) data
        original_output_file = "to_upload/matchup_model/rounds_extracted_original.csv"
        df.to_csv(original_output_file, index=False)
        print(f"Original rounds data saved to '{original_output_file}'")
        
        # Merge duplicate rounds
        print("Merging duplicate rounds...")
        merged_df = merge_duplicate_rounds(df)
        
        print(f"Merged into {len(merged_df)} unique rounds")
        
        # Display summary
        print(f"\nMerged DataFrame created with {len(merged_df)} rows and {len(merged_df.columns)} columns")
        print(f"Unique teams: {len(set(list(merged_df['Team1_Code']) + list(merged_df['Team2_Code'])))}")
        
        # Save merged data to CSV
        merged_output_file = "to_upload/matchup_model/rounds_extracted.csv"
        merged_df.to_csv(merged_output_file, index=False)
        print(f"\nMerged rounds data saved to '{merged_output_file}'")
        
        # Display some statistics
        print(f"\nStatistics:")
        print(f"Total rounds: {len(merged_df)}")
        print(f"Team1 win rate: {merged_df['Team1_Won'].mean():.3f}")
        print(f"Team2 win rate: {merged_df['Team2_Won'].mean():.3f}")
        
        # Calculate Aff/Neg win rates
        aff_wins = len(merged_df[(merged_df['Team1_Side'] == 'Aff') & (merged_df['Team1_Won'] == 1)]) + \
                   len(merged_df[(merged_df['Team2_Side'] == 'Aff') & (merged_df['Team2_Won'] == 1)])
        total_aff = len(merged_df[merged_df['Team1_Side'] == 'Aff']) + len(merged_df[merged_df['Team2_Side'] == 'Aff'])
        aff_win_rate = aff_wins / total_aff if total_aff > 0 else 0
        print(f"Aff win rate: {aff_win_rate:.3f}")
        print(f"Neg win rate: {1 - aff_win_rate:.3f}")
        
        # Calculate unique team codes
        all_teams = set(list(merged_df['Team1_Code']) + list(merged_df['Team2_Code']))
        # Remove BYE and FORFEIT from team count
        all_teams.discard('BYE')
        all_teams.discard('FORFEIT')
        print(f"\nUnique team codes: {len(all_teams)}")
        
        # Statistics by source file and tournament
        print(f"\nStatistics by source file:")
        for source_file in sorted(merged_df['Source_File'].unique()):
            file_df = merged_df[merged_df['Source_File'] == source_file]
            file_teams = set(list(file_df['Team1_Code']) + list(file_df['Team2_Code']))
            file_teams.discard('BYE')
            file_teams.discard('FORFEIT')
            tournament_name = file_df['Tournament_Name'].iloc[0] if len(file_df) > 0 else "Unknown Tournament"
            year = file_df['Year'].iloc[0] if len(file_df) > 0 else "Unknown"
            print(f"  {source_file} - {tournament_name} ({year}): {len(file_df)} rounds, {len(file_teams)} teams")
        
        # Count special rounds
        bye_rounds = len(merged_df[(merged_df['Team1_Code'] == 'BYE') | (merged_df['Team2_Code'] == 'BYE')])
        forfeit_rounds = len(merged_df[(merged_df['Team1_Code'] == 'FORFEIT') | (merged_df['Team2_Code'] == 'FORFEIT')])
        regular_rounds = len(merged_df) - bye_rounds - forfeit_rounds
        
        print(f"\nRound types:")
        print(f"  Regular rounds: {regular_rounds}")
        print(f"  BYE rounds: {bye_rounds}")
        print(f"  FORFEIT rounds: {forfeit_rounds}")
        
        # Count rounds by round number
        print(f"\nRounds by round number:")
        round_counts = merged_df['Round_Number'].value_counts().sort_index()
        for round_num in sorted(round_counts.index):
            print(f"  Round {round_num}: {round_counts[round_num]} rounds")
        
        # Calculate speaker point statistics
        all_points = []
        all_points.extend(merged_df['Team1_Member1_Points'].tolist())
        all_points.extend(merged_df['Team1_Member2_Points'].tolist())
        all_points.extend(merged_df['Team2_Member1_Points'].tolist())
        all_points.extend(merged_df['Team2_Member2_Points'].tolist())
        
        # Filter out zero points (from BYE/FORFEIT rounds)
        non_zero_points = [p for p in all_points if p > 0]
        
        if non_zero_points:
            print(f"\nSpeaker point statistics:")
            print(f"  Maximum speaker points: {max(non_zero_points):.1f}")
            print(f"  Minimum speaker points: {min(non_zero_points):.1f}")
            print(f"  Average speaker points: {sum(non_zero_points)/len(non_zero_points):.2f}")
            
            print(f"\nAverage speaker points by team position:")
            team1_mem1_points = [p for p in merged_df['Team1_Member1_Points'].tolist() if p > 0]
            team1_mem2_points = [p for p in merged_df['Team1_Member2_Points'].tolist() if p > 0]
            team2_mem1_points = [p for p in merged_df['Team2_Member1_Points'].tolist() if p > 0]
            team2_mem2_points = [p for p in merged_df['Team2_Member2_Points'].tolist() if p > 0]
            
            if team1_mem1_points:
                print(f"  Team1 Member 1: {sum(team1_mem1_points)/len(team1_mem1_points):.2f}")
            if team1_mem2_points:
                print(f"  Team1 Member 2: {sum(team1_mem2_points)/len(team1_mem2_points):.2f}")
            if team2_mem1_points:
                print(f"  Team2 Member 1: {sum(team2_mem1_points)/len(team2_mem1_points):.2f}")
            if team2_mem2_points:
                print(f"  Team2 Member 2: {sum(team2_mem2_points)/len(team2_mem2_points):.2f}")
            
            # Calculate speaker points by side (Aff/Neg)
            aff_team1_df = merged_df[merged_df['Team1_Side'] == 'Aff']
            aff_team2_df = merged_df[merged_df['Team2_Side'] == 'Aff']
            neg_team1_df = merged_df[merged_df['Team1_Side'] == 'Neg']
            neg_team2_df = merged_df[merged_df['Team2_Side'] == 'Neg']
            
            all_aff_points = []
            if len(aff_team1_df) > 0:
                all_aff_points.extend([p for p in aff_team1_df['Team1_Member1_Points'].tolist() if p > 0])
                all_aff_points.extend([p for p in aff_team1_df['Team1_Member2_Points'].tolist() if p > 0])
            if len(aff_team2_df) > 0:
                all_aff_points.extend([p for p in aff_team2_df['Team2_Member1_Points'].tolist() if p > 0])
                all_aff_points.extend([p for p in aff_team2_df['Team2_Member2_Points'].tolist() if p > 0])
            
            all_neg_points = []
            if len(neg_team1_df) > 0:
                all_neg_points.extend([p for p in neg_team1_df['Team1_Member1_Points'].tolist() if p > 0])
                all_neg_points.extend([p for p in neg_team1_df['Team1_Member2_Points'].tolist() if p > 0])
            if len(neg_team2_df) > 0:
                all_neg_points.extend([p for p in neg_team2_df['Team2_Member1_Points'].tolist() if p > 0])
                all_neg_points.extend([p for p in neg_team2_df['Team2_Member2_Points'].tolist() if p > 0])
            
            print(f"\nAverage speaker points by side:")
            if all_aff_points:
                print(f"  Aff speakers: {sum(all_aff_points)/len(all_aff_points):.2f}")
            if all_neg_points:
                print(f"  Neg speakers: {sum(all_neg_points)/len(all_neg_points):.2f}")
        else:
            print("\nNo speaker point data available.")
        
    else:
        print("No rounds data extracted. Please check the text file format.")

if __name__ == "__main__":
    main()