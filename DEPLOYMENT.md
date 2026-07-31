# Cloud Deployment Guide - IntelliX

This guide describes how to deploy the IntelliX stack (FastAPI Backend + React Frontend + Managed Neo4j Database) online for free using **Render**, **Vercel / Netlify**, and **Neo4j AuraDB**.

```
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚                    React Frontend                      â”‚
  â”‚                  (Vercel or Netlify)                   â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                              â”‚ HTTPS Request
                              â–¼
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚                    FastAPI Backend                     â”‚
  â”‚                        (Render)                        â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                              â”‚ Bolt Protocol
                              â–¼
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚                     Neo4j Database                     â”‚
  â”‚                    (Neo4j AuraDB)                      â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## Step 1: Push Code to GitHub

Initialize git, add files, and push your repository to GitHub:
```bash
git init
git add .
git commit -m "feat: IntelliX initial structure"
# Create a new repository on github.com and link it
git remote add origin https://github.com/yourusername/intellix.git
git branch -M main
git push -u origin main
```

---

## Step 2: Set Up Managed Neo4j (Neo4j AuraDB Free)

Neo4j AuraDB is the official managed cloud platform for Neo4j.

1. Go to the [Neo4j Aura Console](https://console.neo4j.io/).
2. Create a free account or sign in.
3. Click **Create Database** -> Select **AuraDB Free** tier -> Select your region.
4. Download the generated credentials file (contains connection credentials).
5. Copy the **Connection URI** (it will start with `neo4j+s://...`).
6. Copy the password.

---

## Step 3: Deploy Backend on Render

Render builds and hosts Web Services directly from your repository.

1. Sign in to [Render Console](https://dashboard.render.com/).
2. Click **New +** in the top right, and select **Blueprint**.
3. Connect your GitHub repository.
4. Render will parse the `render.yaml` file in the root, automatically loading the backend configuration.
5. In the configuration page, fill in the Environment Variables:
   - `GEMINI_API_KEY`: Your Gemini API key.
   - `GROQ_API_KEY`: Your Groq API key (`gsk_EoIJtZ...`).
   - `TAVILY_API_KEY`: Your Tavily API key.
   - `NEO4J_URI`: Your Neo4j Aura Connection URI (e.g. `neo4j+s://a1b2c3d4.databases.neo4j.io`).
   - `NEO4J_USER`: `neo4j`
   - `NEO4J_PASSWORD`: Your Neo4j Aura Password.
6. Click **Deploy**. Render will install requirements, pre-download the BGE embedding model, and launch the service.
7. Once deployed, copy your Render Web Service URL (e.g. `https://intellix-backend.onrender.com`).

---

## Step 4: Deploy Frontend on Vercel or Netlify

### Option A: Vercel Deployment (Recommended)

1. Sign in to [Vercel Dashboard](https://vercel.com/).
2. Click **Add New** -> **Project**.
3. Import your GitHub repository.
4. Configure the project:
   - **Root Directory**: Select `frontend`.
   - **Framework Preset**: select **Vite** (detected automatically).
   - **Environment Variables**: Add one key:
     - Name: `VITE_API_URL`
     - Value: `https://your-render-backend-url.onrender.com` (paste the backend URL copied from Step 3).
5. Click **Deploy**. Vercel will build the React bundle and deploy it.

### Option B: Netlify Deployment

1. Sign in to [Netlify Dashboard](https://www.netlify.com/).
2. Click **Add new site** -> **Import an existing project** -> Select **GitHub**.
3. Import your repository.
4. Configure site settings:
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `dist` (Vite's default output folder)
   - Go to **Environment variables** and add:
     - Key: `VITE_API_URL`
     - Value: `https://your-render-backend-url.onrender.com` (backend URL from Step 3).
5. Click **Deploy Site**.

---

## Routing & Fallback Notes

- **Vite Environment Variables**: In Vite, custom environment variables must be prefixed with `VITE_` (e.g. `VITE_API_URL`). They are loaded into the app bundle at compile-time.
- **SPA Routing Redirects**: To handle direct URL reloads on the frontend, we have created `vercel.json` and `public/_redirects` configurations. These ensure Vercel and Netlify forward all page requests back to `index.html` dynamically, resolving SPA 404 errors.
