// Air Pollution Analysis & Forecasting System - JavaScript

let trendChart = null;
let forecastChart = null;
let forecastBarChart = null;
let availableCities = [];
let currentForecastData = null;

// Load available cities on page load
window.addEventListener('DOMContentLoaded', async function() {
    await loadCities();
});

// Load cities from API
async function loadCities() {
    try {
        const response = await fetch('/api/cities');
        const data = await response.json();
        
        if (data.cities) {
            availableCities = data.cities;
            
            // Populate all city dropdowns
            const dropdowns = ['city-select-overview', 'city-select-trends', 'city-select-forecast'];
            dropdowns.forEach(dropdownId => {
                const dropdown = document.getElementById(dropdownId);
                if (dropdown) {
                    dropdown.innerHTML = '<option value="">All Cities</option>';
                    data.cities.forEach(city => {
                        const option = document.createElement('option');
                        option.value = city;
                        option.textContent = city;
                        dropdown.appendChild(option);
                    });
                }
            });
        }
    } catch (error) {
        console.error('Error loading cities:', error);
        // Set default option if cities fail to load
        const dropdowns = ['city-select-overview', 'city-select-trends', 'city-select-forecast'];
        dropdowns.forEach(dropdownId => {
            const dropdown = document.getElementById(dropdownId);
            if (dropdown) {
                dropdown.innerHTML = '<option value="">All Cities</option>';
            }
        });
    }
}

// Get selected city from a dropdown
function getSelectedCity(dropdownId) {
    const dropdown = document.getElementById(dropdownId);
    return dropdown ? dropdown.value : '';
}

// Tab switching functionality
function showTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(tab => tab.classList.remove('active'));
    
    // Remove active class from all buttons
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(btn => btn.classList.remove('active'));
    
    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    
    // Add active class to clicked button
    event.target.classList.add('active');
}

// Load and display data overview
async function loadData() {
    const statusDiv = document.getElementById('data-status');
    const statsContainer = document.getElementById('stats-container');
    const city = getSelectedCity('city-select-overview');
    
    statusDiv.className = 'status-message info';
    statusDiv.textContent = 'Loading data...';
    statusDiv.style.display = 'block';
    statsContainer.innerHTML = '';
    
    try {
        const response = await fetch('/api/load-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ city: city || null })
        });
        
        const data = await response.json();
        
        if (data.success) {
            statusDiv.className = 'status-message success';
            statusDiv.textContent = data.message;
            
            // Display statistics
            const stats = data.stats;
            const cityLabel = stats.city ? ` (${stats.city})` : '';
            statsContainer.innerHTML = `
                <div class="stat-card">
                    <h3>City</h3>
                    <div class="value" style="font-size: 1.2em;">${stats.city || 'All Cities'}</div>
                </div>
                <div class="stat-card">
                    <h3>Total Records</h3>
                    <div class="value">${stats.total_records.toLocaleString()}</div>
                </div>
                <div class="stat-card">
                    <h3>Date Range</h3>
                    <div class="value" style="font-size: 1.2em;">${stats.date_range.start}<br>to<br>${stats.date_range.end}</div>
                </div>
                <div class="stat-card">
                    <h3>Average AQI</h3>
                    <div class="value">${stats.aqi_stats.mean.toFixed(2)}</div>
                </div>
                <div class="stat-card">
                    <h3>Min AQI</h3>
                    <div class="value">${stats.aqi_stats.min.toFixed(2)}</div>
                </div>
                <div class="stat-card">
                    <h3>Max AQI</h3>
                    <div class="value">${stats.aqi_stats.max.toFixed(2)}</div>
                </div>
                <div class="stat-card">
                    <h3>Std Deviation</h3>
                    <div class="value">${stats.aqi_stats.std.toFixed(2)}</div>
                </div>
            `;
        } else {
            throw new Error(data.error || 'Failed to load data');
        }
    } catch (error) {
        statusDiv.className = 'status-message error';
        statusDiv.textContent = 'Error: ' + error.message;
    }
}

// Load and display daily trend
async function loadDailyTrend() {
    try {
        const city = getSelectedCity('city-select-trends');
        const url = city ? `/api/daily-trend?city=${encodeURIComponent(city)}` : '/api/daily-trend';
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.error) {
            alert('Error: ' + data.error);
            return;
        }
        
        // Destroy existing chart if it exists
        if (trendChart) {
            trendChart.destroy();
        }
        
        // Create new chart
        const ctx = document.getElementById('trendChart').getContext('2d');
        const cityLabel = data.city ? ` - ${data.city}` : '';
        trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [{
                    label: `Daily AQI${cityLabel}`,
                    data: data.aqi_values,
                    borderColor: 'rgb(102, 126, 234)',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `Daily AQI Trend${cityLabel}`,
                        font: {
                            size: 18
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: 'AQI Value'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Date'
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                }
            }
        });
    } catch (error) {
        alert('Error loading daily trend: ' + error.message);
    }
}

// Load and display monthly trend
async function loadMonthlyTrend() {
    try {
        const city = getSelectedCity('city-select-trends');
        const url = city ? `/api/monthly-trend?city=${encodeURIComponent(city)}` : '/api/monthly-trend';
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.error) {
            alert('Error: ' + data.error);
            return;
        }
        
        // Destroy existing chart if it exists
        if (trendChart) {
            trendChart.destroy();
        }
        
        // Create new chart
        const ctx = document.getElementById('trendChart').getContext('2d');
        const cityLabel = data.city ? ` - ${data.city}` : '';
        trendChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.dates,
                datasets: [{
                    label: `Monthly Average AQI${cityLabel}`,
                    data: data.aqi_values,
                    backgroundColor: 'rgba(102, 126, 234, 0.7)',
                    borderColor: 'rgb(102, 126, 234)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `Monthly AQI Trend${cityLabel}`,
                        font: {
                            size: 18
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: 'Average AQI Value'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Month'
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                }
            }
        });
    } catch (error) {
        alert('Error loading monthly trend: ' + error.message);
    }
}

// Generate and display forecast
async function generateForecast() {
    const statusDiv = document.getElementById('forecast-status');
    const forecastDays = parseInt(document.getElementById('forecast-days').value) || 30;
    const city = getSelectedCity('city-select-forecast');
    
    statusDiv.className = 'status-message info';
    statusDiv.textContent = 'Generating forecast... This may take a few moments.';
    statusDiv.style.display = 'block';
    
    try {
        const response = await fetch('/api/forecast', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ days: forecastDays, city: city || null })
        });
        
        const data = await response.json();
        
        if (data.error) {
            statusDiv.className = 'status-message error';
            statusDiv.textContent = 'Error: ' + data.error;
            return;
        }
        
        statusDiv.className = 'status-message success';
        const cityLabel = data.city ? ` for ${data.city}` : '';
        statusDiv.textContent = `Forecast generated successfully for ${forecastDays} days${cityLabel}.`;
        
        // Store forecast data for table and charts
        currentForecastData = data;
        
        // Populate forecast table
        populateForecastTable(data);
        
        // Show table container
        document.getElementById('forecast-table-container').style.display = 'block';
        
        // Destroy existing charts if they exist
        if (forecastChart) {
            forecastChart.destroy();
        }
        if (forecastBarChart) {
            forecastBarChart.destroy();
        }
        
        // Prepare data for charts
        const allDates = [...data.historical.dates, ...data.forecast.dates];
        const historicalData = [...data.historical.aqi_values, ...new Array(data.forecast.dates.length).fill(null)];
        const forecastData = [...new Array(data.historical.dates.length).fill(null), ...data.forecast.aqi_values];
        const lowerBound = [...new Array(data.historical.dates.length).fill(null), ...data.forecast.lower_bound];
        const upperBound = [...new Array(data.historical.dates.length).fill(null), ...data.forecast.upper_bound];
        
        // Create line chart
        const ctx = document.getElementById('forecastChart').getContext('2d');
        forecastChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: allDates,
                datasets: [
                    {
                        label: `Historical AQI${cityLabel}`,
                        data: historicalData,
                        borderColor: 'rgb(102, 126, 234)',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4
                    },
                    {
                        label: 'Forecasted AQI',
                        data: forecastData,
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.4
                    },
                    {
                        label: 'Lower Bound',
                        data: lowerBound,
                        borderColor: 'rgba(255, 99, 132, 0.3)',
                        backgroundColor: 'rgba(255, 99, 132, 0.05)',
                        borderWidth: 1,
                        borderDash: [3, 3],
                        fill: '+1',
                        tension: 0.4,
                        pointRadius: 0
                    },
                    {
                        label: 'Upper Bound',
                        data: upperBound,
                        borderColor: 'rgba(255, 99, 132, 0.3)',
                        backgroundColor: 'rgba(255, 99, 132, 0.05)',
                        borderWidth: 1,
                        borderDash: [3, 3],
                        fill: false,
                        tension: 0.4,
                        pointRadius: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `AQI Forecast (Next ${forecastDays} Days)${cityLabel}`,
                        font: {
                            size: 18
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: 'AQI Value'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Date'
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                }
            }
        });
        
        // Create bar chart for forecast values only
        const barCtx = document.getElementById('forecastBarChart').getContext('2d');
        forecastBarChart = new Chart(barCtx, {
            type: 'bar',
            data: {
                labels: data.forecast.dates,
                datasets: [{
                    label: 'Forecasted AQI',
                    data: data.forecast.aqi_values,
                    backgroundColor: 'rgba(255, 99, 132, 0.7)',
                    borderColor: 'rgb(255, 99, 132)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `Forecasted AQI Values (Bar Chart)${cityLabel}`,
                        font: {
                            size: 18
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: 'AQI Value'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Date'
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                }
            }
        });
        
        // Show line chart by default
        showForecastChart('line');
        
    } catch (error) {
        statusDiv.className = 'status-message error';
        statusDiv.textContent = 'Error generating forecast: ' + error.message;
    }
}

// Populate forecast table with values
function populateForecastTable(data) {
    const tableBody = document.getElementById('forecast-table-body');
    tableBody.innerHTML = '';
    
    // Create table rows for each forecast value
    for (let i = 0; i < data.forecast.dates.length; i++) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${data.forecast.dates[i]}</td>
            <td>${data.forecast.aqi_values[i].toFixed(2)}</td>
            <td>${data.forecast.lower_bound[i].toFixed(2)}</td>
            <td>${data.forecast.upper_bound[i].toFixed(2)}</td>
        `;
        tableBody.appendChild(row);
    }
}

// Toggle between line and bar chart
function showForecastChart(chartType) {
    const lineContainer = document.getElementById('line-chart-container');
    const barContainer = document.getElementById('bar-chart-container');
    const buttons = document.querySelectorAll('.chart-type-toggle .btn-secondary');
    
    // Update button states
    buttons.forEach(btn => {
        if (btn.textContent.includes('Line') && chartType === 'line') {
            btn.classList.add('active');
        } else if (btn.textContent.includes('Bar') && chartType === 'bar') {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    if (chartType === 'line') {
        lineContainer.style.display = 'block';
        barContainer.style.display = 'none';
    } else if (chartType === 'bar') {
        lineContainer.style.display = 'none';
        barContainer.style.display = 'block';
    }
}



