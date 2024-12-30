document.addEventListener("DOMContentLoaded", function () {
            const sidebarToggle = document.getElementById("sidebarToggle");
            const sidebar = document.getElementById("sidebar");

            // Retrieve the sidebar state from localStorage
            const sidebarState = localStorage.getItem("sidebarState");
            if (sidebarState === "closed") {
                sidebar.classList.add("hidden");
            }

            // Sidebar toggle functionality
            if (sidebarToggle) {
                sidebarToggle.addEventListener("click", function (event) {
                    event.preventDefault();
                    sidebar.classList.toggle("hidden");

                    // Store the sidebar state in localStorage
                    localStorage.setItem("sidebarState", sidebar.classList.contains("hidden") ? "closed" : "open");
                });
            }

            // Function for printing the page
            window.printPage = function(day = null) {
                if (day) {
                    // Hide all schedules except the selected day
                    document.querySelectorAll('.schedule-day').forEach(function(element) {
                        if (element.querySelector('h3').innerText.trim() !== day) {
                            element.style.display = 'none';
                        } else {
                            element.style.display = 'block';
                        }
                    });
                }
                // Print the page
                window.print();

                // Restore the visibility of all schedules after printing
                document.querySelectorAll('.schedule-day').forEach(function(element) {
                    element.style.display = 'block';
                });
            };

            // Confirm rescheduling without closing the sidebar
            window.confirmReschedule = function(scheduleId) {
                $('#rescheduleModal').modal('show');
                document.getElementById('confirmRescheduleBtn').onclick = function() {
                    const url = `/reschedule/${scheduleId}/`;
                    window.location.href = url;
                };
            };

            // Event listener for action modal show event
            $('#actionModal').on('show.bs.modal', function (event) {
                const button = $(event.relatedTarget);  // Button that triggered the modal
                const scheduleId = button.data('schedule-id');  // Extract info from data-* attributes
                const currentSlot = button.data('current-slot');  // Extract current time slot
                const currentDate = button.data('current-date');  // Extract current date
                const currentRoom = button.data('current-room');  // Extract current room

                // Set up reschedule button
                document.getElementById('rescheduleBtn').onclick = function() {
                    $('#actionModal').modal('hide');
                    confirmReschedule(scheduleId);
                };

                // Set up reassign button
                document.getElementById('reassignBtn').onclick = function() {
                    $('#actionModal').modal('hide');
                    $('#reassignModal').modal('show');
                    const modal = $('#reassignModal');
                    modal.find('#current_time').val(currentSlot);  // Set the current time slot in the modal
                    modal.find('#current_date').val(currentDate);  // Set the current date in the modal
                    modal.find('#current_room').val(currentRoom);  // Set the current room in the modal

                    // Clear previous error messages and remove error class when the modal is shown
                    modal.on('shown.bs.modal', function () {
                        document.getElementById('error_message').style.display = 'none';
                        document.getElementById('error_message').innerHTML = '';
                        document.getElementById('new_date').classList.remove('is-invalid');
                        document.getElementById('new_time').classList.remove('is-invalid');
                        document.getElementById('new_lab').classList.remove('is-invalid');
                    });

                    document.getElementById('confirmReassignBtn').onclick = function() {
                        const newDate = document.getElementById('new_date').value;
                        const newTime = document.getElementById('new_time').value;
                        const newLab = document.getElementById('new_lab').value;
                        const errorMessage = document.getElementById('error_message');
                        let errors = [];

                        // Validate fields
                        if (!newDate) {
                            errors.push('Please select a new date.');
                            document.getElementById('new_date').classList.add('is-invalid');
                        } else {
                            document.getElementById('new_date').classList.remove('is-invalid');
                        }
                        if (!newTime) {
                            errors.push('Please select a new time.');
                            document.getElementById('new_time').classList.add('is-invalid');
                        } else {
                            document.getElementById('new_time').classList.remove('is-invalid');
                        }
                        if (!newLab) {
                            errors.push('Please select a room.');
                            document.getElementById('new_lab').classList.add('is-invalid');
                        } else {
                            document.getElementById('new_lab').classList.remove('is-invalid');
                        }

                        // Date comparison
                        const newDateObj = new Date(newDate);
                        const currentDateObj = new Date(currentDate);
                        if (newDateObj < currentDateObj) {
                            errors.push('Cannot reschedule to a date earlier than the original schedule.');
                            document.getElementById('new_date').classList.add('is-invalid');
                        }

                        // Rescheduling allowed check
                        const reschedulingAllowed = true; // Replace with actual check
                        if (!reschedulingAllowed) {
                            errors.push('Rescheduling is only allowed within one to two weeks from the original schedule.');
                            document.getElementById('new_date').classList.add('is-invalid');
                        }

                        // Check if the schedule already exists (this is a placeholder, replace with actual check)
                        const scheduleExists = false; // Replace with actual check
                        if (scheduleExists) {
                            errors.push('Schedule already exists for the selected date, time, and room. Please choose a different slot.');
                            document.getElementById('new_date').classList.add('is-invalid');
                            document.getElementById('new_time').classList.add('is-invalid');
                            document.getElementById('new_lab').classList.add('is-invalid');
                        }

                        // Display errors or proceed
                        if (errors.length > 0) {
                            errorMessage.innerHTML = errors.join('<br>');
                            errorMessage.style.display = 'block'; // Ensure error message is visible
                        } else {
                            errorMessage.style.display = 'none'; // Hide error message if no errors
                            const url = `/reassign/${scheduleId}/`;
                            const form = document.createElement('form');
                            form.method = 'POST';
                            form.action = url;
                            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
                            form.innerHTML = `
                                <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                                <input type="hidden" name="new_date" value="${newDate}">
                                <input type="hidden" name="new_time" value="${newTime}">
                                <input type="hidden" name="new_lab" value="${newLab}">
                            `;
                            document.body.appendChild(form);
                            form.submit();
                        }
                    };
                };
            });

            // Adjust table layout before and after printing
            window.addEventListener('beforeprint', function() {
                document.querySelectorAll('.lunch-break td').forEach(function(td) {
                    td.setAttribute('colspan', '6');
                });
            });

            window.addEventListener('afterprint', function() {
                document.querySelectorAll('.lunch-break td').forEach(function(td) {
                    td.setAttribute('colspan', '7');
                });
            });

            // Back to Top button functionality
            const backToTopButton = document.getElementById('back-to-top');
            window.addEventListener('scroll', function() {
                if (window.scrollY > 300) {
                    backToTopButton.style.display = 'block';
                } else {
                    backToTopButton.style.display = 'none';
                }
            });

            window.scrollToTop = function() {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            };
        });