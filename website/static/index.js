// Confirmation Dialog for Deleting Questions
document.querySelectorAll('.delete-btn').forEach(button => {
    button.addEventListener('click', async function(event) {
        event.preventDefault();
        const questionId = this.dataset.questionId;
        const confirmation = confirm('Are you sure you want to delete this question?');
        if (confirmation) {
            try {
                const response = await fetch(`/delete_question/${questionId}`, {
                    method: 'POST'
                });
                if (response.ok) {
                    window.location.reload(); // Reload the page after successful deletion
                } else {
                    console.error('Failed to delete question');
                }
            } catch (error) {
                console.error('Error:', error);
            }
        }
    });
});

// Submitting Answers Form (assuming you have a form with id answers-form)
document.getElementById('answers-form').addEventListener('submit', async function(event) {
    event.preventDefault();
    const formData = new FormData(this);
    try {
        const response = await fetch('/submit_answers', {
            method: 'POST',
            body: formData
        });
        if (response.ok) {
            window.location.href = '/active_questions'; // Redirect to active questions page after successful submission
        } else {
            console.error('Failed to submit answers');
        }
    } catch (error) {
        console.error('Error:', error);
    }
});

// Handling Google OAuth Authentication (assuming you have a button with id login-btn)
document.getElementById('login-btn').addEventListener('click', function() {
    window.location.href = '/login'; // Redirect to login page
});

// Other Utility Functions
function myUtilityFunction() {
    // Your code here
}
