// Download Progress Spinner
document.addEventListener('DOMContentLoaded', function() {
  // Global download spinner
  const spinnerHTML = `
    <div id="downloadSpinner" class="position-fixed top-50 start-50 translate-middle z-index-1055 d-none" style="z-index: 1055;">
      <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
        <span class="visually-hidden">Downloading...</span>
      </div>
      <div class="mt-2 text-white fw-bold">Downloading...</div>
    </div>
  `;
  document.body.insertAdjacentHTML('beforeend', spinnerHTML);

  const spinner = document.getElementById('downloadSpinner');

  // Intercept all download links
  document.addEventListener('click', function(e) {
    if (e.target.closest('a[href^="/download/"]')) {
      e.preventDefault();
      
      const link = e.target.closest('a');
      const originalHref = link.href;
      
      // Show spinner
      spinner.classList.remove('d-none');
      
      // Create invisible download iframe/link
      const a = document.createElement('a');
      a.href = originalHref;
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      
      // Hide spinner after delay (download started)
      setTimeout(() => {
        spinner.classList.add('d-none');
      }, 1500);
    }
  });
});
