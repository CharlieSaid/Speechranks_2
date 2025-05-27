import numpy as np
import pandas as pd
import re
import os
import fitz  # PyMuPDF

print("Imports done")

text = ""

# Check if the file exists
if not os.path.exists("matchup_model/cumulatives/nitoc-2024-tp-cum-file.pdf"):
    print("File not found")
    exit()

doc = fitz.open("matchup_model/cumulatives/nitoc-2024-tp-cum-file.pdf")

for page in doc:
    text = text + (page.get_text())
print("Text extracted")

def parse_teams_from_text(text):
    lines = text.split('\n')
    teams = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        print(line)

        if line == "Team Policy" or line == "Preliminary Round Results":
            print("Skipping")
            i += 1
            continue
        
        # Look for pattern: First Name Last Name
        if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+$', line):
            first_member = line
            
            # Next line should be team code and organization
            if i + 1 < len(lines):
                team_line = lines[i + 1].strip()
                # Extract team code (first part before space)
                team_code_match = re.match(r'^([A-Z]+[A-Z0-9]*)', team_line)
                if team_code_match:
                    team_code = team_code_match.group(1)
                    
                    # Next line should be second member name
                    if i + 2 < len(lines):
                        second_member_line = lines[i + 2].strip()
                        if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+$', second_member_line):
                            second_member = second_member_line
                            
                            teams.append({
                                'Team Code': team_code,
                                'First Member': first_member,
                                'Second Member': second_member
                            })
                            
                            i += 3  # Skip the processed lines
                            continue
        
        i += 1
    
    return teams

# Parse teams from the OCR text
teams_data = parse_teams_from_text(text)

# Create DataFrame
df = pd.DataFrame(teams_data)

df['Team Name'] = df['First Member'] + "/" + df['Second Member']

# Remove duplicates based on team code
df = df.drop_duplicates(subset=['Team Code'])

print(f"\n=== Extracted Teams ({len(df)} teams) ===")
print(df.to_string(index=False))

# Save to CSV
df.to_csv('matchup_model/teams_extracted.csv', index=False)
print("\nTeams data saved to 'matchup_model/teams_extracted.csv'")