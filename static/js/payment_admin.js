document.addEventListener('DOMContentLoaded', function() {
    // Cicilan: when "Apakah bagian dari cicilan?" = Ya, lock "Skip otomatis update membership?" to Ya
    const apakahNyicilRadios = document.querySelectorAll('input[name="apakah_nyicil"]');
    const skipMembershipRadios = document.querySelectorAll('input[name="skip_membership_update"]');
    const skipMembershipRow = document.querySelector('.field-skip_membership_update');

    function toggleSkipMembershipForCicilan() {
        const isCicilan = document.querySelector('input[name="apakah_nyicil"]:checked')?.value === 'True';
        skipMembershipRadios.forEach(function(radio) {
            radio.disabled = isCicilan;
            if (isCicilan && radio.value === 'True') {
                radio.checked = true;
            }
        });
        if (skipMembershipRow) {
            skipMembershipRow.style.pointerEvents = isCicilan ? 'none' : '';
            skipMembershipRow.style.opacity = isCicilan ? '0.7' : '1';
        }
    }

    if (apakahNyicilRadios.length && skipMembershipRadios.length) {
        apakahNyicilRadios.forEach(function(radio) {
            radio.addEventListener('change', toggleSkipMembershipForCicilan);
        });
        toggleSkipMembershipForCicilan();
    }

    // Get all duration choice radio buttons
    const durationChoiceRadios = document.querySelectorAll('input[name="duration_choice"]');
    const durationDaysField = document.getElementById('id_duration_days');
    const durationDaysRow = document.querySelector('.field-duration_days');
    
    // Hide the membership_end_date field and its row if they exist
    const membershipEndDateRow = document.querySelector('.field-membership_end_date');
    if (membershipEndDateRow) {
        membershipEndDateRow.style.display = 'none';
    }
    
    // Hide the created_by field using multiple approaches to ensure it works
    // Try with class
    const createdByRows = document.querySelectorAll('.field-created_by');
    createdByRows.forEach(function(row) {
        row.style.display = 'none';
    });
    
    // Try with direct ID
    const createdByField = document.getElementById('id_created_by');
    if (createdByField) {
        // Find the containing row - walk up the DOM tree
        let parent = createdByField.parentElement;
        while (parent && !parent.classList.contains('form-row') && parent.tagName !== 'DIV') {
            parent = parent.parentElement;
        }
        if (parent) {
            parent.style.display = 'none';
        }
        
        // Also hide any labels for this field
        const labels = document.querySelectorAll('label[for="id_created_by"]');
        labels.forEach(function(label) {
            label.style.display = 'none';
        });
    }
    
    // Try to hide any div that contains the created_by label
    const allLabels = document.querySelectorAll('label');
    allLabels.forEach(function(label) {
        if (label.textContent.includes('Created by')) {
            // Find the containing row
            let parent = label.parentElement;
            while (parent && !parent.classList.contains('form-row') && parent.tagName !== 'DIV') {
                parent = parent.parentElement;
            }
            if (parent) {
                parent.style.display = 'none';
            }
        }
    });
    
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
    
    // Handle form submission
    const form = document.querySelector('#payment_form');
    if (form) {
        form.addEventListener('submit', function(e) {
            // No need to manually set created_by as we handle it in save_model
        });
    }
}); 