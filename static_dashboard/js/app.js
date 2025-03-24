/**
 * Robby Locks - Dashboard View
 * Main JavaScript file
 */

// Initialize performance chart with dynamic data
function initPerformanceChart() {
    console.log('Initializing performance chart...');
    
    // This function will read chart data from the window.chartData variable
    if (!window.chartData) {
        console.error('Chart data not available');
        document.querySelector("#performance-chart").innerHTML = 
            '<div class="alert alert-warning m-3">Chart data not available.</div>';
        return;
    }
    
    // Check if we have any data to display
    if (!window.chartData.dates || window.chartData.dates.length === 0) {
        console.warn('No chart data available');
        document.querySelector("#performance-chart").innerHTML = 
            '<div class="alert alert-info m-3">No performance data available yet. Make some picks to see your performance over time.</div>';
        return;
    }
    
    console.log('Chart data:', window.chartData);
    
    // Chart configuration
    const options = {
        series: [{
            name: 'Robby Lock',
            type: 'column',
            data: window.chartData.locks
        }, {
            name: 'Robby Rock',
            type: 'column',
            data: window.chartData.rocks
        }, {
            name: 'Success Rate',
            type: 'line',
            data: window.chartData.rates
        }],
        chart: {
            height: 350,
            type: 'line',
            stacked: false,
            toolbar: {
                show: false
            },
            fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif",
            animations: {
                enabled: true,
                easing: 'easeinout',
                speed: 800
            },
            background: '#fff'
        },
        plotOptions: {
            bar: {
                borderRadius: 4,
                columnWidth: '60%',
                dataLabels: {
                    position: 'top'
                }
            }
        },
        dataLabels: {
            enabled: true,
            enabledOnSeries: [2],
            formatter: function(val) {
                return val + '%';
            },
            style: {
                fontSize: '12px',
                fontWeight: 600
            },
            background: {
                enabled: true,
                foreColor: '#fff',
                padding: 4,
                borderRadius: 2,
                borderWidth: 0,
                opacity: 0.9
            }
        },
        stroke: {
            width: [0, 0, 3],
            curve: 'smooth'
        },
        colors: ['#22c55e', '#ef4444', '#0d6efd'],
        xaxis: {
            categories: window.chartData.dates,
            labels: {
                style: {
                    fontSize: '12px',
                    fontWeight: 500
                }
            },
            axisBorder: {
                show: false
            },
            axisTicks: {
                show: false
            }
        },
        yaxis: [
            {
                title: {
                    text: 'Count of Results',
                    style: {
                        fontSize: '13px',
                        fontWeight: 500
                    }
                },
                min: 0,
                labels: {
                    style: {
                        fontSize: '12px',
                        fontWeight: 500
                    }
                }
            },
            {
                opposite: true,
                title: {
                    text: 'Success Rate (%)',
                    style: {
                        fontSize: '13px',
                        fontWeight: 500
                    }
                },
                min: 0,
                max: 100,
                labels: {
                    style: {
                        fontSize: '12px',
                        fontWeight: 500
                    }
                }
            }
        ],
        tooltip: {
            shared: true,
            intersect: false,
            theme: 'light',
            style: {
                fontSize: '13px',
                fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif"
            },
            y: {
                formatter: function(value, { seriesIndex }) {
                    if (seriesIndex === 2) {
                        return value + '%';
                    }
                    return value;
                }
            }
        },
        legend: {
            position: 'top',
            horizontalAlign: 'center',
            offsetY: 5,
            fontSize: '13px',
            fontWeight: 600,
            markers: {
                width: 12,
                height: 12,
                radius: 6
            }
        },
        grid: {
            borderColor: '#e2e8f0',
            strokeDashArray: 4,
            padding: {
                top: 0,
                right: 0,
                bottom: 0,
                left: 10
            }
        },
        responsive: [
            {
                breakpoint: 768,
                options: {
                    chart: {
                        height: 280
                    },
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        ]
    };

    // Create and render the chart
    const chartElement = document.querySelector("#performance-chart");
    if (chartElement) {
        try {
            console.log('Rendering chart...');
            const chart = new ApexCharts(chartElement, options);
            chart.render();
            console.log('Chart rendered successfully');
        } catch (error) {
            console.error('Error rendering chart:', error);
            chartElement.innerHTML = 
                '<div class="alert alert-danger m-3">Error rendering chart. Please check console for details.</div>';
        }
    } else {
        console.error('Chart element not found');
    }
}

/**
 * Initialize sport and date filters
 */
function initFilters() {
    console.log('Initializing filters...');
    const sportSelector = document.getElementById('sport_selector');
    const dateSelector = document.getElementById('game_date');
    
    if (sportSelector) {
        sportSelector.addEventListener('change', function() {
            document.getElementById('filter-form').submit();
        });
    }
    
    if (dateSelector) {
        dateSelector.addEventListener('change', function() {
            document.getElementById('filter-form').submit();
        });
    }
}

/**
 * Initialize smooth scrolling for anchor links
 */
function initSmoothScroll() {
    console.log('Initializing smooth scroll...');
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();

            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                window.scrollTo({
                    top: target.offsetTop - 20,
                    behavior: 'smooth'
                });
            }
        });
    });
}

/**
 * Add hover effects to game cards
 */
function initGameCardEffects() {
    const gameCards = document.querySelectorAll('.game-card');
    
    gameCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-8px)';
            this.style.boxShadow = '0 10px 25px rgba(0, 0, 0, 0.1)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.05)';
        });
    });
}

/**
 * Add animations to stats cards
 */
function initStatsCardAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate');
            }
        });
    }, { threshold: 0.1 });
    
    const statsCards = document.querySelectorAll('.stats-card');
    statsCards.forEach(card => {
        observer.observe(card);
    });
}