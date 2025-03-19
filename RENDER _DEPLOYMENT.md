# Deploying 4K Video Reaper on Render

This guide provides steps to deploy the 4K Video Reaper application on Render's free tier.

## Prerequisites

1. A [Render account](https://render.com/signup)
2. Your project code pushed to a GitHub repository

## Important: Free Tier Storage Limitations

Since Render's free tier doesn't support persistent disk storage, this deployment uses temporary storage (`/tmp/downloads`). **This means downloaded files will be cleared whenever the service restarts or spins down after periods of inactivity.**

For persistent storage, you'll need to:
1. Upgrade to a paid plan
2. Implement external storage like AWS S3, Google Cloud Storage, or similar

## Deployment Steps

### 1. Connect Your Repository

1. Log in to your Render account
2. Go to the Dashboard and click "New +"
3. Select "Blueprint" from the dropdown
4. Connect your GitHub account if you haven't already
5. Select the repository containing your 4K Video Reaper code
6. Render will detect the `render.yaml` file and use it to configure your service

### 2. Review and Customize Settings

1. Review the automatically populated settings from your `render.yaml` file
2. You can adjust settings as needed:
   - Choose the service name
   - Select a region close to your users
   - Configure environment variables

### 3. Deploy the Application

1. Click "Apply" to start the deployment
2. Render will build and deploy your application
   - This might take 5-10 minutes for the initial build
   - Subsequent deployments will be faster

### 4. Access Your Application

Once deployed, Render will provide you with a URL (something like `https://4kvideoreaper-api.onrender.com`).

1. Visit this URL to access your 4K Video Reaper application
2. Navigate to `/api/status` to verify the API is working

## Important Limitations on Render's Free Tier

1. **Temporary Storage Only**: Downloaded files are stored in temporary storage and will be lost when the service restarts
2. **Spinning Down**: Free services on Render spin down after 15 minutes of inactivity
3. **Startup Time**: When a request comes in, the service will spin up again, which can take up to 30 seconds
4. **Bandwidth Limits**: Limited to 100GB/month
5. **RAM/CPU Limits**: Limited to 512MB RAM and 0.5 CPU (shared)

## Recommendations for Production Use

1. **Upgrade to a paid plan** for persistent storage and to avoid spin-downs
2. **Implement external storage** such as AWS S3 for downloaded files
3. **Set up a CDN** for better content delivery performance

## Monitoring and Maintaining Your Deployment

1. In the Render dashboard, you can:
   - View logs for your service
   - Check resource usage
   - Monitor uptime

2. Set up automatic deployments:
   - By default, Render will automatically redeploy when you push to your GitHub repository
