// Matchup Page JavaScript

document.addEventListener('DOMContentLoaded', () => {
    initializeMatchupPage();
});

// Global state for matchup page
let matchupAllTeams1 = [];
let matchupAllTeams2 = [];
let selectedTeam1 = null;
let selectedTeam2 = null;

// DOM Elements
const matchupElements = {
    team1YearSelect: document.getElementById('team1YearSelect'),
    team2YearSelect: document.getElementById('team2YearSelect'),
    team1SearchInput: document.getElementById('team1SearchInput'),
    team2SearchInput: document.getElementById('team2SearchInput'),
    team1Results: document.getElementById('team1Results'),
    team2Results: document.getElementById('team2Results'),
    selectedTeam1StatsContainer: document.getElementById('selectedTeam1StatsContainer'),
    selectedTeam2StatsContainer: document.getElementById('selectedTeam2StatsContainer'),
    team1Label: document.querySelector('label[for="team1SearchInput"]'), // For potential use later
    team2Label: document.querySelector('label[for="team2SearchInput"]'), // For potential use later
    aboutBtn: document.getElementById('aboutBtnMatchup'),
    aboutModal: document.getElementById('aboutModalMatchup'),
    closeModal: document.querySelector('.closeMatchup')
};

async function initializeMatchupPage() {
    await populateYearSelectors();
    setupEventListeners();
    setupModalHandlersMatchup();
    // Ensure initial state has stats containers hidden and results lists shown
    if (matchupElements.selectedTeam1StatsContainer) matchupElements.selectedTeam1StatsContainer.style.display = 'none';
    if (matchupElements.team1Results) matchupElements.team1Results.style.display = 'block'; // Or an appropriate display value like 'flex' if it is a flex container
    if (matchupElements.selectedTeam2StatsContainer) matchupElements.selectedTeam2StatsContainer.style.display = 'none';
    if (matchupElements.team2Results) matchupElements.team2Results.style.display = 'block';
}

async function populateYearSelectors() {
    try {
        const response = await fetch('../year_files/manifest.json'); // Path relative to matchup.js
        if (!response.ok) {
            throw new Error('Failed to load ../year_files/manifest.json for matchup page');
        }
        const manifest = await response.json();
        let years = manifest.available_years || [];

        years.sort((a, b) => b - a); // Sort descending, newest first

        if (years.length > 0) {
            [matchupElements.team1YearSelect, matchupElements.team2YearSelect].forEach(selectElement => {
                if (!selectElement) {
                    console.error("Year select element not found");
                    return;
                }
                selectElement.innerHTML = '<option value="">Select Year</option>'; // Clear existing options
                years.forEach(year => {
                    const option = document.createElement('option');
                    option.value = year;
                    option.textContent = year;
                    selectElement.appendChild(option);
                });
            });
            
            if (matchupElements.team1YearSelect.options.length > 1) {
                 matchupElements.team1YearSelect.value = years[0]; 
                 await loadMatchupTeamData(years[0], 1);
                 if (matchupElements.selectedTeam1StatsContainer) matchupElements.selectedTeam1StatsContainer.style.display = 'none';
                 if (matchupElements.team1Results) matchupElements.team1Results.style.display = 'block';
            }
            if (matchupElements.team2YearSelect.options.length > 1) {
                matchupElements.team2YearSelect.value = years[0];
                await loadMatchupTeamData(years[0], 2);
                if (matchupElements.selectedTeam2StatsContainer) matchupElements.selectedTeam2StatsContainer.style.display = 'none';
                if (matchupElements.team2Results) matchupElements.team2Results.style.display = 'block';
            }
        } else {
            console.warn('No debate team data files found for matchup page.');
        }
    } catch (error) {
        console.error('Error populating year selectors for matchup from manifest:', error);
        // Handle UI for no years available if necessary, e.g., disable dropdowns
        [matchupElements.team1YearSelect, matchupElements.team2YearSelect].forEach(selectElement => {
            if(selectElement) {
                selectElement.innerHTML = '<option value="">No Years</option>';
                selectElement.disabled = true;
            }
        });
    }
}

function setupEventListeners() {
    if (matchupElements.team1YearSelect) {
        matchupElements.team1YearSelect.addEventListener('change', async (event) => {
            selectedTeam1 = null; 
            matchupElements.team1SearchInput.value = ''; 
            await loadMatchupTeamData(event.target.value, 1);
            if (matchupElements.selectedTeam1StatsContainer) matchupElements.selectedTeam1StatsContainer.style.display = 'none';
            if (matchupElements.team1Results) matchupElements.team1Results.style.display = 'block';
            // displayMatchupTeamList(1) is called by loadMatchupTeamData
        });
    }
    if (matchupElements.team2YearSelect) {
        matchupElements.team2YearSelect.addEventListener('change', async (event) => {
            selectedTeam2 = null; 
            matchupElements.team2SearchInput.value = ''; 
            await loadMatchupTeamData(event.target.value, 2);
            if (matchupElements.selectedTeam2StatsContainer) matchupElements.selectedTeam2StatsContainer.style.display = 'none';
            if (matchupElements.team2Results) matchupElements.team2Results.style.display = 'block';
            // displayMatchupTeamList(2) is called by loadMatchupTeamData
        });
    }

    if (matchupElements.team1SearchInput) {
        matchupElements.team1SearchInput.addEventListener('input', () => {
            if (selectedTeam1 && matchupElements.team1SearchInput.value !== getCompositeTeamNameMatchup(selectedTeam1)) {
                selectedTeam1 = null; 
                if (matchupElements.selectedTeam1StatsContainer) matchupElements.selectedTeam1StatsContainer.style.display = 'none';
                if (matchupElements.team1Results) matchupElements.team1Results.style.display = 'block';
            }
            if (!selectedTeam1) {
                 displayMatchupTeamList(1);
            }
        });
    }
    if (matchupElements.team2SearchInput) {
        matchupElements.team2SearchInput.addEventListener('input', () => {
            if (selectedTeam2 && matchupElements.team2SearchInput.value !== getCompositeTeamNameMatchup(selectedTeam2)) {
                selectedTeam2 = null; 
                if (matchupElements.selectedTeam2StatsContainer) matchupElements.selectedTeam2StatsContainer.style.display = 'none';
                if (matchupElements.team2Results) matchupElements.team2Results.style.display = 'block';
            }
            if (!selectedTeam2) {
                displayMatchupTeamList(2);
            }
        });
    }
}

async function loadMatchupTeamData(year, panelNumber) {
    if (!year) {
        if (panelNumber === 1) matchupAllTeams1 = [];
        else matchupAllTeams2 = [];
        displayMatchupTeamList(panelNumber);
        return;
    }
    try {
        const response = await fetch(`../year_files/debate_teams_${year}.json`);
        if (!response.ok) throw new Error(`Failed to load team data for ${year}`);
        
        const data = await response.json();
        if (panelNumber === 1) {
            matchupAllTeams1 = data;
        } else {
            matchupAllTeams2 = data;
        }
        // After loading new data, if a team was selected, its info might be stale or not exist in the new year.
        // So, clear selections for the panel whose year changed.
        if (panelNumber === 1) selectedTeam1 = null;
        else selectedTeam2 = null;
        displayMatchupTeamList(panelNumber); // Display after loading, typically the full list for the new year
    } catch (error) {
        console.error(`Error loading team data for panel ${panelNumber}:`, error);
        if (panelNumber === 1) matchupAllTeams1 = [];
        else matchupAllTeams2 = [];
        displayMatchupTeamList(panelNumber);
    }
}

function getCompositeTeamNameMatchup(team) {
    if (!team) return "Unknown Team";
    const name1 = team.debater1 && team.debater1.name ? team.debater1.name.trim() : "N/A";
    const name2 = team.debater2 && team.debater2.name ? team.debater2.name.trim() : "N/A";
    if (name1 === "N/A" && name2 === "N/A") return "Unknown Team";
    if (name1 === "N/A") return name2;
    if (name2 === "N/A") return name1;
    return `${name1} / ${name2}`;
}

function parseRecord(recordStr) {
    if (!recordStr || typeof recordStr !== 'string') return [0, 0];
    const parts = recordStr.split('-').map(n => parseInt(n.trim()));
    return parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1]) ? [parts[0], parts[1]] : [0, 0];
}

function calculateRatioString(wins, losses) {
    if (wins === 0 && losses === 0) return "0 / 0 (N/A)";
    const totalRounds = wins + losses;
    const ratio = totalRounds > 0 ? ((wins / totalRounds) * 100).toFixed(1) : "0.0";
    return `${wins} / ${losses} (${ratio}%)`;
}

function handleTeamSelection(team, panelNumber) {
    const searchInput = panelNumber === 1 ? matchupElements.team1SearchInput : matchupElements.team2SearchInput;
    const resultsContainer = panelNumber === 1 ? matchupElements.team1Results : matchupElements.team2Results; // This is the list container
    const statsContainer = panelNumber === 1 ? matchupElements.selectedTeam1StatsContainer : matchupElements.selectedTeam2StatsContainer;

    if (!statsContainer) {
        console.error(`Stats container for panel ${panelNumber} not found.`);
        return;
    }

    if (panelNumber === 1) {
        selectedTeam1 = team;
    } else {
        selectedTeam2 = team;
    }

    searchInput.value = getCompositeTeamNameMatchup(team);
    
    statsContainer.innerHTML = ''; // Clear previous stats from the dedicated stats container

    // Add "Summary Metrics" header
    const summaryHeader = document.createElement('h3');
    summaryHeader.className = 'stats-header';
    summaryHeader.textContent = 'Summary Metrics';
    statsContainer.appendChild(summaryHeader);

    // Calculate statistics
    const numTournaments = team.tournaments ? team.tournaments.length : 0;
    let totalPrelimWins = 0;
    let totalPrelimLosses = 0;
    let totalOverallWins = 0;
    let totalOverallLosses = 0;

    if (team.tournaments) {
        team.tournaments.forEach(tournament => {
            const [pWins, pLosses] = parseRecord(tournament.prelim_record);
            totalPrelimWins += pWins;
            totalPrelimLosses += pLosses;

            const [oWins, oLosses] = parseRecord(tournament.overall_record);
            totalOverallWins += oWins;
            totalOverallLosses += oLosses;
        });
    }

    const totalOutroundWins = totalOverallWins - totalPrelimWins;
    const totalOutroundLosses = totalOverallLosses - totalPrelimLosses;

    const stats = [
        { label: "National Rank", value: team.national_rank || 'N/A' },
        { label: "Number of Tournaments", value: numTournaments },
        { label: "Total Win/Loss", value: calculateRatioString(totalOverallWins, totalOverallLosses) },
        { label: "Prelim Win/Loss", value: calculateRatioString(totalPrelimWins, totalPrelimLosses) },
        { label: "Outround Win/Loss", value: calculateRatioString(totalOutroundWins, totalOutroundLosses) }
    ];

    const table = document.createElement('table');
    table.className = 'stats-table';
    const tbody = document.createElement('tbody');

    stats.forEach(stat => {
        const row = tbody.insertRow();
        const cellLabel = row.insertCell();
        cellLabel.textContent = stat.label;
        const cellValue = row.insertCell();
        cellValue.textContent = stat.value;
    });

    table.appendChild(tbody);
    statsContainer.appendChild(table); // Append table to the dedicated stats container

    // Add "Experience and Exposure" header
    const experienceHeader = document.createElement('h3');
    experienceHeader.className = 'stats-header';
    experienceHeader.textContent = 'Experience and Exposure';
    statsContainer.appendChild(experienceHeader);

    // Placeholder for future content for Experience and Exposure
    // const experienceContentDiv = document.createElement('div');
    // experienceContentDiv.className = 'experience-content';
    // experienceContentDiv.textContent = 'Details coming soon...';
    // statsContainer.appendChild(experienceContentDiv);

    // Hide results list and show stats container
    if(resultsContainer) resultsContainer.style.display = 'none';
    statsContainer.style.display = 'block';
}

function displayMatchupTeamList(panelNumber) {
    const resultsContainer = panelNumber === 1 ? matchupElements.team1Results : matchupElements.team2Results;
    const statsContainer = panelNumber === 1 ? matchupElements.selectedTeam1StatsContainer : matchupElements.selectedTeam2StatsContainer;

    // Hide stats, show results list
    if(statsContainer) statsContainer.style.display = 'none';
    if(resultsContainer) resultsContainer.style.display = 'block'; // Or appropriate display type

    const currentSelectedTeam = panelNumber === 1 ? selectedTeam1 : selectedTeam2;
    const searchInputValue = panelNumber === 1 ? matchupElements.team1SearchInput.value : matchupElements.team2SearchInput.value;
    if (currentSelectedTeam && getCompositeTeamNameMatchup(currentSelectedTeam) === searchInputValue) {
        // A team is selected and the search bar shows its name, so its info should be displayed.
        // handleTeamSelection would have already set this up.
        // Or, if we want to ensure it's displayed, call a display-only function here.
        // For now, assume handleTeamSelection took care of it.
        return; 
    }

    const teams = panelNumber === 1 ? matchupAllTeams1 : matchupAllTeams2;
    const searchInputString = panelNumber === 1 ? matchupElements.team1SearchInput.value.toLowerCase() : matchupElements.team2SearchInput.value.toLowerCase();

    if (!resultsContainer) {
        console.error(`Results container for panel ${panelNumber} not found in displayMatchupTeamList.`);
        return;
    }
    resultsContainer.innerHTML = ''; // Clear previous results or selected team info

    const filteredTeams = teams.filter(team => {
        const compositeName = getCompositeTeamNameMatchup(team).toLowerCase();
        return compositeName.includes(searchInputString);
    });

    if (filteredTeams.length === 0 && searchInputString.length > 0 && teams.length > 0) {
        const noResultsMessage = document.createElement('p');
        noResultsMessage.textContent = 'No teams match your search.';
        noResultsMessage.style.padding = '10px';
        resultsContainer.appendChild(noResultsMessage);
        return;
    }
    
    const yearSelect = panelNumber === 1 ? matchupElements.team1YearSelect : matchupElements.team2YearSelect;
    if (filteredTeams.length === 0 && teams.length === 0 && searchInputString.length === 0 && yearSelect.value !== "") {
        const loadingMessage = document.createElement('p');
        loadingMessage.textContent = 'Loading teams or no teams for this year...';
        loadingMessage.style.padding = '10px';
        resultsContainer.appendChild(loadingMessage);
        return;
    }

    filteredTeams.forEach(team => {
        const teamDiv = document.createElement('div');
        teamDiv.className = 'matchup-team-item'; 
        teamDiv.textContent = getCompositeTeamNameMatchup(team);
        teamDiv.addEventListener('click', () => handleTeamSelection(team, panelNumber));
        resultsContainer.appendChild(teamDiv);
    });
}

function setupModalHandlersMatchup() {
    if (matchupElements.aboutBtn && matchupElements.aboutModal && matchupElements.closeModal) {
        matchupElements.aboutBtn.onclick = function() {
            matchupElements.aboutModal.style.display = "block";
        }
        matchupElements.closeModal.onclick = function() {
            matchupElements.aboutModal.style.display = "none";
        }
        window.onclick = function(event) {
            if (event.target == matchupElements.aboutModal) {
                matchupElements.aboutModal.style.display = "none";
            }
        }
    } else {
        console.warn("Modal elements not found for matchup page. Skipping modal setup.");
    }
}