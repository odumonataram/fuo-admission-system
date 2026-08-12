// Global site JS. Page-specific scripts will be added in later phases
// (AJAX application status polling, Chart.js dashboards, SweetAlert2 confirms).

document.addEventListener("DOMContentLoaded", () => {
    // Auto-dismiss flash alerts after 6 seconds.
    document.querySelectorAll(".alert").forEach((alertEl) => {
        setTimeout(() => {
            const alert = bootstrap.Alert.getOrCreateInstance(alertEl);
            alert.close();
        }, 6000);
    });
});
