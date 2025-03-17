document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const videoUrlInput = document.getElementById('video-url');
    const downloadBtn = document.getElementById('download-btn');
    const downloadOptionsSection = document.getElementById('download-options');
    const videoThumbnail = document.getElementById('video-thumbnail');
    const videoTitle = document.getElementById('video-title');
    const videoChannel = document.getElementById('video-channel');
    const videoDuration = document.getElementById('video-duration');
    const formatGrid = document.getElementById('format-grid');
    const downloadProgress = document.getElementById('download-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const progressPercentage = document.getElementById('progress-percentage');
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    
    // Mobile menu functionality
    mobileMenuBtn?.addEventListener('click', function() {
        const mainNav = document.querySelector('.main-nav');
        
        if (mainNav.style.display === 'flex') {
            mainNav.style.display = 'none';
        } else {
            mainNav.style.display = 'flex';
            mainNav.style.flexDirection = 'column';
            mainNav.style.position = 'absolute';
            mainNav.style.top = '100%';
            mainNav.style.left = '0';
            mainNav.style.right = '0';
            mainNav.style.backgroundColor = '#fff';
            mainNav.style.padding = '10px 20px';
            mainNav.style.boxShadow = '0 5px 10px rgba(0, 0, 0, 0.1)';
        }
    });
    
    // Dropdown functionality for mobile
    const dropdowns = document.querySelectorAll('.dropdown');
    dropdowns.forEach(dropdown => {
        const link = dropdown.querySelector('a');
        
        if (window.innerWidth <= 992) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const dropdownContent = dropdown.querySelector('.dropdown-content');
                
                if (dropdownContent.style.display === 'block') {
                    dropdownContent.style.display = 'none';
                } else {
                    // Close other dropdowns
                    document.querySelectorAll('.dropdown-content').forEach(content => {
                        content.style.display = 'none';
                    });
                    
                    dropdownContent.style.display = 'block';
                    dropdownContent.style.position = 'static';
                    dropdownContent.style.boxShadow = 'none';
                    dropdownContent.style.marginLeft = '20px';
                }
            });
        }
    });
    
    // Download button functionality
    downloadBtn?.addEventListener('click', function() {
        const videoUrl = videoUrlInput.value.trim();
        
        if (!videoUrl) {
            alert('Please enter a YouTube URL');
            return;
        }
        
        if (!isValidYoutubeUrl(videoUrl)) {
            alert('Please enter a valid YouTube URL');
            return;
        }
        
        // Show loading state
        downloadBtn.textContent = 'Processing...';
        downloadBtn.disabled = true;
        
        // Simulate fetching video info (replace with actual API call)
        setTimeout(() => {
            // Get video information (this would be an API call to your backend)
            getVideoInfo(videoUrl)
                .then(response => {
                    // Update UI with video info
                    updateVideoInfo(response);
                    
                    // Show download options section
                    downloadOptionsSection.classList.remove('hidden');
                    
                    // Reset download button
                    downloadBtn.textContent = 'Download';
                    downloadBtn.disabled = false;
                    
                    // Scroll to download options
                    downloadOptionsSection.scrollIntoView({ behavior: 'smooth' });
                })
                .catch(error => {
                    alert('Error processing video: ' + error.message);
                    
                    // Reset download button
                    downloadBtn.textContent = 'Download';
                    downloadBtn.disabled = false;
                });
        }, 1000); // Simulated delay for demo purposes
    });
    
    // Check if YouTube URL is valid
    function isValidYoutubeUrl(url) {
        const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$/;
        return youtubeRegex.test(url);
    }
    
    // Get video information (mock function, replace with actual API call)
    function getVideoInfo(url) {
        // This is a mock function - replace with actual API call to your backend
        return new Promise((resolve, reject) => {
            // For demo purposes, we'll create fake video data
            // In a real app, this would be an API call to your backend
            
            // Extract video ID from URL
            let videoId = '';
            
            if (url.includes('youtube.com/watch')) {
                const urlParams = new URLSearchParams(new URL(url).search);
                videoId = urlParams.get('v');
            } else if (url.includes('youtu.be/')) {
                videoId = url.split('youtu.be/')[1].split('?')[0];
            }
            
            if (!videoId) {
                reject(new Error('Could not extract video ID from URL'));
                return;
            }
            
            // Mock video data based on video ID
            const mockData = {
                id: videoId,
                title: 'Sample YouTube Video - ' + videoId,
                channel: 'Sample Channel',
                duration: '10:15',
                thumbnail: `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`,
                formats: [
                    { id: 'mp4-1080p', name: 'MP4 1080p', quality: '1080p', size: '85.4 MB' },
                    { id: 'mp4-720p', name: 'MP4 720p', quality: '720p', size: '45.2 MB' },
                    { id: 'mp4-480p', name: 'MP4 480p', quality: '480p', size: '25.7 MB' },
                    { id: 'mp4-360p', name: 'MP4 360p', quality: '360p', size: '15.3 MB' },
                    { id: 'mp3-high', name: 'MP3 High Quality', quality: '320 kbps', size: '10.1 MB' },
                    { id: 'mp3-medium', name: 'MP3 Medium Quality', quality: '192 kbps', size: '6.8 MB' }
                ]
            };
            
            resolve(mockData);
        });
    }
    
    // Update UI with video information
    function updateVideoInfo(video) {
        videoThumbnail.src = video.thumbnail;
        videoTitle.textContent = video.title;
        videoChannel.textContent = video.channel;
        videoDuration.textContent = video.duration;
        
        // Clear existing formats
        formatGrid.innerHTML = '';
        
        // Add format options
        video.formats.forEach(format => {
            const formatOption = document.createElement('div');
            formatOption.className = 'format-option';
            formatOption.dataset.formatId = format.id;
            
            formatOption.innerHTML = `
                <div class="format-name">${format.name}</div>
                <div class="format-info">
                    <span>${format.quality}</span>
                    <span>${format.size}</span>
                </div>
            `;
            
            formatOption.addEventListener('click', function() {
                // Remove selected class from all format options
                document.querySelectorAll('.format-option').forEach(option => {
                    option.classList.remove('selected');
                });
                
                // Add selected class to clicked option
                formatOption.classList.add('selected');
                
                // Start download process
                startDownload(video.id, format.id);
            });
            
            formatGrid.appendChild(formatOption);
        });
    }
    
    // Start download process (mock function, replace with actual download logic)
    function startDownload(videoId, formatId) {
        // Show progress section
        downloadProgress.classList.remove('hidden');
        
        // Reset progress
        progressFill.style.width = '0%';
        progressText.textContent = 'Preparing download...';
        progressPercentage.textContent = '0%';
        
        // Simulate progress updates
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 10;
            
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);
                
                progressText.textContent = 'Download complete!';
                
                // Simulate the actual file download after completion
                setTimeout(() => {
                    // In a real app, this would download the actual file
                    // For demo purposes, we'll just create a dummy download
                    downloadFile(videoId, formatId);
                }, 1000);
            }
            
            // Update progress UI
            progressFill.style.width = `${progress}%`;
            progressPercentage.textContent = `${Math.round(progress)}%`;
            
            if (progress < 30) {
                progressText.textContent = 'Preparing download...';
            } else if (progress < 60) {
                progressText.textContent = 'Downloading...';
            } else if (progress < 90) {
                progressText.textContent = 'Almost done...';
            } else {
                progressText.textContent = 'Finishing up...';
            }
        }, 500);
    }
    
    // Simulate file download
    function downloadFile(videoId, formatId) {
        // In a real app, this would trigger the actual file download
        // For demo purposes, we'll just alert the user
        
        const format = formatId.split('-')[0].toUpperCase();
        const quality = formatId.split('-')[1];
        
        alert(`Download complete! Your ${format} file in ${quality} quality would now be downloading. In a real application, the file would automatically download to your device.`);
        
        // In a real implementation, you would create a download link like this:
        // const link = document.createElement('a');
        // link.href = `your-backend-url/download?videoId=${videoId}&formatId=${formatId}`;
        // link.download = 'video.' + formatId.split('-')[0];
        // document.body.appendChild(link);
        // link.click();
        // document.body.removeChild(link);
    }
    
    // Initialize tooltips or other UI components
    function initializeUI() {
        // Add any additional UI initialization here
        console.log('UI initialized');
    }
    
    // Call initialization function
    initializeUI();
});