// Custom JavaScript for Family Pay Application

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // PIN input validation - restrict to numbers only
    const pinInputs = document.querySelectorAll('input[name="pin"]');
    pinInputs.forEach(function(input) {
        input.addEventListener('input', function(e) {
            this.value = this.value.replace(/[^0-9]/g, '');

            // Limit to 4 digits
            if (this.value.length > 4) {
                this.value = this.value.slice(0, 4);
            }
        });
    });

    // Amount input validation - format as currency
    const amountInputs = document.querySelectorAll('input[name="amount"]');
    amountInputs.forEach(function(input) {
        input.addEventListener('blur', function(e) {
            // If the input is not empty, format it
            if (this.value) {
                // Parse the value as a float and format with 2 decimal places
                const amount = parseFloat(this.value);
                if (!isNaN(amount)) {
                    this.value = amount.toFixed(2);
                }
            }
        });
    });

    // Password confirmation validation
    const passwordForm = document.querySelector('form');
    if (passwordForm) {
        const password = document.getElementById('password');
        const confirmPassword = document.getElementById('confirm_password');

        if (password && confirmPassword) {
            confirmPassword.addEventListener('input', function() {
                if (password.value !== confirmPassword.value) {
                    confirmPassword.setCustomValidity("Passwords don't match");
                } else {
                    confirmPassword.setCustomValidity('');
                }
            });
        }
    }
});
