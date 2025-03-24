// Chart initialization for performance trends
document.addEventListener('DOMContentLoaded', function() {
    // Get chart data from the hidden div
    const chartDataElement = document.getElementById('chart-data');
    if (!chartDataElement) {
        console.error("Chart data element not found");
        displayChartError("Chart data element not found");
        return;
    }

    try {
        // Parse the data
        const datesJSON = chartDataElement.getAttribute('data-dates');
        const locksJSON = chartDataElement.getAttribute('data-locks');
        const rocksJSON = chartDataElement.getAttribute('data-rocks');
        const ratesJSON = chartDataElement.getAttribute('data-rates');

        // Validate data exists
        if (!datesJSON || !locksJSON || !rocksJSON || !ratesJSON) {
            throw new Error("Missing chart data attributes");
        }

        // Try to parse the JSON - if this fails, the error will be caught
        const dates = JSON.parse(datesJSON);
        const locks = JSON.parse(locksJSON);
        const rocks = JSON.parse(rocksJSON);
        const rates = JSON.parse(ratesJSON);
        
        // Debug data validation
        console.log("Dates:", dates, "Length:", dates.length);
        console.log("Locks:", locks, "Length:", locks.length);
        console.log("Rocks:", rocks, "Length:", rocks.length);
        console.log("Rates:", rates, "Length:", rates.length);

        // Validate that we have data to display
        if (dates.length === 0 || locks.length === 0 || rocks.length === 0 || rates.length === 0) {
            displayNoDataMessage();
            return;
        }

        // Initialize the chart
        initializeChart(dates, locks, rocks, rates);
    } catch (error) {
        console.error("Error parsing chart data:", error);
        displayChartError("Error parsing chart data: " + error.message);
    }
});

function displayChartError(message) {
    const chartContainer = document.getElementById('performance-chart');
    if (chartContainer) {
        chartContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>${message}
            </div>
        `;
    }
    
    // Update debug info
    const debugElement = document.getElementById('chart-debug');
    const debugInfoElement = document.getElementById('chart-debug-info');
    if (debugElement && debugInfoElement) {
        debugElement.style.display = 'block';
        debugInfoElement.textContent = message;
    }
}

function displayNoDataMessage() {
    const chartContainer = document.getElementById('performance-chart');
    if (chartContainer) {
        chartContainer.innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle me-2"></i>No performance data available or data is invalid.
            </div>
        `;
    }
}

function initializeChart(dates, locks, rocks, rates) {
    // Toggle between count and rate view
    const chartTypeToggle = document.getElementById('chartTypeToggle');
    let showRate = chartTypeToggle ? chartTypeToggle.checked : false;
    
    // Create the chart options
    const options = {
        series: showRate ? 
            [{ name: 'Success Rate', type: 'line', data: rates }] : 
            [
                { name: 'Locks', type: 'column', data: locks },
                { name: 'Rocks', type: 'column', data: rocks }
            ],
        chart: {
            height: 350,
            type: 'line',
            stacked: !showRate,
            toolbar: {
                show: true,
                tools: {
                    download: true,
                    selection: true,
                    zoom: true,
                    zoomin: true,
                    zoomout: true,
                    pan: true,
                    reset: true
                }
            }
        },
        stroke: {
            width: showRate ? 3 : [1, 1],
            curve: 'smooth'
        },
        plotOptions: {
            bar: {
                columnWidth: '50%'
            }
        },
        colors: showRate ? ['#22c55e'] : ['#22c55e', '#ef4444'],
        fill: {
            opacity: 1
        },
        labels: dates,
        markers: {
            size: showRate ? 4 : 0
        },
        xaxis: {
            type: 'category'
        },
        yaxis: showRate ? 
            {
                title: {
                    text: 'Success Rate (%)'
                },
                min: 0,
                max: 100,
                labels: {
                    formatter: function(val) {
                        return val.toFixed(0) + '%';
                    }
                }
            } : 
            {
                title: {
                    text: 'Count'
                },
                min: 0
            },
        tooltip: {
            shared: true,
            intersect: false,
            y: {
                formatter: function(value, { seriesIndex, dataPointIndex, w }) {
                    return showRate ? value.toFixed(1) + '%' : value;
                }
            }
        },
        legend: {
            position: 'top'
        }
    };

    // Create the chart
    const chart = new ApexCharts(document.getElementById('performance-chart'), options);
    chart.render();
    
    // Handle chart type toggle
    if (chartTypeToggle) {
        chartTypeToggle.addEventListener('change', function() {
            showRate = this.checked;
            chart.updateOptions({
                series: showRate ? 
                    [{ name: 'Success Rate', type: 'line', data: rates }] : 
                    [
                        { name: 'Locks', type: 'column', data: locks },
                        { name: 'Rocks', type: 'column', data: rocks }
                    ],
                colors: showRate ? ['#22c55e'] : ['#22c55e', '#ef4444'],
                stroke: {
                    width: showRate ? 3 : [1, 1]
                },
                markers: {
                    size: showRate ? 4 : 0
                },
                yaxis: showRate ? 
                    {
                        title: {
                            text: 'Success Rate (%)'
                        },
                        min: 0,
                        max: 100,
                        labels: {
                            formatter: function(val) {
                                return val.toFixed(0) + '%';
                            }
                        }
                    } : 
                    {
                        title: {
                            text: 'Count'
                        },
                        min: 0
                    }
            });
        });
    }
}