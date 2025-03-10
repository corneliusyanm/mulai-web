document.addEventListener('DOMContentLoaded', function() {
    // Get all duration choice radio buttons
    const durationChoiceRadios = document.querySelectorAll('input[name="duration_choice"]');
    const durationDaysField = document.getElementById('id_duration_days');
    const durationDaysRow = document.querySelector('.field-duration_days');
    
    // Hide the membership_end_date field and its row if they exist
    const membershipEndDateRow = document.querySelector('.field-membership_end_date');
    if (membershipEndDateRow) {
        membershipEndDateRow.style.display = 'none';
    }
    
    // Function to toggle custom duration field visibility
    function toggleCustomDurationField() {
        const selectedValue = document.querySelector('input[name="duration_choice"]:checked')?.value;
        
        if (selectedValue === '0') {
            // Show custom duration field if "Custom" is selected
            if (durationDaysRow) durationDaysRow.style.display = 'block';
            if (durationDaysField) {
                durationDaysField.style.display = 'block';
                durationDaysField.required = true;
            }
        } else {
            // Hide custom duration field for other options
            if (durationDaysRow) durationDaysRow.style.display = 'none';
            if (durationDaysField) {
                durationDaysField.style.display = 'none';
                durationDaysField.required = false;
            }
        }
    }
    
    // Add event listeners to all radio buttons
    durationChoiceRadios.forEach(radio => {
        radio.addEventListener('change', toggleCustomDurationField);
    });
    
    // Initial call to set correct visibility
    toggleCustomDurationField();
}); 