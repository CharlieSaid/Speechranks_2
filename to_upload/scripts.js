/******************************************
 * GLOBAL STATE
 ******************************************/

// Main data store
let allTeams = [];  // All loaded teams
let currentTeam = null;  // Currently selected team

// Filter and sort state
let activeFilters = {
    state: null,
    club: null
};
let currentSort = {
    column: 'rank',
    ascending: true
};

// Chart state
let currentMetric = 'overall';
let performanceChart = null;  // Store chart instance globally

// Year range
let YEARS = {
    start: null,
    end: null,
    list: []
};

/******************************************
 * DOM ELEMENTS
 ******************************************/

const elements = {
    // Left pane elements
    yearSelect: document.getElementById('yearSelect'),
    teamsTable: document.getElementById('teamsTable'),
    teamsBody: document.getElementById('teamsTableBody'),
    filterContainer: document.getElementById('activeFilters'),
    searchInput: document.getElementById('searchInput'),
    
    // Right pane elements
    noTeamSelected: document.getElementById('noTeamSelected'),
    teamInfo: document.getElementById('teamInfo'),
    selectedTeamName: document.getElementById('selectedTeamName'),
    tournamentsBody: document.getElementById('tournamentsTableBody'),
    rightPanel: document.getElementById('teamDetails'),
    
    // Modal
    modal: document.getElementById('aboutModal')
};

/******************************************
 * PAGE INITIALIZATION
 ******************************************/

async function initializePage() {
    await getAvailableYears();
    setupYearSelector();
    setupSortingListeners();
    setupSearchListener();
    setupModalHandlers();
    setupChartControls();
    loadInitialData();
}

// Find available year files
async function getAvailableYears() {
    try {
        const response = await fetch('year_files/manifest.json');
        if (!response.ok) {
            throw new Error('Failed to load year_files/manifest.json');
        }
        const manifest = await response.json();
        const years = manifest.available_years || [];
        
        // Sort years numerically, just in case they aren't in the manifest
        years.sort((a, b) => a - b);
        
        if (years.length > 0) {
            YEARS.start = Math.min(...years); // Or years[0] if pre-sorted ascending
            YEARS.end = Math.max(...years);   // Or years[years.length - 1] if pre-sorted
            // Store the full list if needed by setupYearSelector or other functions
            YEARS.list = years; 
        } else {
            console.warn('No available years found in manifest.json or manifest is empty.');
            YEARS.list = [];
        }
    } catch (error) {
        console.error('Error getting available years from manifest:', error);
        YEARS.start = null;
        YEARS.end = null;
        YEARS.list = [];
    }
}

/******************************************
 * LEFT PANE - TEAM LIST FUNCTIONALITY 
 ******************************************/

// Load and display teams for a year
async function loadTeamData(year) {
    try {
        const response = await fetch(`year_files/debate_teams_${year}.json`);
        if (!response.ok) throw new Error('Failed to load team data');
        
        allTeams = await response.json();
        resetFilters();
        displayTeamList();
    } catch (error) {
        console.error('Error loading team data:', error);
    }
}

// Display teams in the left pane table
function displayTeamList() {
    const filteredTeams = filterTeams(allTeams);
    const sortedTeams = sortTeams(filteredTeams);
    
    elements.teamsBody.innerHTML = '';
    sortedTeams.forEach(team => {
        const row = createTeamRow(team);
        elements.teamsBody.appendChild(row);
    });
}

// Create a row for a team
function createTeamRow(team) {
    const row = document.createElement('tr');
    row.innerHTML = `
        <td title="${team.debater1.name} / ${team.debater2.name}">
            ${team.debater1.name} / ${team.debater2.name}
        </td>
        <td class="clickable state-cell" title="${team.state}">
            ${team.state || 'None'}
        </td>
        <td class="clickable club-cell" title="${team.debater1.debate_club}">
            ${team.debater1.debate_club || 'None'}
        </td>
        <td>${team.national_rank || 'None'}</td>
        <td>${Math.round(team.rank_points * 100) / 100 || '0'}</td>
        <td>${team.total_wins || '0'}</td>
        <td>${team.total_losses || '0'}</td>
    `;
    
    // Add click handlers
    row.querySelector('.state-cell').addEventListener('click', (e) => {
        e.stopPropagation();
        toggleFilter('state', team.state);
    });
    
    row.querySelector('.club-cell').addEventListener('click', (e) => {
        e.stopPropagation();
        toggleFilter('club', team.debater1.debate_club);
    });
    
    row.addEventListener('click', () => showTeamDetails(team));
    
    return row;
}

// Sorting functions
function sortTeams(teams) {
    return [...teams].sort((a, b) => {
        const getValue = (team) => {
            switch(currentSort.column) {
                case 'team': return `${team.debater1.name} ${team.debater2.name}`;
                case 'state': return team.state || '';
                case 'club': return team.debater1.debate_club || '';
                case 'rank': return parseInt(team.national_rank) || Infinity;
                case 'points': return parseFloat(team.rank_points) || 0;
                case 'wins': return parseInt(team.total_wins) || 0;
                case 'losses': return parseInt(team.total_losses) || 0;
                default: return '';
            }
        };

        const valueA = getValue(a);
        const valueB = getValue(b);
        
        return (valueA < valueB ? -1 : valueA > valueB ? 1 : 0) 
            * (currentSort.ascending ? 1 : -1);
    });
}

// Filter management
function resetFilters() {
    activeFilters = {
        state: null,
        club: null
    };
    
    // Clear filter display
    elements.filterContainer.innerHTML = '';
    
    // Clear search
    elements.searchInput.value = '';
    
    // Refresh display
    displayTeamList();
}

function toggleFilter(type, value) {
    if (activeFilters[type] === value) {
        activeFilters[type] = null;
    } else {
        activeFilters[type] = value;
    }
    
    updateFilterDisplay();
    displayTeamList();
}

function updateFilterDisplay() {
    elements.filterContainer.innerHTML = '';
    
    // Create filter tags
    Object.entries(activeFilters).forEach(([type, value]) => {
        if (value) {
            const tag = document.createElement('span');
            tag.className = 'filter-tag';
            tag.innerHTML = `${type}: ${value} <span class="remove">×</span>`;
            
            tag.querySelector('.remove').addEventListener('click', () => {
                activeFilters[type] = null;
                updateFilterDisplay();
                displayTeamList();
            });
            
            elements.filterContainer.appendChild(tag);
        }
    });
}

function filterTeams(teams) {
    let filtered = teams;
    const searchTerm = elements.searchInput.value.toLowerCase();
    
    if (searchTerm) {
        filtered = filtered.filter(team => 
            team.debater1.name.toLowerCase().includes(searchTerm) ||
            team.debater2.name.toLowerCase().includes(searchTerm)
        );
    }
    
    if (activeFilters.state) {
        filtered = filtered.filter(team => team.state === activeFilters.state);
    }
    
    if (activeFilters.club) {
        filtered = filtered.filter(team => 
            team.debater1.debate_club === activeFilters.club ||
            team.debater2.debate_club === activeFilters.club
        );
    }
    
    return filtered;
}

/******************************************
 * RIGHT PANE - TEAM DETAILS FUNCTIONALITY
 ******************************************/

function showTeamDetails(team) {
    currentTeam = team;
    
    // Update visibility
    elements.noTeamSelected.style.display = 'none';
    elements.teamInfo.style.display = 'block';
    elements.rightPanel.scrollTop = 0;
    
    // Update names
    elements.selectedTeamName.textContent = `${team.debater1.name} / ${team.debater2.name}`;
    document.getElementById('debater1Name').textContent = team.debater1.name;
    document.getElementById('debater2Name').textContent = team.debater2.name;
    document.getElementById('debater1SpeechName').textContent = team.debater1.name;
    document.getElementById('debater2SpeechName').textContent = team.debater2.name;
    
    // Update events
    updateDebaterEvents('debater1Events', team.debater1.debate_events);
    updateDebaterEvents('debater2Events', team.debater2.debate_events);
    updateSpeechEvents('debater1Speech', team.debater1.speech_events);
    updateSpeechEvents('debater2Speech', team.debater2.speech_events);
    
    // Update performance data
    updatePerformanceChart(team);
    updateTournamentsTable(team);
}

// Update events tables
function updateDebaterEvents(tableId, events) {
    const tbody = document.getElementById(tableId).getElementsByTagName('tbody')[0];
    tbody.innerHTML = '';
    
    if (!events || events.length === 0) {
        const row = tbody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 5;
        cell.textContent = 'No other events';
        return;
    }

    // Filter for debate events only and exclude current team
    const debateEvents = events.filter(event => {
        // Check if it's a debate event
        const isDebateEvent = event.name.includes('Debate') || event.name.includes('Parliamentary');
        
        // Check if this event matches current team
        const isCurrentTeam = currentTeam && 
            event.points === currentTeam.rank_points &&
            ((event.partner === currentTeam.debater2.name) || 
             (event.partner === currentTeam.debater1.name));
        
        return isDebateEvent && !isCurrentTeam;
    });

    if (debateEvents.length === 0) {
        const row = tbody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 5;
        cell.textContent = 'No other events';
        return;
    }

    debateEvents.forEach(event => {
        const row = tbody.insertRow();
        row.innerHTML = `
            <td>${phrase_shorthand(event.name)}</td>
            <td>${event.rank || '-'}</td>
            <td>${event.points || '-'}</td>
            <td>${event.partner || '-'}</td>
            <td>${'✓'.repeat(event.checkmarks || 0)}</td>
        `;
    });
}

function updateSpeechEvents(tableId, events) {
    const tbody = document.getElementById(tableId).getElementsByTagName('tbody')[0];
    tbody.innerHTML = '';
    
    if (!events || events.length === 0) {
        const row = tbody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 4;
        cell.textContent = 'No speech events';
        return;
    }

    // Filter for speech events only
    const speechEvents = events.filter(event => 
        !event.name.includes('Debate') && !event.name.includes('Parliamentary')
    );

    if (speechEvents.length === 0) {
        const row = tbody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 4;
        cell.textContent = 'No speech events';
        return;
    }

    speechEvents.forEach(event => {
        const row = tbody.insertRow();
        row.innerHTML = `
            <td>${event.name}</td>
            <td>${event.rank || '-'}</td>
            <td>${event.points || '-'}</td>
            <td>${event.checkmarks || '0'}</td>
        `;
    });
}

// Update tournaments table
function updateTournamentsTable(team) {
    elements.tournamentsBody.innerHTML = '';
    
    if (!team.tournaments) return;
    
    team.tournaments.forEach(tournament => {
        const row = elements.tournamentsBody.insertRow();
        row.innerHTML = `
            <td>${phrase_shorthand(tournament.name || 'Unknown')}</td>
            <td>${tournament.place || 'Unknown'}</td>
            <td>${tournament.prelim_record || 'Unknown'}</td>
            <td>${tournament.overall_record || 'Unknown'}</td>
            <td>${tournament.points || '0'}</td>
            <td>${'✓'.repeat(tournament.checkmarks)}</td>
        `;
    });
}

/******************************************
 * CHART FUNCTIONALITY
 ******************************************/

function updatePerformanceChart(team) {
    const ctx = document.getElementById('teamChart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (performanceChart) {
        performanceChart.destroy();
    }
    
    // Prepare data
    const chartData = prepareChartData(team);
    
    // Create new chart
    performanceChart = new Chart(ctx, createChartConfig(chartData));
}

function prepareChartData(team) {
    return team.tournaments.map(t => {
        let value = 0;
        switch (currentMetric) {
            case 'points':
                value = parseFloat(t.points) || 0;
                break;
            case 'rank':
                value = t.place ? 100 - parseInt(t.place) : 0;
                break;
            case 'prelims':
                const [pWins, pLosses] = t.prelim_record.split('-').map(n => parseInt(n) || 0);
                value = pWins + pLosses > 0 ? (pWins / (pWins + pLosses)) * 100 : 0;
                break;
            case 'overall':
                const [oWins, oLosses] = t.overall_record.split('-').map(n => parseInt(n) || 0);
                value = oWins + oLosses > 0 ? (oWins / (oWins + oLosses)) * 100 : 0;
                break;
        }
        return { name: t.name, value: value };
    });
}

function createChartConfig(data) {
    const yAxisLabels = {
        points: 'Points',
        rank: 'Rank (inverted)',
        prelims: 'Prelim Win %',
        overall: 'Overall Win %'
    };

    return {
        type: 'line',
        data: {
            labels: data.map(t => t.name),
            datasets: [{
                label: yAxisLabels[currentMetric],
                data: data.map(t => t.value),
                borderColor: 'rgb(255, 0, 0)',
                backgroundColor: 'rgba(255, 0, 0, 0.1)',
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: false },
                y: {
                    beginAtZero: true,
                    title: { 
                        display: true, 
                        text: yAxisLabels[currentMetric]
                    },
                    max: currentMetric === 'points' ? undefined : 100
                }
            }
        }
    };
}

/******************************************
 * SETUP AND EVENT HANDLERS
 ******************************************/

function setupYearSelector() {
    if (!elements.yearSelect) return;
    elements.yearSelect.innerHTML = ''; // Clear existing options

    if (!YEARS.list || YEARS.list.length === 0) {
        const option = document.createElement('option');
        option.textContent = 'No Years Available';
        option.disabled = true;
        elements.yearSelect.appendChild(option);
        return;
    }

    // Sort years in descending order for display (newest first)
    const displayYears = [...YEARS.list].sort((a, b) => b - a);

    displayYears.forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        elements.yearSelect.appendChild(option);
    });

    // Optional: Select the most recent year by default
    if (displayYears.length > 0) {
        elements.yearSelect.value = displayYears[0];
        loadTeamData(displayYears[0]); // Load data for the default selected year
    }

    elements.yearSelect.addEventListener('change', (event) => {
        loadTeamData(event.target.value);
    });
}

function setupSortingListeners() {
    elements.teamsTable.querySelectorAll('th[data-sort]').forEach(header => {
        header.addEventListener('click', () => {
            const column = header.dataset.sort;
            
            // Update sort direction
            if (column === currentSort.column) {
                currentSort.ascending = !currentSort.ascending;
            } else {
                currentSort.column = column;
                currentSort.ascending = true;
            }
            
            // Update sort indicators
            elements.teamsTable.querySelectorAll('th').forEach(h => {
                h.classList.remove('sort-asc', 'sort-desc');
            });
            header.classList.add(currentSort.ascending ? 'sort-asc' : 'sort-desc');
            
            // Refresh display
            displayTeamList();
        });
    });
}

function setupChartControls() {
    document.querySelectorAll('.chart-toggle').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.chart-toggle').forEach(b => 
                b.classList.remove('active'));
            button.classList.add('active');
            currentMetric = button.dataset.metric;
            if (currentTeam) {
                updatePerformanceChart(currentTeam);
            }
        });
    });
}

function setupSearchListener() {
    elements.searchInput.addEventListener('input', () => displayTeamList());
}

function setupModalHandlers() {
    const aboutBtn = document.getElementById('aboutBtn');
    const closeBtn = document.getElementsByClassName('close')[0];

    aboutBtn.onclick = () => elements.modal.style.display = 'block';
    closeBtn.onclick = () => elements.modal.style.display = 'none';
    window.onclick = (event) => {
        if (event.target == elements.modal) {
            elements.modal.style.display = 'none';
        }
    };
}

function loadInitialData() {
    elements.yearSelect.value = YEARS.end;
    currentSort.column = 'rank';
    currentSort.ascending = true;
    elements.teamsTable.querySelector('th[data-sort="rank"]').classList.add('sort-asc');
    
    // Set the initial active chart toggle
    document.querySelector('[data-metric="overall"]').classList.add('active');
    document.querySelector('[data-metric="points"]').classList.remove('active');
    
    loadTeamData(YEARS.end);
}

// Start everything when the page loads
document.addEventListener('DOMContentLoaded', initializePage);

// Add this to your utility functions section
function phrase_shorthand(eventName) {
    return eventName
        .replace('Team Policy Debate', 'TP')
        .replace('Lincoln Douglas Value Debate', 'LD')
        .replace('Parliamentary Debate', 'Parli');
} 