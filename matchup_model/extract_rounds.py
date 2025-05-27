import numpy as np
import pandas as pd
import re
import os
import fitz  # PyMuPDF

def extract_rounds_from_text(text):
    """
    Extract debate round results from the cumulative text file using a team-experience-based approach.
    
    Strategy:
    1. Split text by team experiences (ending with " - " pattern between two integers)
    2. Remove page break lines from each team experience
    3. Parse each team experience individually:
       - Line 1: Team Member 1 name
       - Line 2: Team code (first word) + organization
       - Line 3: Team Member 2 name
       - Remaining lines: Round data (speaker points, opponent, side, result)
    """
    
    def is_page_break_line(line):
        """Check if line is a page break header"""
        page_break_indicators = ["Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", 
                               "Monday", "Page", "Team Policy", "Preliminary Round Results", "2009",
                               "2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", 
                               "2020", "2021", "2022", "2023", "2024", "2025"]
        return any(indicator in line for indicator in page_break_indicators)
    
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
            
            # Check if this line is a team summary (ends with " - " between two integers)
            if re.match(r'^\d+\s*-\s*\d+$', line):
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
            
        # First 3 lines are team info
        team_info = team_lines[:3]
        round_lines = team_lines[3:]
        
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
                    print(round_experiences[-1])
                    current_round = []
        
        # Add any remaining lines as the last round (in case it doesn't end properly)
        if current_round:
            round_experiences.append(team_info + current_round)
            
        return round_experiences
    
    def parse_round_experience(round_lines):
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
            print(f"BYE round found for team {team_code}")

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
    
    def parse_team_experience(team_lines):
        """
        Parse a single team's experience into rounds data using the new round-based approach.
        """
        # Split team experience into individual round experiences
        round_experiences = split_team_into_round_experiences(team_lines)
        
        rounds_data = []
        round_num = 1
        
        for round_exp in round_experiences:
            round_record = parse_round_experience(round_exp)
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
        team_rounds = parse_team_experience(cleaned_lines)
        
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
    BYE rounds are handled separately since they don't have opponent data to merge.
    """
    merged_rounds = []
    processed_pairs = set()
    
    for idx, row in df.iterrows():
        team_a = row['Team_Code']
        team_b = row['Opponent_Code']
        round_num = row['Round']
        
        # Handle BYE and FORFEIT rounds separately - they don't need merging
        if team_b in ['BYE', 'FORFEIT']:
            merged_round = {
                'Round_Number': round_num,
                'Source_File': row['Source_File'],
                'Aff_Team_Code': team_a if row['Side'] == 'Aff' else team_b,
                'Aff_Member1_Name': row['Member1_Name'] if row['Side'] == 'Aff' else '',
                'Aff_Member2_Name': row['Member2_Name'] if row['Side'] == 'Aff' else '',
                'Aff_Member1_Points': row['Member1_Points'] if row['Side'] == 'Aff' else 0,
                'Aff_Member1_Rank': row['Member1_Rank'] if row['Side'] == 'Aff' else 0,
                'Aff_Member2_Points': row['Member2_Points'] if row['Side'] == 'Aff' else 0,
                'Aff_Member2_Rank': row['Member2_Rank'] if row['Side'] == 'Aff' else 0,
                'Aff_Won': row['Won'] if row['Side'] == 'Aff' else (0 if team_b == 'FORFEIT' else 1),
                'Neg_Team_Code': team_a if row['Side'] == 'Neg' else team_b,
                'Neg_Member1_Name': row['Member1_Name'] if row['Side'] == 'Neg' else '',
                'Neg_Member2_Name': row['Member2_Name'] if row['Side'] == 'Neg' else '',
                'Neg_Member1_Points': row['Member1_Points'] if row['Side'] == 'Neg' else 0,
                'Neg_Member1_Rank': row['Member1_Rank'] if row['Side'] == 'Neg' else 0,
                'Neg_Member2_Points': row['Member2_Points'] if row['Side'] == 'Neg' else 0,
                'Neg_Member2_Rank': row['Member2_Rank'] if row['Side'] == 'Neg' else 0,
                'Neg_Won': row['Won'] if row['Side'] == 'Neg' else (0 if team_b == 'FORFEIT' else 1),
            }
            merged_rounds.append(merged_round)
            continue
        
        # Create a sorted pair to avoid duplicates (A vs B is same as B vs A)
        pair_key = tuple(sorted([team_a, team_b]) + [round_num])
        
        if pair_key in processed_pairs:
            continue
            
        # Find the corresponding row for the opponent team
        opponent_row = df[
            (df['Team_Code'] == team_b) & 
            (df['Opponent_Code'] == team_a) & 
            (df['Round'] == round_num)
        ]
        
        if len(opponent_row) == 1:
            opp = opponent_row.iloc[0]
            
            # Determine which team was Aff and which was Neg
            if row['Side'] == 'Aff':
                aff_team = row
                neg_team = opp
            else:
                aff_team = opp
                neg_team = row
            
            # Create merged round data
            merged_round = {
                'Round_Number': round_num,
                'Source_File': row['Source_File'],  # Both teams should have same source file
                'Aff_Team_Code': aff_team['Team_Code'],
                'Aff_Member1_Name': aff_team['Member1_Name'],
                'Aff_Member2_Name': aff_team['Member2_Name'],
                'Aff_Member1_Points': aff_team['Member1_Points'],
                'Aff_Member1_Rank': aff_team['Member1_Rank'],
                'Aff_Member2_Points': aff_team['Member2_Points'],
                'Aff_Member2_Rank': aff_team['Member2_Rank'],
                'Aff_Won': 1 if aff_team['Result'] == 'W' else 0,
                'Neg_Team_Code': neg_team['Team_Code'],
                'Neg_Member1_Name': neg_team['Member1_Name'],
                'Neg_Member2_Name': neg_team['Member2_Name'],
                'Neg_Member1_Points': neg_team['Member1_Points'],
                'Neg_Member1_Rank': neg_team['Member1_Rank'],
                'Neg_Member2_Points': neg_team['Member2_Points'],
                'Neg_Member2_Rank': neg_team['Member2_Rank'],
                'Neg_Won': 1 if neg_team['Result'] == 'W' else 0,
            }
            
            merged_rounds.append(merged_round)
            processed_pairs.add(pair_key)
        else:
            # If no matching opponent found, keep the original row but mark it
            print(f"Warning: No matching opponent found for {team_a} vs {team_b} in round {round_num}")
    
    return pd.DataFrame(merged_rounds)

def main():
    print("Starting round extraction...")
    
    # Get all PDF files in the cumulatives folder
    cumulatives_dir = "matchup_model/cumulatives"
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

        # Write the text to a file
        with open(f"matchup_model/cumulatives/{pdf_file}.txt", "w") as file:
            file.write(text)
        
        # Extract rounds data from this file
        file_rounds_data = extract_rounds_from_text(text)
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
        original_output_file = "matchup_model/rounds_extracted_original.csv"
        df.to_csv(original_output_file, index=False)
        print(f"Original rounds data saved to '{original_output_file}'")
        
        # Merge duplicate rounds
        print("Merging duplicate rounds...")
        merged_df = merge_duplicate_rounds(df)
        
        print(f"Merged into {len(merged_df)} unique rounds")
        
        # Display summary
        print(f"\nMerged DataFrame created with {len(merged_df)} rows and {len(merged_df.columns)} columns")
        print(f"Unique teams: {len(set(list(merged_df['Aff_Team_Code']) + list(merged_df['Neg_Team_Code'])))}")
        
        # Display first few rows
        print("\nFirst 5 merged rounds:")
        print(merged_df.head(5).to_string(index=False))
        
        # Save merged data to CSV
        merged_output_file = "matchup_model/rounds_extracted.csv"
        merged_df.to_csv(merged_output_file, index=False)
        print(f"\nMerged rounds data saved to '{merged_output_file}'")
        
        # Display some statistics
        print(f"\nStatistics:")
        print(f"Total rounds: {len(merged_df)}")
        print(f"Aff win rate: {merged_df['Aff_Won'].mean():.3f}")
        print(f"Neg win rate: {merged_df['Neg_Won'].mean():.3f}")
        
        # Calculate unique team codes
        all_teams = set(list(merged_df['Aff_Team_Code']) + list(merged_df['Neg_Team_Code']))
        # Remove BYE and FORFEIT from team count
        all_teams.discard('BYE')
        all_teams.discard('FORFEIT')
        print(f"\nUnique team codes: {len(all_teams)}")
        
        # Statistics by source file
        print(f"\nStatistics by source file:")
        for source_file in sorted(merged_df['Source_File'].unique()):
            file_df = merged_df[merged_df['Source_File'] == source_file]
            file_teams = set(list(file_df['Aff_Team_Code']) + list(file_df['Neg_Team_Code']))
            file_teams.discard('BYE')
            file_teams.discard('FORFEIT')
            print(f"  {source_file}: {len(file_df)} rounds, {len(file_teams)} teams")
        
        # Count special rounds
        bye_rounds = len(merged_df[(merged_df['Aff_Team_Code'] == 'BYE') | (merged_df['Neg_Team_Code'] == 'BYE')])
        forfeit_rounds = len(merged_df[(merged_df['Aff_Team_Code'] == 'FORFEIT') | (merged_df['Neg_Team_Code'] == 'FORFEIT')])
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
        all_points.extend(merged_df['Aff_Member1_Points'].tolist())
        all_points.extend(merged_df['Aff_Member2_Points'].tolist())
        all_points.extend(merged_df['Neg_Member1_Points'].tolist())
        all_points.extend(merged_df['Neg_Member2_Points'].tolist())
        
        print(f"\nSpeaker point statistics:")
        print(f"  Maximum speaker points: {max(all_points):.1f}")
        print(f"  Minimum speaker points: {min(all_points):.1f}")
        print(f"  Average speaker points: {sum(all_points)/len(all_points):.2f}")
        
        print(f"\nAverage speaker points by position:")
        print(f"  Aff Member 1: {merged_df['Aff_Member1_Points'].mean():.2f}")
        print(f"  Aff Member 2: {merged_df['Aff_Member2_Points'].mean():.2f}")
        print(f"  Neg Member 1: {merged_df['Neg_Member1_Points'].mean():.2f}")
        print(f"  Neg Member 2: {merged_df['Neg_Member2_Points'].mean():.2f}")
        
    else:
        print("No rounds data extracted. Please check the text file format.")

if __name__ == "__main__":
    main()