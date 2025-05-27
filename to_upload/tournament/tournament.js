// Tournament Simulator JavaScript

// --- GLOBAL STATE ---
let allTeams = [];
let availableYears = [];
let selectedYear = null;
let searchQuery = '';
let tournamentRoster = [];
let finalized = false;

// --- DOM ELEMENTS ---
const elements = {
    yearSelect: document.getElementById('yearSelect'),
    searchInput: document.getElementById('searchInput'),
    teamSelectTableBody: document.getElementById('teamSelectTableBody'),
    tournamentRoster: document.getElementById('tournamentRoster'),
    finalizeBtn: document.getElementById('finalizeBtn'),
    container: document.getElementById('tournamentContainer'),
    teamSelectPanel: document.getElementById('teamSelectPanel'),
    rosterPanel: document.getElementById('rosterPanel'),
};

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', async function() {
    console.log('Tournament Simulator: DOMContentLoaded');
    await getAvailableYearsFromManifest();
    setupYearSelector();
    setupSearchListener();
    setupFinalizeButton();

    if (availableYears.length > 0) {
        selectedYear = availableYears[0]; // Default to most recent year
        console.log(`Tournament Simulator: Defaulting to year ${selectedYear}`);
        if (elements.yearSelect) elements.yearSelect.value = selectedYear;
        await loadTeamData(selectedYear);
        renderTeamSearchResults();
    } else {
        console.warn("Tournament Simulator: No available years found during initialization. Cannot load teams.");
        if (elements.teamSelectTableBody) elements.teamSelectTableBody.innerHTML = '<tr><td colspan="7">No year data files found. Cannot load teams.</td></tr>';
        if (elements.yearSelect) elements.yearSelect.disabled = true;
        if (elements.searchInput) elements.searchInput.disabled = true;
    }
});

// --- YEAR DROPDOWN ---
async function getAvailableYearsFromManifest() {
    console.log('getAvailableYearsFromManifest: Starting to fetch available years from manifest.');
    try {
        const response = await fetch('../year_files/manifest.json');
        if (!response.ok) {
            throw new Error('Failed to load ../year_files/manifest.json');
        }
        const manifest = await response.json();
        const yearsFromManifest = manifest.available_years || [];
        
        yearsFromManifest.sort((a, b) => b - a);
        availableYears = yearsFromManifest;

    } catch (error) {
        console.error('Error getting available years from manifest for tournament page:', error);
        availableYears = [];
    }
    console.log('getAvailableYearsFromManifest: Finished. Available years loaded:', availableYears);
}

function setupYearSelector() {
    if (!elements.yearSelect) return;
    elements.yearSelect.innerHTML = ''; // Clear existing options
    if (availableYears.length === 0) {
        const option = document.createElement('option');
        option.textContent = 'No Years Available';
        option.value = '';
        elements.yearSelect.appendChild(option);
        elements.yearSelect.disabled = true;
        return;
    }
    for (let year of availableYears) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        elements.yearSelect.appendChild(option);
    }
    elements.yearSelect.addEventListener('change', async () => {
        selectedYear = elements.yearSelect.value;
        console.log(`Year changed to: ${selectedYear}`);
        await loadTeamData(selectedYear);
        renderTeamSearchResults();
    });
    console.log('setupYearSelector: Year selector populated and event listener attached.');
}

// --- TEAM DATA LOADING ---
async function loadTeamData(year) {
    console.log(`loadTeamData: Attempting to load data for year ${year}.`);
    if (!year) {
        allTeams = [];
        console.warn('loadTeamData: No year provided, allTeams cleared.');
        return;
    }
    try {
        const response = await fetch(`../year_files/debate_teams_${year}.json`);
        if (!response.ok) {
            console.error(`loadTeamData: Failed to load team data for year ${year}: ${response.statusText} (status ${response.status})`);
            allTeams = [];
        } else {
            allTeams = await response.json();
            console.log(`loadTeamData: Successfully loaded ${allTeams.length} teams for year ${year}.`);
            
            if (!Array.isArray(allTeams)) {
                console.error('loadTeamData: CRITICAL - allTeams is NOT an array after parsing JSON! Structure:', allTeams);
                allTeams = []; 
            } else {
                 // Add composite name to each team object for easier use
                allTeams.forEach(team => {
                    team.compositeName = getCompositeTeamName(team);
                });
                if (allTeams.length > 0) console.log('loadTeamData: First team with compositeName:', JSON.stringify(allTeams[0]));

                allTeams.sort((a, b) => {
                    const rankA = parseFloat(a.national_rank); // Use national_rank as on main page
                    const rankB = parseFloat(b.national_rank);
                    if (isNaN(rankA) && isNaN(rankB)) return 0;
                    if (isNaN(rankA)) return 1;
                    if (isNaN(rankB)) return -1;
                    return rankA - rankB;
                });
                console.log('loadTeamData: Teams sorted by national_rank.');
            }
        }
    } catch (error) {
        allTeams = [];
        console.error(`loadTeamData: Error loading or parsing team data for year ${year}:`, error);
    }
    console.log('loadTeamData: Exiting. Current allTeams count:', Array.isArray(allTeams) ? allTeams.length : 'Not an array');
}

// Helper to get a displayable/searchable team name
function getCompositeTeamName(team) {
    if (team && team.debater1 && team.debater1.name && team.debater2 && team.debater2.name) {
        return `${team.debater1.name} / ${team.debater2.name}`;
    }
    // Fallback if structure is unexpected, helps with debugging but shouldn't happen with valid data
    console.warn('getCompositeTeamName: Team object missing expected debater names:', team);
    return 'Unknown Team'; 
}

// --- SEARCH ---
function setupSearchListener() {
    if (!elements.searchInput) return;
    elements.searchInput.addEventListener('input', () => {
        searchQuery = elements.searchInput.value.trim().toLowerCase();
        console.log(`Search query changed: "${searchQuery}"`);
        renderTeamSearchResults();
    });
    console.log('setupSearchListener: Search listener attached.');
}

function renderTeamSearchResults() {
    if (finalized) return;
    if (!elements.teamSelectTableBody) {
        console.error("renderTeamSearchResults: teamSelectTableBody element not found!");
        return;
    }

    console.log('renderTeamSearchResults: Current tournamentRoster:', JSON.stringify(tournamentRoster.map(t => t.compositeName)));
    console.log(`renderTeamSearchResults: Called. SearchQuery: "${searchQuery}", allTeams count: ${Array.isArray(allTeams) ? allTeams.length : 'Not an array'}`);

    const results = allTeams.filter(team =>
        team.compositeName &&
        team.compositeName.toLowerCase().includes(searchQuery) &&
        !tournamentRoster.some(rt => rt.compositeName === team.compositeName)
    );
    console.log('renderTeamSearchResults: Filtered results count:', results.length);

    elements.teamSelectTableBody.innerHTML = ''; // Clear previous rows

    if (allTeams.length === 0 && selectedYear) {
        console.warn(`renderTeamSearchResults: No teams loaded for selected year ${selectedYear} to render.`);
        const row = elements.teamSelectTableBody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 7; // Match number of columns
        cell.textContent = `No teams found for ${selectedYear}. Data might be missing or empty.`;
        cell.style.fontStyle = 'italic';
        cell.style.textAlign = 'center';
    } else if (results.length === 0 && allTeams.length > 0) {
        const row = elements.teamSelectTableBody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 7;
        if (searchQuery !== '') {
            cell.textContent = 'No teams match your current search.';
        } else {
            cell.textContent = 'All available teams are in the roster or no teams to display.';
        }
        cell.style.fontStyle = 'italic';
        cell.style.textAlign = 'center';
        console.log('renderTeamSearchResults: No results to display, showing appropriate message.');
    } else if (results.length === 0 && allTeams.length === 0 && selectedYear) { // Added selectedYear check
        const row = elements.teamSelectTableBody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 7;
        cell.textContent = `No teams available for ${selectedYear}.`;
        cell.style.fontStyle = 'italic';
        cell.style.textAlign = 'center';
    }

    for (let team of results) {
        const row = elements.teamSelectTableBody.insertRow();
        row.className = 'clickable'; // For hover effects from main styles.css
        row.dataset.teamCompositeName = team.compositeName; 

        // Populate cells according to main page structure
        let cellTeam = row.insertCell();
        cellTeam.textContent = team.compositeName;
        cellTeam.title = team.compositeName; // For potential tooltip like main page

        let cellState = row.insertCell();
        cellState.textContent = team.state || 'N/A';
        cellState.title = team.state || 'N/A';

        let cellClub = row.insertCell();
        // Assuming club might be on debater1 or could be a team property
        // Based on main page it's team.debater1.debate_club
        cellClub.textContent = (team.debater1 && team.debater1.debate_club) || 'N/A';
        cellClub.title = (team.debater1 && team.debater1.debate_club) || 'N/A';

        let cellRank = row.insertCell();
        cellRank.textContent = team.national_rank || 'N/A';

        let cellPts = row.insertCell();
        cellPts.textContent = team.rank_points !== undefined ? (Math.round(parseFloat(team.rank_points) * 100) / 100) : 'N/A';

        let cellWins = row.insertCell();
        cellWins.textContent = team.total_wins !== undefined ? team.total_wins : 'N/A';

        let cellLosses = row.insertCell();
        cellLosses.textContent = team.total_losses !== undefined ? team.total_losses : 'N/A';

        row.addEventListener('click', () => {
            const fullTeamObject = allTeams.find(t => t.compositeName === row.dataset.teamCompositeName);
            if (fullTeamObject && !tournamentRoster.some(rt => rt.compositeName === fullTeamObject.compositeName)) {
                tournamentRoster.push(fullTeamObject);
                console.log(`Added to roster: ${fullTeamObject.compositeName}. Roster size: ${tournamentRoster.length}`);
                renderTeamSearchResults(); 
                renderTournamentRoster();
                updateFinalizeButton();
            } else if (tournamentRoster.some(rt => rt.compositeName === (fullTeamObject ? fullTeamObject.compositeName : 'fallback'))){
                 console.log(`Team already in roster: ${fullTeamObject ? fullTeamObject.compositeName : 'N/A'}`);
            } else {
                console.error("Could not find full team object or team already in roster for:", row.dataset.teamCompositeName);
            }
        });
    }
    console.log('renderTeamSearchResults: Rendering complete. Row count in search results table:', elements.teamSelectTableBody.rows.length);
}

// --- ROSTER ---
function renderTournamentRoster() {
    if (!elements.tournamentRoster) return;
    elements.tournamentRoster.innerHTML = '';
    for (let team of tournamentRoster) {
        const li = document.createElement('li');
        li.textContent = team.compositeName; // Display composite name
        li.className = 'clickable';
        li.addEventListener('click', () => {
            tournamentRoster = tournamentRoster.filter(t => t.compositeName !== team.compositeName);
            console.log(`Removed from roster: ${team.compositeName}. Roster size: ${tournamentRoster.length}`);
            renderTeamSearchResults(); 
            renderTournamentRoster();
            updateFinalizeButton();
        });
        elements.tournamentRoster.appendChild(li);
    }
    console.log('renderTournamentRoster: Roster display updated.');
}

// --- FINALIZE BUTTON ---
function setupFinalizeButton() {
    if (!elements.finalizeBtn) return;
    elements.finalizeBtn.addEventListener('click', () => {
        if (tournamentRoster.length > 1) {
            finalized = true;
            console.log('Finalize button clicked. Roster finalized.');
            showFinalizedRoster();
        } else {
            console.log('Finalize button clicked, but roster size is not > 1.');
        }
    });
    console.log('setupFinalizeButton: Finalize button listener attached.');
}

function updateFinalizeButton() {
    if (!elements.finalizeBtn) return;
    elements.finalizeBtn.disabled = tournamentRoster.length <= 1;
    console.log(`updateFinalizeButton: Finalize button disabled state: ${elements.finalizeBtn.disabled}`);
}

// --- FINALIZED ROSTER VIEW ---
function showFinalizedRoster() {
    console.log('showFinalizedRoster: Preparing to display finalized roster on current page.');
    if (elements.container) elements.container.style.display = 'flex'; 
    if (elements.teamSelectPanel) elements.teamSelectPanel.style.display = 'none';
    if (elements.rosterPanel) elements.rosterPanel.style.display = 'none';
    
    const finalizeContainer = document.querySelector('.finalize-container');
    if (finalizeContainer) finalizeContainer.style.display = 'none';

    const mainElement = document.querySelector('main');
    if (!mainElement) {
        console.error('showFinalizedRoster: <main> element not found!');
        return;
    }

    const existingCenteredRoster = document.querySelector('.centered-roster');
    if (existingCenteredRoster) existingCenteredRoster.remove();

    const centerDiv = document.createElement('div');
    centerDiv.className = 'centered-roster';
    centerDiv.innerHTML = '<h2>Finalized Team Roster</h2>';
    const ul = document.createElement('ul');
    ul.className = 'team-list';
    for (let team of tournamentRoster) {
        const li = document.createElement('li');
        li.textContent = team.compositeName; 
        ul.appendChild(li);
    }
    centerDiv.appendChild(ul);
    mainElement.appendChild(centerDiv); 
    console.log('showFinalizedRoster: Finalized roster displayed on current page.');
}

document.addEventListener('DOMContentLoaded', function() {
    // Test button functionality
    const testButton = document.getElementById('testButton');
    const testResult = document.getElementById('testResult');

    if (testButton && testResult) {
        testButton.addEventListener('click', function() {
            testResult.textContent = 'JavaScript is working!';
            testResult.className = 'success';
            
            // Remove the success message after 3 seconds
            setTimeout(() => {
                testResult.textContent = '';
                testResult.className = '';
            }, 3000);
        });
    }
}); 