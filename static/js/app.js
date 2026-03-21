// Modern UI JS - Dark Mode, Live Search, Animations ONLY
// Upload handled by upload-enhance.js

// Dark Mode Toggle
const darkToggle = document.getElementById('dark-toggle');
if (darkToggle) {
  const theme = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', theme);
  darkToggle.checked = theme === 'dark';

  darkToggle.addEventListener('change', () => {
    const newTheme = darkToggle.checked ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
  });
}

// Live Search (for files.html)
function initLiveSearch() {
  const searchInput = document.getElementById('live-search');
  if (!searchInput) return;

  const rows = document.querySelectorAll('#file-table tbody tr');
  const noResults = document.getElementById('no-results');

  const debounce = (func, delay) => {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func(...args), delay);
    };
  };

  const filterRows = debounce((query) => {
    const lowerQuery = query.toLowerCase();
    let visibleCount = 0;

    rows.forEach(row => {
      const nameCell = row.cells[0].textContent.toLowerCase();
      if (nameCell.includes(lowerQuery)) {
        row.style.display = '';
        visibleCount++;
      } else {
        row.style.display = 'none';
      }
    });

    if (noResults) {
      noResults.textContent = visibleCount === 0 ? 'No files match your search.' : `${visibleCount} results found.`;
    }
  }, 300);

  searchInput.addEventListener('input', (e) => filterRows(e.target.value));
}

// Lightweight animations - no observer (perf)
function initAnimations() {
  // Minimal hover-only for speed
}

// NO UPLOAD CODE HERE - upload-enhance.js handles it

// Init on DOM load
document.addEventListener('DOMContentLoaded', () => {
  initLiveSearch();
  initAnimations();
  
  // Smooth scroll
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      document.querySelector(this.getAttribute('href')).scrollIntoView({
        behavior: 'smooth'
      });
    });
  });
});
