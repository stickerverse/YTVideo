document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const videoUrlInput = document.getElementById('video-url');
    const downloadBtn = document.getElementById('download-btn');
    const downloadOptionsSection = document.getElementById('download-options');
    const videoThumbnail = document.getElementById('video-thumbnail');
    const videoTitle = document.getElementById('video-title');
    const videoChannel = document.getElementById('video-channel');
    const videoDuration = document.getElementById('video-duration');
    const videoViews = document.getElementById('video-views');
    const formatGrid = document.getElementById('format-grid');
    const downloadProgress = document.getElementById('download-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const progressPercentage = document.getElementById('progress-percentage');
    const downloadSpeed = document.getElementById('download-speed');
    const downloadEta = document.getElementById('download-eta');
    const cancelBtn = document.getElementById('cancel-btn');
    const batchUrlsInput = document.getElementById('batch-urls');
    const batchBtn = document.getElementById('batch-btn');
    const batchDownloads = document.getElementById('batch-downloads');
    const useAria2Checkbox = document.getElementById('use-aria2');
    const useProxyCheckbox = document.getElementById('use-proxy');
    const downloadSubtitlesCheckbox = document.getElementById('download-subtitles');
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const faqItems = document.querySelectorAll('.faq-item');
    
    // API endpoint
    const API_URL = '/api';
    
    // Store active downloads
    let activeDownloads = {};
    let currentDownloadId = null;
    
    // Initialize mobile menu
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
    
    // Initialize FAQ accordions
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        question.addEventListener('click', () => {
            item.classList.toggle('active');
        });
    });
    
    // Download button click event
    if (downloadBtn) {
        downloadBtn.addEventListener('click', function() {
            const videoUrl = videoUrlInput.value.trim();
            
            if (!videoUrl) {
                showNotification('Please enter a YouTube URL', 'error');
                return;
            }
            
            if (!isValidYoutubeUrl(videoUrl)) {
                showNotification('Please enter a valid YouTube URL', 'error');
                return;
            }
            
            // Update button state
            downloadBtn.textContent = 'Processing...';
            downloadBtn.disabled = true;
            
            // Get options
            const useAria2 = useAria2Checkbox ? useAria2Checkbox.checked : true;
            const useProxy = useProxyCheckbox ? useProxyCheckbox.checked : false;
            const downloadSubtitles = downloadSubtitlesCheckbox ? downloadSubtitlesCheckbox.checked : false;
            
            // Fetch video info from API
            fetchVideoInfo(videoUrl, useProxy)
                .then(data => {
                    if (data.error) {
                        throw new Error(data.error);
                    }
                    
                    // Update UI with video info
                    updateVideoInfo(data.data || data);
                    
                    // Show download options section
                    downloadOptionsSection.classList.remove('hidden');
                    
                    // Reset download button
                    downloadBtn.textContent = 'Download';
                    downloadBtn.disabled = false;
                    
                    // Scroll to download options
                    downloadOptionsSection.scrollIntoView({ behavior: 'smooth' });
                })
                .catch(error => {
                    console.error('Error:', error);
                    showNotification('Error: ' + error.message, 'error');
                    
                    // Reset download button
                    downloadBtn.textContent = 'Download';
                    downloadBtn.disabled = false;
                });
        });
    }
    
    // Cancel download
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            if (!currentDownloadId) return;
            
            cancelDownload(currentDownloadId)
                .then(() => {
                    showNotification('Download cancelled', 'warning');
                    resetDownloadProgress();
                })
                .catch(error => {
                    console.error('Error cancelling download:', error);
                    showNotification('Error cancelling download', 'error');
                });
        });
    }
    
    // Batch download
    if (batchBtn && batchUrlsInput) {
        batchBtn.addEventListener('click', function() {
            const urls = batchUrlsInput.value.trim().split('\n').filter(url => url.trim() !== '');
            
            if (urls.length === 0) {
                showNotification('Please enter at least one URL', 'error');
                return;
            }
            
            // Validate URLs
            const invalidUrls = urls.filter(url => !isValidYoutubeUrl(url.trim()));
            if (invalidUrls.length > 0) {
                showNotification(`Found ${invalidUrls.length} invalid YouTube URLs`, 'error');
                return;
            }
            
            // Get options
            const format = document.getElementById('batch-format') ? document.getElementById('batch-format').value : 'best';
            const maxConcurrent = parseInt(document.getElementById('batch-concurrent') ? document.getElementById('batch-concurrent').value : '3');
            const useAria2 = useAria2Checkbox ? useAria2Checkbox.checked : true;
            const useProxy = useProxyCheckbox ? useProxyCheckbox.checked : false;
            const downloadSubtitles = downloadSubtitlesCheckbox ? downloadSubtitlesCheckbox.checked : false;
            
            // Start batch download
            fetch(`${API_URL}/batch-download`, {
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
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || 'Failed to start batch download');
                    });
                }
                return response.json();
            })
            .then(response => {
                showNotification(`Started batch download of ${urls.length} videos`, 'success');
                
                // Clear input
                batchUrlsInput.value = '';
                
                // Create batch download items in UI
                if (batchDownloads) {
                    const downloadIds = response.downloadIds || [];
                    downloadIds.forEach((id, index) => {
                        createBatchDownloadItem(id, urls[index]);
                    });
                }
            })
            .catch(error => {
                console.error('Batch download error:', error);
                showNotification('Error: ' + error.message, 'error');
            });
        });
    }
    
    // Check if YouTube URL is valid
    function isValidYoutubeUrl(url) {
        const pattern = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$/;
        return pattern.test(url);
    }
    
    // Fetch video info from API
    async function fetchVideoInfo(url, useProxy = false) {
        try {
            const response = await fetch(`${API_URL}/video-info?url=${encodeURIComponent(url)}&proxy=${useProxy}`);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to get video info');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Fetch error:', error);
            throw error;
        }
    }
    
    // Update UI with video information
    function updateVideoInfo(videoData) {
        // Update video details
        if (videoThumbnail) videoThumbnail.src = videoData.thumbnail;
        if (videoTitle) videoTitle.textContent = videoData.title || 'Unknown Title';
        if (videoChannel) videoChannel.textContent = `Channel: ${videoData.uploader || videoData.channel || 'Unknown Channel'}`;
        
        if (videoDuration && videoData.duration) {
            videoDuration.textContent = formatDuration(videoData.duration);
        } else if (videoDuration) {
            videoDuration.textContent = '';
        }
        
        if (videoViews && videoData.view_count) {
            videoViews.textContent = `Views: ${formatNumber(videoData.view_count)}`;
        } else if (videoViews) {
            videoViews.textContent = '';
        }
        
        // Clear existing formats
        if (formatGrid) {
            formatGrid.innerHTML = '';
            
            // Add format options
            if (videoData.formats && videoData.formats.length > 0) {
                videoData.formats.forEach(format => {
                    const formatOption = document.createElement('div');
                    formatOption.className = 'format-option';
                    formatOption.dataset.formatId = format.format_id || format.id;
                    
                    formatOption.innerHTML = `
                        <div class="format-name">${format.name || format.quality || format.format_id || format.resolution}</div>
                        <div class="format-info">
                            <span>${format.resolution || format.quality || ''}</span>
                            <span>${format.filesize ? formatSize(format.filesize) : ''}</span>
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
                        const videoUrl = videoUrlInput.value.trim();
                        const useAria2 = useAria2Checkbox ? useAria2Checkbox.checked : true;
                        const useProxy = useProxyCheckbox ? useProxyCheckbox.checked : false;
                        const downloadSubtitles = downloadSubtitlesCheckbox ? downloadSubtitlesCheckbox.checked : false;
                        
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
            currentDownloadId = data.downloadId;
            
            // Start polling for download progress
            startProgressPolling(currentDownloadId);
            
            return data;
        } catch (error) {
            console.error('Download error:', error);
            throw error;
        }
    }
    
    // Cancel download
    async function cancelDownload(downloadId) {
        try {
            const response = await fetch(`${API_URL}/cancel-download`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    downloadId
                }),
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to cancel download');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Cancel download error:', error);
            throw error;
        }
    }
    
    // Start polling for download progress
    function startProgressPolling(downloadId) {
        // Clear existing polling
        if (activeDownloads[downloadId] && activeDownloads[downloadId].interval) {
            clearInterval(activeDownloads[downloadId].interval);
        }
        
        // Set up polling
        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`${API_URL}/download-status?id=${downloadId}`);
                
                if (!response.ok) {
                    const errorData = await response.json();
                    console.error('Error fetching download status:', errorData);
                    return;
                }
                
                const data = await response.json();
                
                // Update progress
                updateDownloadProgress(data.data || data);
                
                // Handle completed download
                if (data.data?.status === 'completed' || data.status === 'completed') {
                    clearInterval(pollInterval);
                    handleDownloadComplete(data.data || data);
                }
                
                // Handle failed download
                if (data.data?.status === 'failed' || data.status === 'failed') {
                    clearInterval(pollInterval);
                    handleDownloadFailed(data.data || data);
                }
                
                // Handle cancelled download
                if (data.data?.status === 'cancelled' || data.status === 'cancelled') {
                    clearInterval(pollInterval);
                    resetDownloadProgress();
                }
                
                // Update batch download item if exists
                updateBatchDownloadItem(downloadId, data.data || data);
                
            } catch (error) {
                console.error('Error polling download status:', error);
            }
        }, 1000);
        
        // Store polling interval
        activeDownloads[downloadId] = { interval: pollInterval };
    }
    
    // Update download progress UI
    function updateDownloadProgress(data) {
        const progress = data.progress || 0;
        if (progressFill) progressFill.style.width = `${progress}%`;
        if (progressPercentage) progressPercentage.textContent = `${Math.round(progress)}%`;
        
        // Update status text
        if (progressText) {
            if (data.status === 'queued') {
                progressText.textContent = 'Queued...';
            } else if (data.status === 'downloading') {
                progressText.textContent = 'Downloading...';
            } else if (data.status === 'completed') {
                progressText.textContent = 'Download complete!';
            } else if (data.status === 'failed') {
                progressText.textContent = `Download failed: ${data.error || 'Unknown error'}`;
            } else if (data.status === 'cancelled') {
                progressText.textContent = 'Download cancelled';
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
        if (progressFill) progressFill.style.width = '0%';
        if (progressPercentage) progressPercentage.textContent = '0%';
        if (progressText) progressText.textContent = 'Preparing download...';
        if (downloadSpeed) downloadSpeed.textContent = '0 MB/s';
        if (downloadEta) downloadEta.textContent = '--:--';
        currentDownloadId = null;
    }
    
    // Handle completed download
    function handleDownloadComplete(data) {
        showNotification('Download complete!', 'success');
        
        // If download ID and file path are available, create download link
        if (data.id && data.file_path) {
            // Create a download link
            const downloadLink = document.createElement('a');
            downloadLink.href = `/api/download-file/${data.id}`;
            downloadLink.download = '';
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
        }
    }
    
    // Handle failed download
    function handleDownloadFailed(data) {
        showNotification(`Download failed: ${data.error || 'Unknown error'}`, 'error');
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
        
        // Start polling for status
        startProgressPolling(downloadId);
    }
    
    // Update batch download item in UI
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
                
                // Add download link if not already there
                if (!item.querySelector('.batch-item-download')) {
                    const downloadLink = document.createElement('a');
                    downloadLink.href = `/api/download-file/${downloadId}`;
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
});
