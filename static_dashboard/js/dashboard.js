/**
 * Dashboard.js - Main JavaScript for Robby's Picks Dashboard
 */

// Initialize any components that need JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize date picker functionality
    initializeDatePicker();
    
    // Add any additional initialization here
});

/**
 * Initialize the date picker dropdown functionality
 */
function initializeDatePicker() {
    const dateSelect = document.getElementById('date-select');
    if (dateSelect) {
        dateSelect.addEventListener('change', function() {
            window.location = this.value;
        });
    }
}