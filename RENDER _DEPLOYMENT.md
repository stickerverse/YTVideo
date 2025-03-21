# Deploying 4K Video Reaper on Render.com

This guide provides step-by-step instructions for deploying the 4K Video Reaper application on Render.com.

## Prerequisites

1. A [Render account](https://render.com/signup)
2. Your 4K Video Reaper codebase in a Git repository (GitHub, GitLab, etc.)

## Free Tier Storage Limitations

Render's free tier doesn't support persistent disk storage. This means:

- Downloaded files will be stored in temporary storage (`/tmp/downloads`)
- Files will be cleared whenever the service restarts or spins down after periods of inactivity
- The application includes automatic cleanup to manage the limited storage space

For production use with persistent storage, consider:
1. Upgrading to a paid Render plan
2. Implementing cloud storage integration (AWS S3, Google Cloud Storage, etc.)

## Deployment Steps

### 1. Prepare Your Repository

Ensure your repository contains the following key files:

- `render.yaml` - Configuration for Render
- `render-build.sh` - Build script for the deployment
- `Dockerfile` - Docker configuration
- Updated code files without mock implementations

### 2. Deploy via Dashboard

1. Log in to your Render account
2. Go to the Dashboard and click "New +"
3. Select "Web Service" from the dropdown
4. Connect your Git repository

### 3. Configure Web Service

Enter the following settings:

- **Name**: 4kvideoreaper (or your preferred name)
- **Region**: Choose the region closest to your target users
- **Branch**: main (or your default branch)
- **Root Directory**: Leave blank
- **Runtime Environment**: Docker
- **Plan**: Free

### 4. Set Environment Variables

Add these environment variables:

| Variable | Value | Description |
|----------|-------|-------------|
| `DOWNLOAD_DIR` | `/tmp/downloads` | Directory for temporary downloads |
| `LOG_DIR` | `/tmp/logs` | Directory for logs |
| `ARIA2_ENABLED` | `true` | Enable Aria2 for downloads |
| `ENVIRONMENT` | `production` | Set to production mode |
| `MAX_CONCURRENT_DOWNLOADS` | `3` | Maximum concurrent downloads |
| `MAX_VIDEO_SIZE_MB` | `1024` | Maximum video size in MB |
| `RATE_LIMIT_REQUESTS` | `10` | Rate limit requests per period |
| `RATE_LIMIT_PERIOD` | `60` | Rate limit period in seconds |
| `SECRET_KEY` | `[generate]` | Use Render's "Generate" button |

### 5. Deploy Your Application

Click "Create Web Service" to start the deployment process.

Render will build and deploy your application. The initial build may take 5-10 minutes.

## 6. Verify Your Deployment

1. Once deployed, navigate to your service URL (e.g., `https://4kvideoreaper.onrender.com`)
2. Test the API by visiting `/api/status`
3. Try downloading a video through the UI

## Monitoring and Troubleshooting

### Viewing Logs

- In the Render dashboard, go to your service
- Click on "Logs" to view application logs
- Check for any error messages or warnings

### Common Issues

1. **Build Failures**
   - Check the build logs for specific errors
   - Ensure dependencies are correctly listed in requirements.txt
   - Verify the Docker configuration is correct

2. **API Errors**
   - Check if system dependencies (FFmpeg, Aria2) are installed correctly
   - Verify environment variables are set properly
   - Ensure file permissions are correct for temporary directories

3. **Storage Issues**
   - The application includes automatic cleanup for temporary storage
   - If storage issues persist, adjust `MAX_VIDEO_SIZE_MB` or increase cleanup frequency

## Updating Your Application

1. Make changes to your codebase
2. Commit and push to your Git repository
3. Render will automatically detect changes and redeploy

## Advanced Configuration

### Custom Domain

1. In the Render dashboard, go to your service
2. Click on "Settings" and scroll to "Custom Domain"
3. Follow the instructions to add your domain

### Upgrading to Paid Plans

For more resources and persistent storage:

1. Go to your service in the Render dashboard
2. Click on "Settings" and scroll to "Instance Type"
3. Choose a paid plan that suits your needs
