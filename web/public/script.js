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
    
    // API endpoint (replace with your actual API endpoint)
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
        const useAria2 = useAria2Checkbox.checked;
        const useProxy = useProxyCheckbox.checked;
        const downloadSubtitles = downloadSubtitlesCheckbox.checked;
        
        // Fetch video info from API
        fetchVideoInfo(videoUrl, useProxy)
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                
                // Update UI with video info
                updateVideoInfo(data);
                
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
    
    // Cancel download
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
    
    // Batch download
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
        const format = document.getElementById('batch-format').value;
        const maxConcurrent = parseInt(document.getElementById('batch-concurrent').value);
        const useAria2 = useAria2Checkbox.checked;
        const useProxy = useProxyCheckbox.checked;
        const downloadSubtitles = downloadSubtitlesCheckbox.checked;
        
        // Start batch download
        startBatchDownload(urls, format, maxConcurrent, useAria2, useProxy, downloadSubtitles)
            .then(response => {
                if (response.error) {
                    throw new Error(response.error);
                }
                
                showNotification(`Started batch download of ${urls.length} videos`, 'success');
                
                // Clear input
                batchUrlsInput.value = '';
                
                // Create batch download items in UI
                response.downloadIds.forEach((id, index) => {
                    createBatchDownloadItem(id, urls[index]);
                });
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Error: ' + error.message, 'error');
            });
    });
    
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
            
            // For demo purposes only - remove in production
            if (!API_URL || API_URL === '/api') {
                return getMockVideoInfo(url);
            }
            
            throw error;
        }
    }
    
    // Update UI with video information
    function updateVideoInfo(videoData) {
        // Update video details
        videoThumbnail.src = videoData.thumbnail;
        videoTitle.textContent = videoData.title;
        videoChannel.textContent = `Channel: ${videoData.channel}`;
        
        if (videoData.duration) {
            videoDuration.textContent = formatDuration(videoData.duration);
        } else {
            videoDuration.textContent = '';
        }
        
        if (videoData.views) {
            videoViews.textContent = `Views: ${formatNumber(videoData.views)}`;
        } else {
            videoViews.textContent = '';
        }
        
        // Clear existing formats
        formatGrid.innerHTML = '';
        
        // Add format options
        if (videoData.formats && videoData.formats.length > 0) {
            videoData.formats.forEach(format => {
                const formatOption = document.createElement('div');
                formatOption.className = 'format-option';
                formatOption.dataset.formatId = format.id || format.format_id;
                
                formatOption.innerHTML = `
                    <div class="format-name">${format.name || format.quality || format.format}</div>
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
                    downloadProgress.classList.remove('hidden');
                    
                    // Reset progress
                    resetDownloadProgress();
                    
                    // Start download
                    const formatId = formatOption.dataset.formatId;
                    const videoUrl = videoUrlInput.value.trim();
                    const useAria2 = useAria2Checkbox.checked;
                    const useProxy = useProxyCheckbox.checked;
                    const downloadSubtitles = downloadSubtitlesCheckbox.checked;
                    
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
            
            // For demo purposes only - remove in production
            if (!API_URL || API_URL === '/api') {
                return startMockDownload(url, formatId);
            }
            
            throw error;
        }
    }
    
    // Start batch download
    async function startBatchDownload(urls, format, maxConcurrent, useAria2 = true, useProxy = false, downloadSubtitles = false) {
        try {
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
            
            return await response.json();
        } catch (error) {
            console.error('Batch download error:', error);
            
            // For demo purposes only - remove in production
            if (!API_URL || API_URL === '/api') {
                return startMockBatchDownload(urls, format, maxConcurrent);
            }
            
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
            
            // For demo purposes only - remove in production
            if (!API_URL || API_URL === '/api') {
                // Stop mock polling
                if (activeDownloads[downloadId] && activeDownloads[downloadId].interval) {
                    clearInterval(activeDownloads[downloadId].interval);
                    delete activeDownloads[downloadId];
                }
                return { success: true };
            }
            
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
                updateDownloadProgress(data);
                
                // Handle completed download
                if (data.status === 'completed') {
                    clearInterval(pollInterval);
                    handleDownloadComplete(data);
                }
                
                // Handle failed download
                if (data.status === 'failed') {
                    clearInterval(pollInterval);
                    handleDownloadFailed(data);
                }
                
                // Handle cancelled download
                if (data.status === 'cancelled') {
                    clearInterval(pollInterval);
                    resetDownloadProgress();
                }
                
                // Update batch download item if exists
                updateBatchDownloadItem(downloadId, data);
                
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
        progressFill.style.width = `${progress}%`;
        progressPercentage.textContent = `${Math.round(progress)}%`;
        
        // Update status text
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
        
        // Update speed and ETA
        if (data.speed) {
            downloadSpeed.textContent = `${formatSize(data.speed)}/s`;
        }
        
        if (data.eta) {
            downloadEta.textContent = formatTime(data.eta);
        }
    }
    
    // Reset download progress UI
    function resetDownloadProgress() {
        progressFill.style.width = '0%';
        progressPercentage.textContent = '0%';
        progressText.textContent = 'Preparing download...';
        downloadSpeed.textContent = '0 MB/s';
        downloadEta.textContent = '--:--';
        currentDownloadId = null;
    }
    
    // Handle completed download
    function handleDownloadComplete(data) {
        showNotification('Download complete!', 'success');
        
        // If file URL is provided, trigger download
        if (data.fileUrl) {
            const link = document.createElement('a');
            link.href = data.fileUrl;
            link.download = '';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }
    
    // Handle failed download
    function handleDownloadFailed(data) {
        showNotification(`Download failed: ${data.error || 'Unknown error'}`, 'error');
    }
    
    // Create batch download item in UI
    function createBatchDownloadItem(downloadId, url) {
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
            } else if (data.status === 'completed')
