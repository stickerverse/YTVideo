document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const downloadForm = document.getElementById('download-form');
    const videoUrlInput = document.getElementById('video-url');
    const formatSelect = document.getElementById('format');
    const subtitlesCheckbox = document.getElementById('download-subtitles');
    const statusSection = document.getElementById('status-section');
    const videoTitle = document.getElementById('video-title');
    const videoChannel = document.getElementById('video-channel');
    const videoDuration = document.getElementById('video-duration');
    const thumbnail = document.getElementById('video-thumbnail');
    const progressBar = document.getElementById('progress-fill');
    const progressPercentage = document.getElementById('progress-percentage');
    const downloadStatus = document.getElementById('progress-text');
    const downloadSpeed = document.getElementById('download-speed');
    const cancelBtn = document.getElementById('cancel-btn');
    const downloadBtn = document.getElementById('download-btn');
    const batchUrls = document.getElementById('batch-urls');
    const batchBtn = document.getElementById('batch-btn');
    const downloadsList = document.getElementById('downloads-list');
    const downloadOptions = document.getElementById('download-options');
    const downloadProgress = document.getElementById('download-progress');
    const useAria2Checkbox = document.getElementById('use-aria2');
    const useProxyCheckbox = document.getElementById('use-proxy');
    const formatGrid = document.getElementById('format-grid');
    
    // API endpoint (will be set up with Firebase Functions)
    const API_URL = '/api';

    // Store the current download ID
    let currentDownloadId = null;
    let downloadCheckInterval = null;

    // Event listeners
    if (downloadForm) {
        downloadForm.addEventListener('submit', handleDownload);
    } else {
        // If the form doesn't exist, add event listener to the download button directly
        if (downloadBtn) {
            downloadBtn.addEventListener('click', handleDownload);
        }
    }
    
    if (cancelBtn) {
        cancelBtn.addEventListener('click', cancelDownload);
    }
    
    if (batchBtn) {
        batchBtn.addEventListener('click', handleBatchDownload);
    }

    // Initialize FAQ accordions
    const faqItems = document.querySelectorAll('.faq-item');
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        if (question) {
            question.addEventListener('click', () => {
                item.classList.toggle('active');
            });
        }
    });

    // Initialize mobile menu
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', function() {
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
    }

    // Validate YouTube URL
    function isValidYoutubeUrl(url) {
        const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$/;
        return youtubeRegex.test(url);
    }

    // Handle single video download
    async function handleDownload(e) {
        if (e && e.preventDefault) {
            e.preventDefault();
        }
        
        // Get input values
        const videoUrl = videoUrlInput ? videoUrlInput.value.trim() : '';
        const format = formatSelect ? formatSelect.value : 'best';
        const subtitles = subtitlesCheckbox ? subtitlesCheckbox.checked : false;
        
        // Validate URL
        if (!videoUrl) {
            showNotification('Please enter a YouTube URL', 'error');
            return;
        }
        
        if (!isValidYoutubeUrl(videoUrl)) {
            showNotification('Please enter a valid YouTube URL', 'error');
            return;
        }
        
        try {
            // Update button state
            if (downloadBtn) {
                downloadBtn.textContent = 'Processing...';
                downloadBtn.disabled = true;
            }
            
            // Show status section if it exists
            if (statusSection) {
                statusSection.classList.remove('hidden');
            }
            
            // Get options
            const useAria2 = useAria2Checkbox ? useAria2Checkbox.checked : true;
            const useProxy = useProxyCheckbox ? useProxyCheckbox.checked : false;
            
            // Get video info first
            const videoInfo = await getVideoInfo(videoUrl);
            
            // If download options section exists, show it
            if (downloadOptions) {
                downloadOptions.classList.remove('hidden');
                
                // Update UI with video info
                updateVideoInfo(videoInfo);
                
                // Reset download button
                if (downloadBtn) {
                    downloadBtn.textContent = 'Download';
                    downloadBtn.disabled = false;
                }
                
                // Scroll to download options
                downloadOptions.scrollIntoView({ behavior: 'smooth' });
            } else {
                // If no options section, start download directly
                startDownload(videoUrl, format, useAria2, useProxy, subtitles);
            }
        } catch (error) {
            console.error('Download error:', error);
            showNotification('Error: ' + error.message, 'error');
            
            // Reset download button
            if (downloadBtn) {
                downloadBtn.textContent = 'Download';
                downloadBtn.disabled = false;
            }
        }
    }

    // Get video information
    async function getVideoInfo(videoUrl) {
        try {
            // Update UI to loading state if elements exist
            if (videoTitle) videoTitle.textContent = 'Loading...';
            if (videoChannel) videoChannel.textContent = '';
            if (videoDuration) videoDuration.textContent = '';
            if (thumbnail) thumbnail.src = '';
            
            const response = await fetch(`${API_URL}/video-info?url=${encodeURIComponent(videoUrl)}`);
            
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Failed to get video info');
            }
            
            const data = await response.json();
            return data.data || data; // Handle different API response structures
        } catch (error) {
            console.error('Error getting video info:', error);
            
            // For demo purposes only - return mock data when API is unavailable
            if (!API_URL || API_URL === '/api') {
                return getMockVideoInfo(videoUrl);
            }
            
            throw error;
        }
    }

    // Update UI with video information
    function updateVideoInfo(videoData) {
        if (!videoData) return;
        
        // Update video details if elements exist
        if (thumbnail && videoData.thumbnail) {
            thumbnail.src = videoData.thumbnail;
        }
        
        if (videoTitle) {
            videoTitle.textContent = videoData.title || 'Unknown title';
        }
        
        if (videoChannel) {
            videoChannel.textContent = `Channel: ${videoData.channel || 'Unknown channel'}`;
        }
        
        if (videoDuration && videoData.duration) {
            videoDuration.textContent = formatDuration(videoData.duration);
        }
        
        // Update format grid if it exists
        if (formatGrid) {
            // Clear existing formats
            formatGrid.innerHTML = '';
            
            // Add format options
            if (videoData.formats && videoData.formats.length > 0) {
                videoData.formats.forEach(format => {
                    const formatOption = document.createElement('div');
                    formatOption.className = 'format-option';
                    formatOption.dataset.formatId = format.format_id || format.id || 'best';
                    
                    formatOption.innerHTML = `
                        <div class="format-name">${format.name || format.quality || format.format || 'Unknown format'}</div>
                        <div class="format-info">
                            <span>${format.resolution || format.quality || ''}</span>
                            <span>${format.size ? formatSize(format.size) : ''}</span>
                        </div>
                    `;
                    
                    formatOption.addEventListener('click', function() {
                        // Remove selected class from all formats
                        document.querySelectorAll('.format-option').forEach(opt => {
                            opt.classList.remove('selected');
                        });
                        
                        // Add selected class to clicked format
                        formatOption.classList.add('selected');
                        
                        // Show progress section
                        if (downloadProgress) {
                            downloadProgress.classList.remove('hidden');
                        }
                        
                        // Reset progress
                        resetDownloadProgress();
                        
                        // Start download
                        const formatId = formatOption.dataset.formatId;
                        const videoUrl = videoUrlInput ? videoUrlInput.value.trim() : '';
                        const useAria2 = useAria2Checkbox ? useAria2Checkbox.checked : true;
                        const useProxy = useProxyCheckbox ? useProxyCheckbox.checked : false;
                        const downloadSubtitles = subtitlesCheckbox ? subtitlesCheckbox.checked : false;
                        
                        startDownload(videoUrl, formatId, useAria2, useProxy, downloadSubtitles);
                    });
                    
                    formatGrid.appendChild(formatOption);
                });
            } else {
                // No formats available
                const noFormats = document.createElement('div');
                noFormats.className = 'no-formats';
                noFormats.textContent = 'No download formats available for this video.';
                formatGrid.appendChild(noFormats);
            }
        }
    }

    // Start a download
    async function startDownload(url, formatId, useAria2 = true, useProxy = false, downloadSubtitles = false) {
        try {
            resetDownloadProgress();
            
            if (downloadProgress) {
                downloadProgress.classList.remove('hidden');
            }
            
            if (downloadStatus) {
                downloadStatus.textContent = 'Starting download...';
            }
            
            const response = await fetch(`${API_URL}/download`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url,
                    formatId,
                    useAria2,
                    useProxy,
                    downloadSubtitles
                }),
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to start download');
            }
            
            const data = await response.json();
            currentDownloadId = data.data?.downloadId || data.downloadId;
            
            // Start polling for download progress
            startProgressPolling(currentDownloadId);
            
            return data;
        } catch (error) {
            console.error('Download error:', error);
            
            // For demo purposes only - simulate download when API is unavailable
            if (!API_URL || API_URL === '/api') {
                return startMockDownload(url, formatId);
            }
            
            showNotification(`Download error: ${error.message}`, 'error');
            throw error;
        }
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
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to cancel download');
            }
            
            // Clear interval and reset UI
            if (downloadCheckInterval) {
                clearInterval(downloadCheckInterval);
                downloadCheckInterval = null;
            }
            
            if (downloadStatus) {
                downloadStatus.textContent = 'Download cancelled';
            }
            
            showNotification('Download cancelled', 'warning');
            
            // Add to downloads list if exists
            if (downloadsList) {
                addToDownloadsList(videoTitle ? videoTitle.textContent : 'Video', 'cancelled');
            }
            
            // Reset current download
            currentDownloadId = null;
            
        } catch (error) {
            console.error('Error cancelling download:', error);
            showNotification('Error cancelling download', 'error');
            
            // For demo purposes - handle cancellation when API is unavailable
            if (!API_URL || API_URL === '/api') {
                if (currentDownloadId && currentDownloadId.startsWith('mock-')) {
                    clearMockDownload(currentDownloadId);
                    if (downloadStatus) downloadStatus.textContent = 'Download cancelled';
                    currentDownloadId = null;
                    return { success: true };
                }
            }
        }
    }

    // Start polling for download progress
    function startProgressPolling(downloadId) {
        // Clear existing polling
        if (downloadCheckInterval) {
            clearInterval(downloadCheckInterval);
        }
        
        // Set up polling
        downloadCheckInterval = setInterval(async () => {
            try {
                const response = await fetch(`${API_URL}/download-status?id=${downloadId}`);
                
                if (!response.ok) {
                    console.error('Error fetching download status:', response.statusText);
                    return;
                }
                
                const rawData = await response.json();
                const data = rawData.data || rawData; // Handle different API response structures
                
                // Update progress
                updateDownloadProgress(data);
                
                // Handle completed download
                if (data.status === 'completed') {
                    clearInterval(downloadCheckInterval);
                    downloadCheckInterval = null;
                    handleDownloadComplete(data);
                }
                
                // Handle failed download
                if (data.status === 'failed') {
                    clearInterval(downloadCheckInterval);
                    downloadCheckInterval = null;
                    handleDownloadFailed(data);
                }
                
                // Handle cancelled download
                if (data.status === 'cancelled') {
                    clearInterval(downloadCheckInterval);
                    downloadCheckInterval = null;
                    resetDownloadProgress();
                }
                
            } catch (error) {
                console.error('Error polling download status:', error);
                
                // For demo purposes - simulate progress when API is unavailable
                if (!API_URL || API_URL === '/api') {
                    if (currentDownloadId && currentDownloadId.startsWith('mock-')) {
                        updateMockDownloadProgress(currentDownloadId);
                    }
                }
            }
        }, 1000);
    }

    // Update download progress UI
    function updateDownloadProgress(data) {
        const progress = data.progress || 0;
        
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
        
        if (progressPercentage) {
            progressPercentage.textContent = `${progress.toFixed(1)}%`;
        }
        
        // Update status text
        if (downloadStatus) {
            if (data.status === 'queued') {
                downloadStatus.textContent = 'Queued...';
            } else if (data.status === 'downloading') {
                downloadStatus.textContent = 'Downloading...';
            } else if (data.status === 'completed') {
                downloadStatus.textContent = 'Download complete!';
            } else if (data.status === 'failed') {
                downloadStatus.textContent = `Download failed: ${data.error || 'Unknown error'}`;
            } else if (data.status === 'cancelled') {
                downloadStatus.textContent = 'Download cancelled';
            }
        }
        
        // Update speed and ETA
        if (downloadSpeed && data.speed) {
            downloadSpeed.textContent = `${formatSize(data.speed)}/s`;
        }
        
        if (downloadEta && data.eta) {
            downloadEta.textContent = formatTime(data.eta);
        }
    }

    // Reset download progress UI
    function resetDownloadProgress() {
        if (progressBar) {
            progressBar.style.width = '0%';
        }
        
        if (progressPercentage) {
            progressPercentage.textContent = '0%';
        }
        
        if (downloadStatus) {
            downloadStatus.textContent = 'Preparing download...';
        }
        
        if (downloadSpeed) {
            downloadSpeed.textContent = '0 MB/s';
        }
        
        if (downloadEta) {
            downloadEta.textContent = '--:--';
        }
        
        currentDownloadId = null;
    }

    // Handle completed download
    function handleDownloadComplete(data) {
        showNotification('Download complete!', 'success');
        
        // If file URL is provided and we want to trigger download
        if (data.fileUrl) {
            const link = document.createElement('a');
            link.href = data.fileUrl;
            link.download = '';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
        
        // Add to downloads list if exists
        if (downloadsList) {
            addToDownloadsList(data.title || 'Video', 'completed', data.fileUrl);
        }
    }

    // Handle failed download
    function handleDownloadFailed(data) {
        showNotification(`Download failed: ${data.error || 'Unknown error'}`, 'error');
        
        // Add to downloads list if exists
        if (downloadsList) {
            addToDownloadsList(data.title || 'Video', 'failed');
        }
    }

    // Handle batch download
    async function handleBatchDownload() {
        if (!batchUrls) return;
        
        const urls = batchUrls.value.trim().split('\n').filter(url => url.trim() !== '');
        
        if (urls.length === 0) {
            showNotification('Please enter at least one URL', 'error');
            return;
        }
        
        // Validate URLs
        const invalidUrls = urls.filter(url => !isValidYoutubeUrl(url.trim()));
        if (invalidUrls.length > 0) {
            showNotification(`Found ${invalidUrls.length} invalid YouTube URLs. Please check your input.`, 'error');
            return;
        }
        
        try {
            // Get format and other options
            const format = document.getElementById('batch-format')?.value || 'best';
            const maxConcurrent = parseInt(document.getElementById('batch-concurrent')?.value || '3');
            const useAria2 = useAria2Checkbox ? useAria2Checkbox.checked : true;
            const useProxy = useProxyCheckbox ? useProxyCheckbox.checked : false;
            const downloadSubtitles = subtitlesCheckbox ? subtitlesCheckbox.checked : false;
            
            // Start batch download
            const response = await fetch(`${API_URL}/batch-download`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    urls,
                    format,
                    maxConcurrent,
                    useAria2,
                    useProxy,
                    downloadSubtitles
                }),
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to start batch download');
            }
            
            const data = await response.json();
            const downloadIds = data.data?.downloadIds || data.downloadIds || [];
            
            // Show status
            showNotification(`Batch download started with ${urls.length} videos. Check the Recent Downloads section for status.`, 'success');
            
            // Clear textarea
            batchUrls.value = '';
            
            // Add to downloads list as pending
            if (batchDownloads) {
                urls.forEach((url, index) => {
                    createBatchDownloadItem(downloadIds[index] || 'mock-batch-' + index, url);
                });
            }
            
        } catch (error) {
            console.error('Batch download error:', error);
            showNotification(`Error starting batch download: ${error.message}`, 'error');
            
            // For demo purposes - simulate batch download when API is unavailable
            if (!API_URL || API_URL === '/api') {
                // Mock batch download ids
                const mockDownloadIds = urls.map((_, i) => 'mock-batch-' + i);
                
                // Show success message
                showNotification(`Batch download started with ${urls.length} videos (DEMO MODE)`, 'success');
                
                // Clear textarea
                batchUrls.value = '';
                
                // Add to downloads list as pending
                if (batchDownloads) {
                    urls.forEach((url, index) => {
                        createBatchDownloadItem(mockDownloadIds[index], url);
                    });
                }
                
                // Start mock downloads
                mockDownloadIds.forEach((id, i) => {
                    startMockBatchDownloadItem(id, urls[i]);
                });
            }
        }
    }

    // Create batch download item in UI
    function createBatchDownloadItem(downloadId, url) {
        if (!batchDownloads) return;
        
        const item = document.createElement('div');
        item.className = 'batch-item';
        item.dataset.downloadId = downloadId;
        
        // Extract video ID from URL for title
        let title = url;
        try {
            const videoId = url.includes('youtu.be/') 
                ? url.split('youtu.be/')[1].split('?')[0]
                : new URL(url).searchParams.get('v');
            title = `YouTube video: ${videoId}`;
        } catch (e) {}
        
        item.innerHTML = `
            <div class="batch-item-title">${title}</div>
            <div class="batch-item-progress">
                <div class="batch-item-progress-fill" style="width: 0%"></div>
            </div>
            <span class="batch-item-status status-queued">Queued</span>
        `;
        
        batchDownloads.appendChild(item);
        
        // Start polling for status if it's a real download
        if (!downloadId.startsWith('mock-')) {
            startBatchItemPolling(downloadId);
        }
    }

    // Start polling for a batch item
    function startBatchItemPolling(downloadId) {
        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`${API_URL}/download-status?id=${downloadId}`);
                
                if (!response.ok) {
                    console.error('Error fetching batch download status:', response.statusText);
                    return;
                }
                
                const rawData = await response.json();
                const data = rawData.data || rawData; // Handle different API response structures
                
                // Update batch item
                updateBatchDownloadItem(downloadId, data);
                
                // If completed or failed, stop polling
                if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
                    clearInterval(pollInterval);
                }
                
            } catch (error) {
                console.error('Error polling batch download status:', error);
            }
        }, 2000);
    }

    // Update batch download item
    function updateBatchDownloadItem(downloadId, data) {
        const item = document.querySelector(`.batch-item[data-download-id="${downloadId}"]`);
        if (!item) return;
        
        const progressFill = item.querySelector('.batch-item-progress-fill');
        const status = item.querySelector('.batch-item-status');
        const title = item.querySelector('.batch-item-title');
        
        // Update title if available
        if (data.title) {
            title.textContent = data.title;
        }
        
        // Update progress
        if (progressFill) {
            progressFill.style.width = `${data.progress || 0}%`;
        }
        
        // Update status
        if (status) {
            status.className = `batch-item-status status-${data.status}`;
            
            if (data.status === 'queued') {
                status.textContent = 'Queued';
            } else if (data.status === 'downloading') {
                status.textContent = `${Math.round(data.progress || 0)}%`;
            } else if (data.status === 'completed') {
                status.textContent = 'Completed';
                
                // Add download link if available
                if (data.fileUrl && !item.querySelector('.batch-item-download')) {
                    const downloadLink = document.createElement('a');
                    downloadLink.href = data.fileUrl;
                    downloadLink.className = 'batch-item-download';
                    downloadLink.innerHTML = '<i class="fas fa-download"></i>';
                    item.appendChild(downloadLink);
                }
            } else if (data.status === 'failed') {
                status.textContent = 'Failed';
            } else if (data.status === 'cancelled') {
                status.textContent = 'Cancelled';
            }
        }
    }

    // Add download to the recent downloads list
    function addToDownloadsList(title, status, fileUrl = null) {
        // Check if downloads list exists
        if (!downloadsList) return;
        
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

    // Format utilities
    function formatDuration(seconds) {
        if (!seconds) return '0:00';
        
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        
        if (minutes < 60) {
            return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
        }
        
        const hours = Math.floor(minutes / 60);
        const remainingMinutes = minutes % 60;
        
        return `${hours}:${remainingMinutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
    
    function formatSize(bytes) {
        if (bytes === 0) return '0 B';
        
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        
        return parseFloat((bytes / Math.pow(1024, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    function formatTime(seconds) {
        if (!seconds) return '--:--';
        
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        
        if (minutes < 60) {
            return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
        }
        
        const hours = Math.floor(minutes / 60);
        const remainingMinutes = minutes % 60;
        
        return `${hours}:${remainingMinutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
    
    function formatNumber(num) {
        if (!num) return '0';
        
        return new Intl.NumberFormat().format(num);
    }

    // Notification system
    function showNotification(message, type = 'info') {
        // Check if notifications container exists
        let container = document.querySelector('.notifications-container');
        
        if (!container) {
            container = document.createElement('div');
            container.className = 'notifications-container';
            document.body.appendChild(container);
        }
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        
        // Add icon based on type
        let icon = 'info-circle';
        if (type === 'success') icon = 'check-circle';
        if (type === 'warning') icon = 'exclamation-triangle';
        if (type === 'error') icon = 'times-circle';
        
        notification.innerHTML = `
            <i class="fas fa-${icon}"></i>
            <span>${message}</span>
            <button class="notification-close"><i class="fas fa-times"></i></button>
        `;
        
        // Add to container
        container.appendChild(notification);
        
        // Add close button event
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => {
            notification.classList.add('notification-hide');
            setTimeout(() => {
                notification.remove();
            }, 300);
        });
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.classList.add('notification-hide');
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.remove();
                    }
                }, 300);
            }
        }, 5000);
    }

    // Mock functions for demo/development
    function getMockVideoInfo(url) {
        // Extract video ID for demo
        let videoId;
        try {
            videoId = url.includes('youtu.be/') 
                ? url.split('youtu.be/')[1].split('?')[0]
                : new URL(url).searchParams.get('v');
        } catch (e) {
            videoId = 'dQw4w9WgXcQ'; // Default for demo
        }
        
        return {
            id: videoId,
            title: 'Demo Video Title',
            channel: 'Demo Channel',
            duration: 245, // 4:05 minutes
            views: 1234567,
            thumbnail: 'https://i.ytimg.com/vi/' + videoId + '/maxresdefault.jpg',
            formats: [
                {
                    format_id: 'best',
                    name: 'Best Quality (Video + Audio)',
                    resolution: 'Best Available',
                    ext: 'mp4'
                },
                {
                    format_id: '2160p',
                    name: '4K MP4',
                    resolution: '3840x2160',
                    ext: 'mp4'
                },
                {
                    format_id: '1080p',
                    name: '1080p MP4',
                    resolution: '1920x1080',
                    ext: 'mp4'
                },
                {
                    format_id: '720p',
                    name: '720p MP4',
                    resolution: '1280x720',
                    ext: 'mp4'
                },
                {
                    format_id: '480p',
                    name: '480p MP4',
                    resolution: '854x480',
                    ext: 'mp4'
                },
                {
                    format_id: 'bestaudio',
                    name: 'MP3 (Audio Only)',
                    resolution: 'Audio only',
                    ext: 'mp3'
                }
            ]
        };
    }
    
    // Mapping of mock downloads
    const mockDownloads = {};
    
    // Start a mock download
    function startMockDownload(url, formatId) {
        // Generate a mock download ID
        const downloadId = 'mock-' + Math.random().toString(36).substring(7);
        currentDownloadId = downloadId;
        
        // Extract video ID for title
        let videoId;
        try {
            videoId = url.includes('youtu.be/') 
                ? url.split('youtu.be/')[1].split('?')[0]
                : new URL(url).searchParams.get('v');
        } catch (e) {
            videoId = 'unknown';
        }
        
        // Store mock download data
        mockDownloads[downloadId] = {
            progress: 0,
            speed: 0,
            eta: 100,
            status: 'downloading',
            title: 'Demo Video: ' + videoId,
            url: url,
            formatId: formatId,
            interval: null
        };
        
        // Set up mock progress updates
        mockDownloads[downloadId].interval = setInterval(() => {
            if (!mockDownloads[downloadId]) return;
            
            mockDownloads[downloadId].progress += Math.random() * 5;
            
            if (mockDownloads[downloadId].progress >= 100) {
                mockDownloads[downloadId].progress = 100;
                clearInterval(mockDownloads[downloadId].interval);
                
                // Complete the download
                mockDownloads[downloadId].status = 'completed';
                mockDownloads[downloadId].fileUrl = '#demo-download';
                
                // Update UI
                updateDownloadProgress({
                    progress: 100,
                    status: 'completed',
                    fileUrl: '#demo-download',
                    title: mockDownloads[downloadId].title
                });
                
                // Show notification
                showNotification('Demo download completed!', 'success');
                
                // Handle complete
                handleDownloadComplete({
                    title: mockDownloads[downloadId].title,
                    fileUrl: '#demo-download'
                });
            } else {
                // Update mock data
                mockDownloads[downloadId].speed = Math.random() * 5 * 1024 * 1024; // Random speed up to 5 MB/s
                mockDownloads[downloadId].eta = Math.floor((100 - mockDownloads[downloadId].progress) / 5); // Estimate time remaining
                
                // Update UI
                updateDownloadProgress({
                    progress: mockDownloads[downloadId].progress,
                    status: 'downloading',
                    speed: mockDownloads[downloadId].speed,
                    eta: mockDownloads[downloadId].eta,
                    title: mockDownloads[downloadId].title
                });
            }
        }, 1000);
        
        return {
            downloadId: downloadId,
            success: true
        };
    }
    
    // Update mock download progress (for polling)
    function updateMockDownloadProgress(downloadId) {
        if (!mockDownloads[downloadId]) return;
        
        // Update UI with current progress
        updateDownloadProgress({
            progress: mockDownloads[downloadId].progress,
            status: mockDownloads[downloadId].status,
            speed: mockDownloads[downloadId].speed,
            eta: mockDownloads[downloadId].eta,
            title: mockDownloads[downloadId].title,
            fileUrl: mockDownloads[downloadId].fileUrl
        });
    }
    
    // Clear a mock download
    function clearMockDownload(downloadId) {
        if (!mockDownloads[downloadId]) return;
        
        clearInterval(mockDownloads[downloadId].interval);
        delete mockDownloads[downloadId];
    }
    
    // Start a mock batch download item
    function startMockBatchDownloadItem(downloadId, url) {
        // Extract video ID for title
        let videoId;
        try {
            videoId = url.includes('youtu.be/') 
                ? url.split('youtu.be/')[1].split('?')[0]
                : new URL(url).searchParams.get('v');
        } catch (e) {
            videoId = 'unknown';
        }
        
        // Store mock download data
        mockDownloads[downloadId] = {
            progress: 0,
            status: 'downloading',
            title: 'Demo Video: ' + videoId,
            url: url,
            interval: null
        };
        
        // Use random delay to start
        const startDelay = Math.random() * 3000;
        
        setTimeout(() => {
            // Set up mock progress updates
            mockDownloads[downloadId].interval = setInterval(() => {
                if (!mockDownloads[downloadId]) return;
                
                mockDownloads[downloadId].progress += Math.random() * 5;
                
                if (mockDownloads[downloadId].progress >= 100) {
                    mockDownloads[downloadId].progress = 100;
                    clearInterval(mockDownloads[downloadId].interval);
                    
                    // Complete the download
                    mockDownloads[downloadId].status = 'completed';
                    mockDownloads[downloadId].fileUrl = '#demo-download-' + downloadId;
                    
                    // Update batch item
                    updateBatchDownloadItem(downloadId, {
                        progress: 100,
                        status: 'completed',
                        fileUrl: '#demo-download-' + downloadId,
                        title: mockDownloads[downloadId].title
                    });
                } else {
                    // Update batch item
                    updateBatchDownloadItem(downloadId, {
                        progress: mockDownloads[downloadId].progress,
                        status: 'downloading',
                        title: mockDownloads[downloadId].title
                    });
                }
            }, 1500);
        }, startDelay);
    }
    
    // Check API status on startup
    async function checkApiStatus() {
        try {
            const response = await fetch(`${API_URL}/status`);
            
            if (!response.ok) {
                showApiUnavailableMessage();
                return false;
            }
            return true;
        } catch (error) {
            console.error('API status check error:', error);
            showApiUnavailableMessage();
            return false;
        }
    }
    
    function showApiUnavailableMessage() {
        // Create message container
        const apiMessage = document.createElement('div');
        apiMessage.className = 'api-unavailable';
        apiMessage.innerHTML = `
            <div class="api-unavailable-content">
                <i class="fas fa-exclamation-triangle"></i>
                <h3>API Service Unavailable</h3>
                <p>The download service is currently offline or not properly configured.</p>
                <p>This is a demo frontend only. The app will work in demo mode with simulated downloads.</p>
            </div>
        `;
        
        // Add to page - try to find the best place to insert it
        const container = document.querySelector('.container');
        if (container) {
            const hero = container.querySelector('.hero');
            if (hero) {
                container.insertBefore(apiMessage, hero);
            } else {
                container.insertBefore(apiMessage, container.firstChild);
            }
        } else {
            // Fallback - prepend to body
            document.body.prepend(apiMessage);
        }
    }
    
    // Run API check on startup
    checkApiStatus();
});
