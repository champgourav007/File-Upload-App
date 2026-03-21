// Enhanced Upload with Progress, Speed, Timer - FIXED
function initEnhancedUpload() {
  console.log('initEnhancedUpload called');
  
  const uploadArea = document.getElementById('upload-area');
  const fileInput = document.getElementById('file-input');
  const selectBtn = document.getElementById('select-btn');
  const clearBtn = document.getElementById('clear-btn');
  const uploadBtn = document.getElementById('upload-btn');
  const progressBar = document.getElementById('progress-bar');
  const progressText = document.getElementById('progress-text');
  const uploadStats = document.getElementById('upload-stats');
  const fileNameSpan = document.getElementById('file-name');
  const speedDisplay = document.getElementById('speed-display');
  const timeDisplay = document.getElementById('time-display');
  const uploadStatus = document.getElementById('upload-status');
  const uploadProgress = document.getElementById('upload-progress'); // Fixed ID
  
  console.log('Elements:', {selectBtn, uploadBtn, fileInput});
  
  if (!selectBtn || !uploadBtn || !fileInput) {
    console.error('Missing upload elements');
    return;
  }
  
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

  let currentFile = null;
  let uploadStartTime = null;
  let lastLoaded = 0;
  let speedInterval = null;

  // Select File
  selectBtn.addEventListener('click', (e) => {
    e.preventDefault();
    console.log('Select clicked');
    fileInput.click();
  });

  // File Selected
  fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    console.log('File selected:', file?.name);
    if (file) {
      currentFile = file;
      fileNameSpan.textContent = `${formatFileSize(file.size)} - ${file.name}`;
      clearBtn.style.display = 'block';
      uploadBtn.style.display = 'block';
      uploadBtn.innerHTML = '<i class="bi bi-upload me-1"></i>Upload';
      uploadStats.style.display = 'block';
      uploadStatus.textContent = 'Ready to upload';
    }
  });

  // Clear File
  clearBtn.addEventListener('click', () => {
    console.log('Clear clicked');
    fileInput.value = '';
    currentFile = null;
    fileNameSpan.textContent = '';
    clearBtn.style.display = 'none';
    uploadBtn.style.display = 'none';
    uploadStats.style.display = 'none';
    uploadStatus.textContent = '';
  });

  // Upload with Real Progress
  uploadBtn.addEventListener('click', () => {
    if (!currentFile) {
      console.log('No file selected');
      return;
    }

    console.log('Upload clicked, starting XHR');
    
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append('file', currentFile);
    formData.append('csrfmiddlewaretoken', csrfToken);

    // Progress
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100);
        progressBar.style.width = percent + '%';
        progressText.textContent = percent + '%';
        
        const elapsed = ((Date.now() - uploadStartTime) / 1000) || 1;
        const speed = (e.loaded / elapsed / 1024).toFixed(1);
        speedDisplay.textContent = speed + ' KB/s';
        timeDisplay.textContent = elapsed.toFixed(1) + 's';
      }
    });

    xhr.addEventListener('load', () => {
      console.log('Upload complete, status:', xhr.status);
      if (xhr.status === 302 || xhr.status === 200) {
        uploadStatus.textContent = '✅ Success! Refresh to see new file.';
        progressBar.style.backgroundColor = '#28a745';
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = '<i class="bi bi-check-circle me-1"></i>Complete';
      } else {
        uploadStatus.textContent = `❌ Failed (${xhr.status})`;
        progressBar.style.backgroundColor = '#dc3545';
      }
    });

    xhr.addEventListener('error', () => {
      console.error('XHR error');
      uploadStatus.textContent = '❌ Network error';
      progressBar.style.backgroundColor = '#dc3545';
    });

    // Start upload
    uploadStartTime = Date.now();
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Uploading...';
    uploadProgress.style.display = 'block';
    uploadStats.style.display = 'block';
    uploadStatus.textContent = 'Starting...';

    xhr.open('POST', '/upload/');
    xhr.send(formData);
  });

  // Drag & Drop
  ['dragenter', 'dragover', 'drop'].forEach(evt => {
    uploadArea.addEventListener(evt, e => e.preventDefault());
  });
  uploadArea.addEventListener('dragover', e => uploadArea.classList.add('drag-highlight'));
  uploadArea.addEventListener('dragleave', e => uploadArea.classList.remove('drag-highlight'));
  uploadArea.addEventListener('drop', e => {
    const file = e.dataTransfer.files[0];
    if (file) {
      fileInput.files = e.dataTransfer.files;
      fileInput.dispatchEvent(new Event('change'));
    }
    uploadArea.classList.remove('drag-highlight');
  });

  // Utils
  function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i];
  }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
  console.log('DOM loaded, init upload');
  initEnhancedUpload();
});
