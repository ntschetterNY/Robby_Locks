/**
 * Chart initialization for Robby's Picks Dashboard
 * Handles the performance trend chart display
 */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get the canvas element
    const canvas = document.getElementById('performanceChart');
    
    // If canvas doesn't exist, exit early
    if (!canvas) {
        console.error('Performance chart canvas element not found');
        return;
    }
    
    try {
        const ctx = canvas.getContext('2d');
        
        // Get data from HTML data attributes
        // Parse the JSON and provide fallbacks in case of errors
        let dates = [];
        let locks = [];
        let rocks = [];
        let rates = [];
        
        try {
            dates = JSON.parse(canvas.getAttribute('data-dates') || '[]');
        } catch (e) {
            console.error('Error parsing dates data:', e);
        }
        
        try {
            locks = JSON.parse(canvas.getAttribute('data-locks') || '[]');
        } catch (e) {
            console.error('Error parsing locks data:', e);
        }
        
        try {
            rocks = JSON.parse(canvas.getAttribute('data-rocks') || '[]');
        } catch (e) {
            console.error('Error parsing rocks data:', e);
        }
        
        try {
            rates = JSON.parse(canvas.getAttribute('data-rates') || '[]');
        } catch (e) {
            console.error('Error parsing rates data:', e);
        }
        
        // Log the data for debugging
        console.log('Chart Data:', { dates, locks, rocks, rates });
        
        // Set min height for the canvas to ensure it's visible
        canvas.style.minHeight = '300px';
        
        // Create the Chart.js chart
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dates,
                datasets: [
                    {
                        label: 'Locks',
                        backgroundColor: '#4CAF50',
                        borderColor: '#2E7D32',
                        borderWidth: 1,
                        data: locks,
                        order: 2
                    },
                    {
                        label: 'Rocks',
                        backgroundColor: '#F44336',
                        borderColor: '#C62828',
                        borderWidth: 1,
                        data: rocks,
                        order: 3
                    },
                    {
                        type: 'line',
                        label: 'Success Rate %',
                        borderColor: '#2196F3',
                        backgroundColor: 'rgba(33, 150, 243, 0.2)',
                        borderWidth: 2,
                        pointBackgroundColor: '#2196F3',
                        pointBorderColor: '#fff',
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        fill: false,
                        data: rates,
                        yAxisID: 'y1',
                        order: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.datasetIndex === 2) { // Success rate
                                    label += context.raw + '%';
                                } else { // Locks and Rocks
                                    label += context.raw;
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Count'
                        },
                        ticks: {
                            precision: 0 // Only show integers for counts
                        }
                    },
                    y1: {
                        beginAtZero: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Success Rate %'
                        },
                        min: 0,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                }
            }
        });
        
        // Add resize event listener to make chart responsive
        window.addEventListener('resize', function() {
            chart.resize();
        });
        
    } catch (error) {
        console.error('Error initializing performance chart:', error);
        
        // Display error message in canvas area
        if (canvas.parentNode) {
            const errorMsg = document.createElement('div');
            errorMsg.style.color = 'red';
            errorMsg.style.padding = '20px';
            errorMsg.style.textAlign = 'center';
            errorMsg.innerHTML = 'Error loading chart. Please refresh the page or contact support.';
            canvas.parentNode.appendChild(errorMsg);
        }
    }
});