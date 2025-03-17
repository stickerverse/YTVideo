# YouTube Downloader - Deployment Guide

This guide will walk you through deploying the YouTube Downloader web application to Firebase.

## Prerequisites

1. Firebase account (free tier is sufficient)
2. Node.js installed on your development machine
3. Firebase CLI installed (`npm install -g firebase-tools`)

## Step 1: Set up Firebase Project

1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project" and follow the steps to create a new project
3. Give your project a name (e.g., "YouTube Downloader")
4. Configure Google Analytics (optional)
5. Click "Create Project"

## Step 2: Initialize Firebase in your local project

1. Open a terminal in the `web` directory of this project
2. Login to Firebase:
   ```bash
   firebase login
   ```
3. Initialize the project:
   ```bash
   firebase init
   ```
   - Select "Hosting" and "Functions" features
   - Select the Firebase project you created in Step 1
   - Use "public" as the public directory
   - Configure as a single-page app: No
   - Use the existing firebase.json (Yes)
   - Install dependencies: Yes

## Step 3: Update Firebase Project Name in Configuration

1. Open the `.firebaserc` file in the `web` directory
2. Update the "default" project name to match your Firebase project ID:
   ```json
   {
     "projects": {
       "default": "YOUR-FIREBASE-PROJECT-ID"
     }
   }
   ```

## Step 4: Deploy to Firebase

Deploy the application and functions:
```bash
firebase deploy
```

This will deploy both the web application and the Firebase Functions that handle the backend logic.

## Step 5: Configure Firebase Services

After deployment, you'll need to enable and configure some Firebase services:

1. **Firebase Storage**: Go to the Firebase Console > Storage, and click "Get Started" to initialize Cloud Storage. Choose a location for your data.

2. **Firestore Database**: Go to the Firebase Console > Firestore Database, and click "Create Database". Start in test mode (you can adjust security rules later).

3. **Upgrade Plan (Important)**: The free "Spark" plan has limitations that may affect video downloads. Consider upgrading to the "Blaze" pay-as-you-go plan for better performance and to allow external network requests.

## Step 6: Configure Billing Alerts (If using Blaze plan)

If you upgraded to the Blaze plan, it's a good idea to set up billing alerts:

1. Go to Firebase Console > Project Settings > Usage and Billing
2. Click "Manage Budget Alerts"
3. Set up alerts to notify you if costs exceed your expectations

## Step 7: Test Your Deployment

Visit your deployed application at:
```
https://YOUR-FIREBASE-PROJECT-ID.web.app
```

Verify that:
- The UI loads correctly
- You can enter YouTube URLs
- Video info is retrieved
- Downloads can be initiated and completed

## Troubleshooting

If you encounter issues:

1. **Functions not deploying**: Check if there are any errors in the Firebase console > Functions logs.

2. **CORS issues**: If you see CORS errors, check your Firebase project settings and ensure your domain is properly configured.

3. **Download failures**: Check the Functions logs for more detailed error messages.

4. **Storage limitations**: If files aren't being uploaded to Storage, check your Storage rules and ensure the Functions have proper permissions.

## Legal Consideration

Remember that this application is for educational purposes only. Using it to download copyrighted content may violate YouTube's Terms of Service and copyright laws in your jurisdiction. Always respect copyright and use this tool responsibly.