/**
 * Performance Chart Initialization for Robby's Picks Dashboard
 * This is a consolidated script that handles chart rendering
 */

document.addEventListener('DOMContentLoaded', function() {
    initializePerformanceChart();
    
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }
});

function initializePerformanceChart() {
    // Get chart data from the container
    const chartDataElement = document.getElementById('chart-data');
    if (!chartDataElement) {
        console.error("Chart data element not found");
        displayChartError("Chart data element not found");
        return;
    }

    try {
        // Parse the data
        const dates = JSON.parse(chartDataElement.dataset.dates || '[]');
        const locks = JSON.parse(chartDataElement.dataset.locks || '[]');
        const rocks = JSON.parse(chartDataElement.dataset.rocks || '[]');
        const rates = JSON.parse(chartDataElement.dataset.rates || '[]');
        
        console.log("Chart data loaded:", {
            dates: dates,
            locks: locks, 
            rocks: rocks,
            rates: rates
        });
        
        // Validate parsed data
        if (dates.length === 0 || locks.length === 0 || rocks.length === 0 || rates.length === 0) {
            console.warn("No chart data available");
            displayNoDataMessage();
            return;
        }
        
        // Get the chart type toggle element
        const chartTypeToggle = document.getElementById('chartTypeToggle');
        const showRate = chartTypeToggle ? chartTypeToggle.checked : false;
        
        // Create ApexCharts configuration
        const options = {
            series: showRate ? 
                [{ name: 'Success Rate (%)', data: rates, type: 'line', color: '#1a237e' }] : 
                [
                    { name: 'Locks', data: locks, type: 'column', color: '#22c55e' },
                    { name: 'Rocks', data: rocks, type: 'column', color: '#ef4444' }
                ],
            chart: {
                height: 300,
                type: showRate ? 'line' : 'bar',
                stacked: !showRate,
                toolbar: {
                    show: true
                },
                animations: {
                    enabled: true,
                    easing: 'easeinout',
                    speed: 800
                }
            },
            plotOptions: {
                bar: {
                    horizontal: false,
                    columnWidth: '55%',
                    borderRadius: 4
                },
            },
            dataLabels: {
                enabled: false
            },
            stroke: {
                width: showRate ? 3 : [0, 0],
                curve: 'smooth'
            },
            xaxis: {
                categories: dates,
                labels: {
                    rotate: -45,
                    style: {
                        fontSize: '11px'
                    }
                }
            },
            yaxis: {
                min: 0,
                max: showRate ? 100 : undefined,
                labels: {
                    formatter: function(val) {
                        return showRate ? val.toFixed(1) + '%' : Math.round(val);
                    }
                }
            },
            colors: showRate ? ['#1a237e'] : ['#22c55e', '#ef4444'],
            legend: {
                position: 'top',
                horizontalAlign: 'right'
            },
            fill: {
                opacity: 1
            },
            grid: {
                borderColor: '#e0e0e0',
                row: {
                    colors: ['#f5f5f5', 'transparent']
                }
            },
            tooltip: {
                y: {
                    formatter: function(val) {
                        return showRate ? val.toFixed(1) + '%' : Math.round(val);
                    }
                }
            }
        };
        
        // Create the chart
        const chartElement = document.getElementById('performance-chart');
        if (chartElement) {
            const chart = new ApexCharts(chartElement, options);
            chart.render();
            
            // Handle toggle change if the toggle exists
            if (chartTypeToggle) {
                chartTypeToggle.addEventListener('change', function() {
                    const showRateToggled = this.checked;
                    
                    if (showRateToggled) {
                        chart.updateOptions({
                            series: [{ name: 'Success Rate (%)', data: rates, type: 'line' }],
                            colors: ['#1a237e'],
                            stroke: { width: 3, curve: 'smooth' },
                            chart: { type: 'line', stacked: false },
                            yaxis: {
                                max: 100,
                                labels: {
                                    formatter: function(val) {
                                        return val.toFixed(1) + '%';
                                    }
                                }
                            }
                        });
                    } else {
                        chart.updateOptions({
                            series: [
                                { name: 'Locks', data: locks, type: 'column' },
                                { name: 'Rocks', data: rocks, type: 'column' }
                            ],
                            colors: ['#22c55e', '#ef4444'],
                            stroke: { width: [0, 0] },
                            chart: { type: 'bar', stacked: true },
                            yaxis: {
                                max: undefined,
                                labels: {
                                    formatter: function(val) {
                                        return Math.round(val);
                                    }
                                }
                            }
                        });
                    }
                });
            }
        } else {
            console.error("Chart container element not found");
        }
    } catch (error) {
        console.error("Error initializing chart:", error);
        displayChartError("Error initializing chart: " + error.message);
    }
}

function displayChartError(message) {
    const chartContainer = document.getElementById('performance-chart');
    if (chartContainer) {
        chartContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>${message}
            </div>
            <div class="text-center mt-3">
                <button class="btn btn-sm btn-outline-primary" onclick="window.location.reload()">
                    <i class="fas fa-sync-alt me-1"></i>Refresh
                </button>
            </div>
        `;
    }
}

function displayNoDataMessage() {
    const chartContainer = document.getElementById('performance-chart');
    if (chartContainer) {
        chartContainer.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>No performance data available yet.
            </div>
        `;
    }
}