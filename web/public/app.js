document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const downloadForm = document.getElementById('download-form');
    const videoUrlInput = document.getElementById('video-url');
    const formatSelect = document.getElementById('format');
    const subtitlesCheckbox = document.getElementById('subtitles');
    const statusSection = document.getElementById('status-section');
    const videoTitle = document.getElementById('video-title');
    const videoChannel = document.getElementById('video-channel');
    const videoDuration = document.getElementById('video-duration');
    const thumbnail = document.getElementById('thumbnail');
    const progressBar = document.getElementById('progress-bar');
    const progressPercentage = document.getElementById('progress-percentage');
    const downloadStatus = document.getElementById('download-status');
    const downloadSpeed = document.getElementById('download-speed');
    const cancelBtn = document.getElementById('cancel-btn');
    const downloadBtn = document.getElementById('download-btn');
    const batchUrls = document.getElementById('batch-urls');
    const batchBtn = document.getElementById('batch-btn');
    const downloadsList = document.getElementById('downloads-list');
    
    // API endpoint (will be set up with Firebase Functions)
    const API_URL = '/api';

    // Store the current download ID
    let currentDownloadId = null;
    let downloadCheckInterval = null;

    // Event listeners
    downloadForm.addEventListener('submit', handleDownload);
    cancelBtn.addEventListener('click', cancelDownload);
    downloadBtn.addEventListener('click', downloadFile);
    batchBtn.addEventListener('click', handleBatchDownload);

    // Validate YouTube URL
    function isValidYoutubeUrl(url) {
        const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$/;
        return youtubeRegex.test(url);
    }

    // Handle single video download
    async function handleDownload(e) {
        e.preventDefault();
        
        // Get input values
        const videoUrl = videoUrlInput.value.trim();
        const format = formatSelect.value;
        const subtitles = subtitlesCheckbox.checked;
        
        // Validate URL
        if (!isValidYoutubeUrl(videoUrl)) {
            alert('Please enter a valid YouTube URL');
            return;
        }
        
        try {
            // Show status section
            statusSection.classList.remove('hidden');
            resetProgress();
            
            // Get video info first
            await getVideoInfo(videoUrl);
            
            // Start the download
            const response = await fetch(`${API_URL}/download`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: videoUrl,
                    format: format,
                    subtitles: subtitles
                }),
            });
            
            if (!response.ok) {
                throw new Error('Failed to start download');
            }
            
            const data = await response.json();
            currentDownloadId = data.downloadId;
            
            // Start progress polling
            downloadCheckInterval = setInterval(checkDownloadProgress, 1000);
            
            // Update status
            downloadStatus.textContent = 'Download started...';
            
        } catch (error) {
            console.error('Download error:', error);
            downloadStatus.textContent = `Error: ${error.message}`;
            progressBar.style.width = '0%';
            progressPercentage.textContent = '0%';
        }
    }

    // Get video information
    async function getVideoInfo(videoUrl) {
        try {
            // Update UI to loading state
            videoTitle.textContent = 'Loading...';
            videoChannel.textContent = '';
            videoDuration.textContent = '';
            thumbnail.src = '';
            
            const response = await fetch(`${API_URL}/video-info?url=${encodeURIComponent(videoUrl)}`);
            
            if (!response.ok) {
                throw new Error('Failed to get video info');
            }
            
            const data = await response.json();
            
            // Update UI with video info
            videoTitle.textContent = data.title;
            videoChannel.textContent = `Channel: ${data.channel}`;
            videoDuration.textContent = `Duration: ${formatDuration(data.duration)}`;
            thumbnail.src = data.thumbnail;
            
        } catch (error) {
            console.error('Error getting video info:', error);
            videoTitle.textContent = 'Could not load video information';
        }
    }

    // Format duration from seconds to MM:SS
    function formatDuration(seconds) {
        if (!seconds) return 'Unknown';
        
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    // Check download progress
    async function checkDownloadProgress() {
        if (!currentDownloadId) return;
        
        try {
            const response = await fetch(`${API_URL}/download-status?id=${currentDownloadId}`);
            
            if (!response.ok) {
                throw new Error('Failed to get download status');
            }
            
            const data = await response.json();
            
            // Update progress
            const progress = data.progress || 0;
            progressBar.style.width = `${progress}%`;
            progressPercentage.textContent = `${progress.toFixed(1)}%`;
            
            // Update status text
            downloadStatus.textContent = data.status;
            
            // Update speed if available
            if (data.speed) {
                downloadSpeed.textContent = `${formatSize(data.speed)}/s`;
            } else {
                downloadSpeed.textContent = '';
            }
            
            // Handle completed download
            if (data.status === 'completed') {
                clearInterval(downloadCheckInterval);
                downloadStatus.textContent = 'Download completed!';
                progressBar.style.width = '100%';
                progressPercentage.textContent = '100%';
                
                // Show download button
                downloadBtn.classList.remove('hidden');
                downloadBtn.dataset.fileUrl = data.fileUrl;
                
                // Add to downloads list
                addToDownloadsList(data.title || 'Video', 'completed', data.fileUrl);
            }
            
            // Handle failed download
            if (data.status === 'failed') {
                clearInterval(downloadCheckInterval);
                downloadStatus.textContent = `Download failed: ${data.error || 'Unknown error'}`;
                
                // Add to downloads list
                addToDownloadsList(data.title || 'Video', 'failed');
            }
            
        } catch (error) {
            console.error('Error checking download progress:', error);
        }
    }

    // Format file size
    function formatSize(bytes) {
        if (bytes === 0) return '0 B';
        
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        
        return parseFloat((bytes / Math.pow(1024, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Cancel download
    async function cancelDownload() {
        if (!currentDownloadId) return;
        
        try {
            const response = await fetch(`${API_URL}/cancel-download`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    downloadId: currentDownloadId
                }),
            });
            
            if (!response.ok) {
                throw new Error('Failed to cancel download');
            }
            
            // Clear interval and reset UI
            clearInterval(downloadCheckInterval);
            downloadStatus.textContent = 'Download cancelled';
            
            // Add to downloads list
            addToDownloadsList(videoTitle.textContent, 'cancelled');
            
            // Reset current download
            currentDownloadId = null;
            
        } catch (error) {
            console.error('Error cancelling download:', error);
        }
    }

    // Download the file
    function downloadFile() {
        const fileUrl = downloadBtn.dataset.fileUrl;
        if (!fileUrl) return;
        
        window.location.href = fileUrl;
    }

    // Handle batch download
    async function handleBatchDownload() {
        const urls = batchUrls.value.trim().split('\n').filter(url => url.trim() !== '');
        
        if (urls.length === 0) {
            alert('Please enter at least one URL');
            return;
        }
        
        // Validate URLs
        const invalidUrls = urls.filter(url => !isValidYoutubeUrl(url.trim()));
        if (invalidUrls.length > 0) {
            alert(`Found ${invalidUrls.length} invalid YouTube URLs. Please check your input.`);
            return;
        }
        
        try {
            const format = formatSelect.value;
            const subtitles = subtitlesCheckbox.checked;
            
            // Start batch download
            const response = await fetch(`${API_URL}/batch-download`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    urls: urls,
                    format: format,
                    subtitles: subtitles
                }),
            });
            
            if (!response.ok) {
                throw new Error('Failed to start batch download');
            }
            
            const data = await response.json();
            
            // Show status
            alert(`Batch download started with ${urls.length} videos. Check the Recent Downloads section for status.`);
            
            // Clear textarea
            batchUrls.value = '';
            
            // Add to downloads list as pending
            urls.forEach((url, index) => {
                addToDownloadsList(`Batch video ${index + 1}`, 'downloading', null, data.downloadIds[index]);
            });
            
        } catch (error) {
            console.error('Batch download error:', error);
            alert(`Error starting batch download: ${error.message}`);
        }
    }

    // Reset progress UI
    function resetProgress() {
        progressBar.style.width = '0%';
        progressPercentage.textContent = '0%';
        downloadStatus.textContent = 'Preparing download...';
        downloadSpeed.textContent = '';
        downloadBtn.classList.add('hidden');
        currentDownloadId = null;
        
        if (downloadCheckInterval) {
            clearInterval(downloadCheckInterval);
        }
    }

    // Add download to the recent downloads list
    function addToDownloadsList(title, status, fileUrl = null, downloadId = null) {
        // Remove empty downloads message if present
        const emptyDownloads = downloadsList.querySelector('.empty-downloads');
        if (emptyDownloads) {
            emptyDownloads.remove();
        }
        
        // Create download item element
        const downloadItem = document.createElement('div');
        downloadItem.className = 'download-item';
        
        // Add download title
        const downloadTitle = document.createElement('div');
        downloadTitle.className = 'download-item-title';
        downloadTitle.textContent = title;
        downloadItem.appendChild(downloadTitle);
        
        // Add status badge
        const statusBadge = document.createElement('span');
        statusBadge.className = 'download-item-status';
        
        switch (status) {
            case 'completed':
                statusBadge.textContent = 'Completed';
                statusBadge.classList.add('status-completed');
                break;
            case 'failed':
                statusBadge.textContent = 'Failed';
                statusBadge.classList.add('status-failed');
                break;
            case 'cancelled':
                statusBadge.textContent = 'Cancelled';
                statusBadge.classList.add('status-failed');
                break;
            case 'downloading':
                statusBadge.textContent = 'Downloading';
                statusBadge.classList.add('status-downloading');
                
                // For downloading items, add data attribute for updating later
                if (downloadId) {
                    downloadItem.dataset.downloadId = downloadId;
                }
                break;
        }
        
        downloadItem.appendChild(statusBadge);
        
        // If there's a file URL, add a download button
        if (fileUrl) {
            const downloadLink = document.createElement('a');
            downloadLink.href = fileUrl;
            downloadLink.className = 'download-link';
            downloadLink.innerHTML = '<i class="fas fa-download"></i>';
            downloadLink.title = 'Download';
            downloadItem.appendChild(downloadLink);
        }
        
        // Add to downloads list
        downloadsList.prepend(downloadItem);
        
        // Limit list to last 10 downloads
        const items = downloadsList.querySelectorAll('.download-item');
        if (items.length > 10) {
            items[items.length - 1].remove();
        }
    }

    // Update statuses of batch downloads periodically
    setInterval(updateBatchStatuses, 5000);

    async function updateBatchStatuses() {
        const downloadingItems = downloadsList.querySelectorAll('.download-item[data-download-id]');
        
        for (const item of downloadingItems) {
            const downloadId = item.dataset.downloadId;
            
            try {
                const response = await fetch(`${API_URL}/download-status?id=${downloadId}`);
                
                if (!response.ok) continue;
                
                const data = await response.json();
                const statusBadge = item.querySelector('.download-item-status');
                
                // Update title if available
                if (data.title) {
                    const titleElement = item.querySelector('.download-item-title');
                    titleElement.textContent = data.title;
                }
                
                // Update status
                if (data.status === 'completed') {
                    statusBadge.textContent = 'Completed';
                    statusBadge.className = 'download-item-status status-completed';
                    
                    // Add download link if available
                    if (data.fileUrl && !item.querySelector('.download-link')) {
                        const downloadLink = document.createElement('a');
                        downloadLink.href = data.fileUrl;
                        downloadLink.className = 'download-link';
                        downloadLink.innerHTML = '<i class="fas fa-download"></i>';
                        downloadLink.title = 'Download';
                        item.appendChild(downloadLink);
                    }
                    
                    // Remove download ID to stop checking
                    delete item.dataset.downloadId;
                    
                } else if (data.status === 'failed') {
                    statusBadge.textContent = 'Failed';
                    statusBadge.className = 'download-item-status status-failed';
                    
                    // Remove download ID to stop checking
                    delete item.dataset.downloadId;
                } else {
                    // Still downloading, update progress
                    statusBadge.textContent = `${Math.round(data.progress || 0)}%`;
                }
                
            } catch (error) {
                console.error('Error updating batch status:', error);
            }
        }
    }
    
    // Initialize by checking if the API is available
    async function checkApiStatus() {
        try {
            const response = await fetch(`${API_URL}/status`);
            
            if (!response.ok) {
                throw new Error('API is not available');
            }
            
            // API is available, do nothing
            console.log('API is available');
            
        } catch (error) {
            console.error('API status error:', error);
            
            // Show API unavailable message
            const container = document.querySelector('.container');
            
            const apiErrorDiv = document.createElement('div');
            apiErrorDiv.style.backgroundColor = '#ffebee';
            apiErrorDiv.style.color = '#c62828';
            apiErrorDiv.style.padding = '1rem';
            apiErrorDiv.style.borderRadius = '4px';
            apiErrorDiv.style.marginBottom = '1rem';
            apiErrorDiv.style.textAlign = 'center';
            
            apiErrorDiv.innerHTML = `
                <p><strong>API Service Unavailable</strong></p>
                <p>The download service is currently offline or not properly configured.</p>
                <p>This is a demo frontend only. Please set up the backend API to enable downloading.</p>
            `;
            
            container.prepend(apiErrorDiv);
        }
    }
    
    // Check API status on load
    checkApiStatus();
});