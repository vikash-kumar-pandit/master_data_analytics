# Stateless Data Platform - Architecture & Deployment Recommendations

**Date:** May 2026  
**Current Stack:** FastAPI + Polars + Redis/Celery | React 18 + Vite + recharts + ag-grid

---

## EXECUTIVE SUMMARY

Your platform has a solid foundation for data analytics. This document provides research-backed recommendations across cloud deployment, frontend modernization, backend architecture, and performance optimization—with actionable code examples for each.

---

# 1. CLOUD PLATFORMS COMPARISON

## 1.1 AWS (Elastic Cloud Compute)

### **Strengths**
- **ML/AI Services:** SageMaker (AutoML), Forecast, Lookout for Anomalies, Comprehend (NLP)
- **Data Processing:** EMR (Spark), Athena (SQL on S3), Glue (ETL)
- **Cost Optimization:** Spot instances (70% discount), Reserved instances, Savings Plans
- **Ecosystem:** Most mature, largest market share, extensive documentation
- **Global Infrastructure:** 30+ regions, 99.99% SLA

### **Estimated Monthly Costs (Mid-scale)**
```
Frontend (S3 + CloudFront):        $20-50
Backend (EC2 t3.medium × 2):       $150-200
Database (RDS PostgreSQL):          $80-150
Redis (ElastiCache):                $30-50
Task Queue (SQS + Lambda):          $50-100
Total (with growth allowance):      $350-600/month
```

### **Deployment Architecture**
```yaml
# AWS Architecture Overview
Load Balancer (ALB) → Auto Scaling Group
  ├── EC2 t3.medium (FastAPI) × 2-5
  ├── RDS PostgreSQL (Multi-AZ)
  ├── ElastiCache Redis (Multi-AZ)
  ├── S3 (Data, Model storage)
  ├── CloudFront (CDN for frontend)
  ├── SageMaker (ML training)
  └── Lambda (Scheduled tasks)

Frontend: S3 static website + CloudFront distribution
CI/CD: CodePipeline + CodeDeploy
```

### **AWS Deployment Code Example**
```bash
# Deploy with CloudFormation (Infrastructure as Code)
aws cloudformation create-stack \
  --stack-name data-platform-prod \
  --template-body file://cloudformation.yaml \
  --parameters ParameterKey=InstanceType,ParameterValue=t3.medium

# Build and push Docker image
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

docker build -t data-platform-backend .
docker tag data-platform-backend:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/data-platform-backend:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/data-platform-backend:latest
```

### **ML Services Integration Example**
```python
# AWS SageMaker AutoML
import boto3
from sagemaker.automl.automl import AutoML

sagemaker_session = boto3.Session().client('sagemaker')

automl = AutoML(
    role='arn:aws:iam::ACCOUNT:role/SageMakerRole',
    target_col='target_variable',
    max_candidates=10,
    max_runtime_per_training_job_in_seconds=3600,
    output_path='s3://my-bucket/automl-output/'
)

automl.fit(X_train, y_train)
predictions = automl.predict(X_test)
```

---

## 1.2 Google Cloud Platform (GCP)

### **Strengths**
- **AI/ML Leadership:** Vertex AI, BigQuery ML, TensorFlow ecosystem
- **Data Analytics:** BigQuery (serverless SQL), Dataflow (Apache Beam)
- **Cost-Effective:** Preemptible VMs (70% discount), committed use discounts
- **Integration:** Native TensorFlow, scikit-learn support
- **ML Ops:** Kubeflow, Vertex AI Pipelines for MLOps

### **Estimated Monthly Costs (Mid-scale)**
```
Frontend (Cloud Storage + CDN):     $15-40
Backend (Compute Engine e2-medium): $120-180
Database (Cloud SQL PostgreSQL):    $100-150
Cloud Memorystore (Redis):          $25-50
BigQuery (Analysis):                $100-200 (per TB queried)
Vertex AI (ML training):            $50-200
Total:                              $410-820/month
```

### **GCP Architecture**
```yaml
# GCP Architecture Overview
Cloud Load Balancing → Instance Group
  ├── Compute Engine VM (FastAPI) × 2-5
  ├── Cloud SQL PostgreSQL
  ├── Cloud Memorystore Redis
  ├── Cloud Storage (Data, Models)
  ├── Cloud CDN
  ├── BigQuery (Data warehouse)
  ├── Vertex AI (AutoML training)
  └── Cloud Scheduler (Scheduled tasks)

Frontend: Cloud Storage website + Cloud CDN
CI/CD: Cloud Build + Cloud Deploy
```

### **GCP Deployment Example**
```bash
# Deploy with gcloud CLI
gcloud app deploy app.yaml

# Or use Cloud Run (Serverless containers)
gcloud run deploy data-platform-backend \
  --image gcr.io/PROJECT_ID/data-platform \
  --platform managed \
  --region us-central1 \
  --memory 4Gi \
  --cpu 2 \
  --set-env-vars REDIS_URL=redis://...,DATABASE_URL=postgresql://...

# Deploy frontend to Cloud Storage
gsutil -m cp -r frontend/dist/* gs://data-platform-frontend/
gcloud compute backend-buckets update data-platform \
  --enable-cdn
```

### **Vertex AI AutoML Example**
```python
# Vertex AI AutoML
from google.cloud import aiplatform

aiplatform.init(project='my-project', location='us-central1')

dataset = aiplatform.TabularDataset.create(
    display_name="sales_dataset",
    gcs_source="gs://my-bucket/train.csv"
)

job = aiplatform.AutoMLTabularTrainingJob(
    display_name="sales_prediction",
    optimization_prediction_type="regression",
)

model = job.run(
    dataset=dataset,
    budget_milli_node_hours=1000,
    disable_early_stopping=False
)

predictions = model.predict(instances=test_data)
```

---

## 1.3 Microsoft Azure

### **Strengths**
- **Enterprise Integration:** Active Directory, Office 365, Dynamics 365
- **Hybrid Capability:** Azure Arc for on-premise + cloud
- **ML Services:** Azure Machine Learning, Cognitive Services (Vision, Language)
- **Database Options:** Cosmos DB (multi-region), Azure SQL, Synapse Analytics
- **DevOps:** Native GitHub Actions, Azure DevOps tight integration

### **Estimated Monthly Costs (Mid-scale)**
```
Frontend (Azure Static Web Apps):   $0-20 (included tier)
Backend (App Service B2):           $120-200
Database (Azure SQL Standard):      $150-250
Azure Cache for Redis:              $50-100
Azure Cosmos DB:                    $100-300 (variable)
Machine Learning:                   $50-200
Total:                              $470-1070/month
```

### **Azure Architecture**
```yaml
# Azure Architecture Overview
Application Gateway → App Service (Windows/Linux)
  ├── App Service Plan (B2, P1v2)
  ├── Azure SQL Database (Standard tier)
  ├── Azure Cache for Redis
  ├── Azure Blob Storage
  ├── Azure CDN
  ├── Azure Machine Learning
  ├── Synapse Analytics (data warehouse)
  └── Logic Apps (Scheduled tasks)

Frontend: Azure Static Web Apps (built-in CDN)
CI/CD: GitHub Actions + Azure DevOps
```

### **Azure Deployment Example**
```bash
# Deploy with Azure CLI
az group create --name data-platform-rg --location eastus

# Deploy using ARM template
az deployment group create \
  --resource-group data-platform-rg \
  --template-file azuredeploy.json \
  --parameters environment=production

# Deploy App Service
az appservice plan create \
  --name data-platform-plan \
  --resource-group data-platform-rg \
  --sku B2 --is-linux

az webapp create \
  --resource-group data-platform-rg \
  --plan data-platform-plan \
  --name data-platform-app \
  --runtime "PYTHON|3.11"
```

### **Azure Machine Learning Example**
```python
# Azure ML AutoML
from azure.ai.ml import MLClient
from azure.ai.ml.entities import Data
from azure.ai.ml.constants import AssetTypes
from azure.ai.ml.automl import regression

ml_client = MLClient.from_config()

# Register dataset
my_data = Data(
    path="./data/train.csv",
    type=AssetTypes.URI_FILE,
    description="Training data"
)

registered_data = ml_client.data.create_or_update(my_data)

# Run AutoML
from azure.ai.ml import automl

automl_config = automl.regression(
    compute="cpu-cluster",
    experiment_name="sales_prediction",
    training_data=registered_data,
    target_column_name="sales",
    primary_metric="r2_score",
)

returned_job = ml_client.jobs.create_or_update(automl_config)
```

---

## 1.4 Vercel (Frontend Hosting)

### **Strengths**
- **Optimized for React:** Next.js native support, Edge Functions
- **Zero-Config Deployments:** Git push = automatic deployment
- **Performance:** Global CDN, automatic image optimization
- **Pricing:** Free tier for small projects, pay-per-request
- **DX:** Instant previews, rollbacks, environment variables

### **Estimated Costs**
```
Free Tier: Up to 100GB bandwidth/month
Pro: $20/month (1TB bandwidth)
Enterprise: Custom pricing

For mid-scale: $0-50/month
```

### **Vercel Deployment (React + Vite)**
```json
// vercel.json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "env": {
    "VITE_API_URL": "@vite_api_url",
    "VITE_ENV": "production"
  },
  "functions": {
    "api/**/*.js": {
      "memory": 3008,
      "maxDuration": 300
    }
  }
}
```

```bash
# Deploy with Vercel CLI
npm install -g vercel
vercel --prod

# Or connect GitHub repo for automatic deployments
# Vercel automatically builds and deploys on push
```

### **Vite Configuration for Vercel**
```javascript
// vite.config.js
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  build: {
    target: 'esnext',
    minify: 'terser',
    sourcemap: false,  // Reduce bundle size
    rollupOptions: {
      output: {
        manualChunks: {
          recharts: ['recharts'],
          'ag-grid': ['ag-grid-react', 'ag-grid-community'],
          vendors: ['react', 'react-dom', 'react-router-dom']
        }
      }
    }
  },
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path
      }
    }
  }
})
```

---

## 1.5 Heroku/Railway (Backend Hosting)

### **Heroku Strengths**
- **Simplicity:** Buildpacks, one-command deploy
- **Add-ons:** PostgreSQL, Redis, monitoring
- **Cost:** $7-50/month for basic tier

### **Railway Advantages**
- **Modern Alternative:** Better pricing ($5-20/month), GitHub integration
- **Containerization:** Native Docker support
- **No Buildpacks:** More control, faster deploys

### **Estimated Costs (Heroku)**
```
Dyno (Standard): $50/month
PostgreSQL (Standard): $50-200/month
Redis (Premium): $30/month
Total: $130-280/month
```

### **Heroku Deployment**
```bash
# Login and create app
heroku login
heroku create data-platform-api

# Add PostgreSQL addon
heroku addons:create heroku-postgresql:standard-0 --app data-platform-api

# Add Redis addon
heroku addons:create heroku-redis:premium-0 --app data-platform-api

# Deploy
git push heroku main

# Scale dynos
heroku ps:scale web=2:standard-2x worker=1:standard-2x
```

### **Railway Deployment**
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Create project
railway init

# Link to GitHub
railway link

# Deploy
railway up

# View logs
railway logs
```

---

## 1.6 CLOUD PLATFORM RECOMMENDATION MATRIX

| Criteria | AWS | GCP | Azure | Vercel | Railway |
|----------|-----|-----|-------|--------|---------|
| **ML/AI Capability** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | N/A | ⭐⭐ |
| **Cost (mid-scale)** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Scalability** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Ease of Deployment** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Data Analytics** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | N/A | ⭐⭐ |
| **Enterprise Support** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |

### **Recommendation by Use Case:**

**🥇 Best for ML-Heavy Data Platform:** GCP (BigQuery + Vertex AI native integration)  
**🥈 Best for Enterprise & Hybrid:** Azure (AD integration + multi-region)  
**🥉 Best for Cost & Scale:** AWS (mature, competitive pricing at scale)  
**🏅 Best Frontend Hosting:** Vercel (React optimization + zero-config)  
**🏅 Best Rapid Deployment:** Railway (modern stack, GitHub native)

---

# 2. FRONTEND UI/UX IMPROVEMENTS

## 2.1 Current Stack Analysis

Your stack is modern but missing critical UX features:

```json
{
  "Current": {
    "Framework": "React 18.3.1 ✓",
    "Build Tool": "Vite 6.2.5 ✓",
    "Charts": "recharts 2.15.3 ✓",
    "Data Grid": "ag-grid-react 32.3.3 ✓",
    "Routing": "react-router-dom 7.5.3 ✓"
  },
  "Missing": [
    "Component Library (UI)",
    "Styling System (CSS-in-JS or Tailwind)",
    "State Management (Redux, Zustand)",
    "Form Validation (react-hook-form + Zod)",
    "Dark Mode System",
    "Accessibility (a11y) Framework",
    "PWA Support",
    "Real-time Collaboration"
  ]
}
```

## 2.2 Recommended UI Component Libraries

### **Option A: shadcn/ui (RECOMMENDED for data platforms)**

**Why:** Headless component library built on Radix UI + Tailwind. Perfect for data analytics.

```bash
npm install shadcn-ui
npx shadcn-ui@latest init -d

# Install commonly needed components
npx shadcn-ui@latest add button card input dropdown-menu
npx shadcn-ui@latest add table tabs dialog alert toast
npx shadcn-ui@latest add select checkbox sidebar
```

**Example Data Grid with shadcn/ui:**
```jsx
// DataGrid.jsx
import { useState } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ChevronDown, ArrowUpDown } from 'lucide-react'

export function DataTable({ data, columns }) {
  const [sorting, setSorting] = useState(null)
  const [filtering, setFiltering] = useState({})

  const handleSort = (columnId) => {
    setSorting({
      columnId,
      direction: sorting?.direction === 'asc' ? 'desc' : 'asc'
    })
  }

  const sortedData = [...data].sort((a, b) => {
    if (!sorting) return 0
    const aVal = a[sorting.columnId]
    const bVal = b[sorting.columnId]
    if (aVal < bVal) return sorting.direction === 'asc' ? -1 : 1
    if (aVal > bVal) return sorting.direction === 'asc' ? 1 : -1
    return 0
  })

  return (
    <div className="border rounded-lg overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="bg-slate-100">
            {columns.map((col) => (
              <TableHead key={col.id} className="cursor-pointer">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSort(col.id)}
                  className="flex items-center gap-2"
                >
                  {col.label}
                  <ArrowUpDown className="w-4 h-4" />
                </Button>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedData.map((row, idx) => (
            <TableRow key={idx}>
              {columns.map((col) => (
                <TableCell key={col.id}>
                  {row[col.id]}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
```

### **Option B: Material-UI (Material Design)**

```bash
npm install @mui/material @emotion/react @emotion/styled
npm install @mui/icons-material

# For data grid
npm install @mui/x-data-grid
```

**Pros:** Comprehensive, enterprise-ready, Google's design language  
**Cons:** Larger bundle size (~100KB gzipped), steeper learning curve

### **Option C: Tailwind CSS (RECOMMENDED base styling)**

Use Tailwind as your styling foundation regardless of component library:

```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

```javascript
// tailwind.config.js
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f8fafc',
          500: '#0f172a',
          900: '#000814',
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.5s ease-in',
      }
    },
  },
  plugins: [],
}
```

## 2.3 Dark Mode Implementation

```jsx
// ThemeProvider.jsx
import { createContext, useState, useEffect } from 'react'

export const ThemeContext = createContext()

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    // Check localStorage and system preference
    const saved = localStorage.getItem('theme')
    if (saved) return saved
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark')

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

// App.jsx
import { ThemeProvider } from './context/ThemeProvider'
import { useTheme } from './hooks/useTheme'
import { Sun, Moon } from 'lucide-react'

function App() {
  return (
    <ThemeProvider>
      <MainApp />
    </ThemeProvider>
  )
}

function MainApp() {
  const { theme, toggleTheme } = useTheme()

  return (
    <div className="min-h-screen bg-white dark:bg-slate-950 text-black dark:text-white transition-colors">
      <button
        onClick={toggleTheme}
        className="fixed top-4 right-4 p-2 rounded-lg bg-slate-200 dark:bg-slate-800"
      >
        {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
      </button>
      {/* Rest of app */}
    </div>
  )
}
```

## 2.4 Mobile Responsiveness & PWA

```javascript
// vite.config.js with PWA support
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png'],
      manifest: {
        name: 'Data Platform',
        short_name: 'DataPlatform',
        description: 'No-code data analytics platform',
        theme_color: '#0f172a',
        background_color: '#ffffff',
        display: 'standalone',
        scope: '/',
        start_url: '/',
        icons: [
          {
            src: '/icons/icon-192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'any maskable'
          },
          {
            src: '/icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/api\./i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: { maxEntries: 500, maxAgeSeconds: 3600 }
            }
          }
        ]
      }
    })
  ],
  build: {
    target: 'esnext',
    minify: 'terser',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          recharts: ['recharts'],
          'ag-grid': ['ag-grid-react', 'ag-grid-community'],
          vendors: ['react', 'react-dom', 'react-router-dom', 'axios']
        }
      }
    }
  }
})
```

## 2.5 Accessibility Improvements

```jsx
// AccessibleDataGrid.jsx
import { useState } from 'react'
import { AlertCircle } from 'lucide-react'

export function AccessibleDataGrid({ data, columns, ariaLabel }) {
  const [focusedCell, setFocusedCell] = useState(null)

  const handleKeyDown = (e, rowIdx, colIdx) => {
    const maxRow = data.length - 1
    const maxCol = columns.length - 1

    switch (e.key) {
      case 'ArrowUp':
        e.preventDefault()
        if (rowIdx > 0) setFocusedCell([rowIdx - 1, colIdx])
        break
      case 'ArrowDown':
        e.preventDefault()
        if (rowIdx < maxRow) setFocusedCell([rowIdx + 1, colIdx])
        break
      case 'ArrowLeft':
        e.preventDefault()
        if (colIdx > 0) setFocusedCell([rowIdx, colIdx - 1])
        break
      case 'ArrowRight':
        e.preventDefault()
        if (colIdx < maxCol) setFocusedCell([rowIdx, colIdx + 1])
        break
    }
  }

  return (
    <div role="region" aria-label={ariaLabel} className="overflow-x-auto">
      <table className="w-full border-collapse border border-gray-300">
        <thead>
          <tr className="bg-gray-100">
            {columns.map((col, idx) => (
              <th
                key={idx}
                scope="col"
                className="border border-gray-300 px-4 py-2 text-left font-semibold"
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIdx) => (
            <tr key={rowIdx}>
              {columns.map((col, colIdx) => (
                <td
                  key={`${rowIdx}-${colIdx}`}
                  role="cell"
                  tabIndex={focusedCell?.[0] === rowIdx && focusedCell?.[1] === colIdx ? 0 : -1}
                  onKeyDown={(e) => handleKeyDown(e, rowIdx, colIdx)}
                  onFocus={() => setFocusedCell([rowIdx, colIdx])}
                  className={`border border-gray-300 px-4 py-2 focus:outline-2 focus:outline-blue-500 ${
                    focusedCell?.[0] === rowIdx && focusedCell?.[1] === colIdx
                      ? 'bg-blue-100'
                      : ''
                  }`}
                >
                  {row[col.id]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      {data.length === 0 && (
        <div role="status" aria-live="polite" className="flex items-center gap-2 p-4 text-yellow-700 bg-yellow-50 rounded">
          <AlertCircle size={20} />
          <p>No data available. Please upload a file or adjust filters.</p>
        </div>
      )}
    </div>
  )
}
```

## 2.6 Real-time Collaboration Features

```jsx
// RealtimeCollaborationContext.jsx
import { createContext, useEffect, useRef, useState } from 'react'
import { useAuth } from './AuthContext'

export const CollaborationContext = createContext()

export function CollaborationProvider({ children }) {
  const { user } = useAuth()
  const ws = useRef(null)
  const [activeUsers, setActiveUsers] = useState([])
  const [cursorPositions, setCursorPositions] = useState({})

  useEffect(() => {
    // WebSocket connection for real-time updates
    ws.current = new WebSocket(
      `${process.env.VITE_WS_URL || 'ws://localhost:8000'}/api/collaborate?user_id=${user?.id}`
    )

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data)
      
      switch (data.type) {
        case 'user_joined':
          setActiveUsers(prev => [...prev, data.user])
          break
        case 'cursor_move':
          setCursorPositions(prev => ({
            ...prev,
            [data.user_id]: data.position
          }))
          break
        case 'data_changed':
          // Propagate data changes to all listening components
          window.dispatchEvent(new CustomEvent('dataChanged', { detail: data }))
          break
      }
    }

    return () => ws.current?.close()
  }, [user])

  return (
    <CollaborationContext.Provider value={{ activeUsers, cursorPositions, ws }}>
      {children}
    </CollaborationContext.Provider>
  )
}

// CollaborativePresence.jsx - Show active users
export function CollaborativePresence() {
  const { activeUsers } = useContext(CollaborationContext)

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-600">Active: {activeUsers.length}</span>
      <div className="flex -space-x-2">
        {activeUsers.map(user => (
          <div
            key={user.id}
            title={user.name}
            className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 border-2 border-white flex items-center justify-center text-white text-xs font-bold"
          >
            {user.name?.[0]}
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

# 3. BACKEND ARCHITECTURE UPGRADES

## 3.1 Database Options

### **PostgreSQL (RECOMMENDED for data platform)**

**Advantages:**
- Excellent JSON support (JSONB)
- Full-text search
- Window functions for analytics
- Partitioning for large datasets
- PostGIS for geospatial data

**Implementation:**

```python
# backend/db.py with SQLAlchemy + PostgreSQL
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/data_platform"
)

engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=40)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Dataset(Base):
    __tablename__ = "datasets"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), index=True)
    owner_id = Column(String(255), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata = Column(JSONB)  # Store schema, stats, quality metrics
    data_path = Column(String(512))  # S3 or local path
    row_count = Column(Integer)
    byte_size = Column(Integer)
    
    __table_args__ = (
        Index('idx_owner_created', 'owner_id', 'created_at'),
    )

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    
    id = Column(Integer, primary_key=True)
    workflow_id = Column(String(255), index=True)
    user_id = Column(String(255), index=True)
    status = Column(String(50))  # pending, running, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    result = Column(JSONB)  # Workflow output
    logs = Column(JSONB)  # Execution logs

# Get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### **DuckDB (For OLAP / In-memory analytics)**

**Advantages:**
- Blazing fast SQL analytics
- Perfect for Polars integration
- No server needed
- Columnar storage

```python
# backend/analytics.py - DuckDB for complex analytics
import duckdb
import polars as pl

def analyze_with_duckdb(df: pl.DataFrame, query: str):
    """Run complex SQL analytics on Polars DataFrame"""
    conn = duckdb.connect(':memory:')
    conn.register('data', df)
    
    result = conn.execute(query).pl()  # Returns Polars DataFrame
    conn.close()
    return result

# Example: Complex aggregation
def calculate_cohort_retention(events_df: pl.DataFrame) -> pl.DataFrame:
    query = """
    WITH cohorts AS (
        SELECT 
            DATE_TRUNC('month', event_date)::DATE as cohort_month,
            user_id,
            MIN(event_date) OVER (PARTITION BY user_id) as user_first_date
        FROM data
    )
    SELECT 
        cohort_month,
        DATE_TRUNC('month', CURRENT_DATE)::DATE - DATE_TRUNC('month', user_first_date)::DATE as months_since_first,
        COUNT(DISTINCT user_id) as retained_users
    FROM cohorts
    GROUP BY cohort_month, months_since_first
    ORDER BY cohort_month DESC, months_since_first
    """
    
    return analyze_with_duckdb(events_df, query)
```

### **Snowflake (For Enterprise Data Warehouse)**

**When to use:** If handling 100TB+ datasets, need multi-tenant isolation

```python
# backend/snowflake_connector.py
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
import pandas as pd

def connect_snowflake():
    return snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse='COMPUTE_WH',
        database='DATA_PLATFORM_DB',
        schema='PUBLIC'
    )

def load_to_snowflake(df: pd.DataFrame, table_name: str):
    """Bulk load data to Snowflake"""
    conn = connect_snowflake()
    write_pandas(conn, df, table_name, auto_create_table=True)
    conn.close()

# Query large dataset
def query_snowflake(sql: str) -> pl.DataFrame:
    conn = connect_snowflake()
    cursor = conn.cursor()
    cursor.execute(sql)
    result = cursor.fetch_pandas_all()
    conn.close()
    return pl.from_pandas(result)
```

## 3.2 Caching Strategy

```python
# backend/cache_manager.py
from functools import wraps
import hashlib
import json
from redis import Redis
import os

redis_client = Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True,
)

def cache_result(
    ttl: int = 3600,  # 1 hour default
    key_prefix: str = "cache",
    depends_on_user: bool = False
):
    """
    Decorator to cache function results in Redis
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        depends_on_user: Include user_id in cache key for per-user caching
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Build cache key from function name, args, kwargs
            cache_key_parts = [key_prefix, func.__name__]
            
            if depends_on_user and 'current_user' in kwargs:
                cache_key_parts.append(kwargs['current_user'].id)
            
            # Hash complex arguments
            arg_hash = hashlib.md5(
                json.dumps(str(args) + str(kwargs), sort_keys=True).encode()
            ).hexdigest()
            cache_key_parts.append(arg_hash)
            
            cache_key = ":".join(cache_key_parts)
            
            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result, default=str)
            )
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_key_parts = [key_prefix, func.__name__]
            
            if depends_on_user and 'current_user' in kwargs:
                cache_key_parts.append(kwargs['current_user'].id)
            
            arg_hash = hashlib.md5(
                json.dumps(str(args) + str(kwargs), sort_keys=True).encode()
            ).hexdigest()
            cache_key_parts.append(arg_hash)
            
            cache_key = ":".join(cache_key_parts)
            
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            result = func(*args, **kwargs)
            redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result, default=str)
            )
            
            return result
        
        # Return async or sync based on function
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator

# Usage in your analytics endpoint
@app.post("/api/analytics/summary")
@cache_result(ttl=1800, key_prefix="analytics", depends_on_user=True)
async def get_analytics_summary(
    dataset_id: str,
    current_user: User = Depends(require_role("analyst"))
):
    """This result is cached per user for 30 minutes"""
    # Expensive computation
    return await compute_summary(dataset_id, current_user)

# Manual cache invalidation
def invalidate_cache(pattern: str):
    """Invalidate cache entries matching pattern"""
    keys = redis_client.keys(f"{pattern}*")
    if keys:
        redis_client.delete(*keys)

# Example: Invalidate analytics cache when dataset changes
@app.post("/api/datasets/{dataset_id}/upload")
async def upload_dataset_file(
    dataset_id: str,
    file: UploadFile,
    current_user: User = Depends(require_role("editor"))
):
    # Process upload
    result = await process_upload(file, dataset_id, current_user)
    
    # Invalidate related caches
    invalidate_cache(f"analytics:{dataset_id}")
    invalidate_cache(f"quality:{dataset_id}")
    
    return result
```

## 3.3 API Optimization

```python
# backend/main.py - Optimized FastAPI setup
from fastapi import FastAPI, Depends
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prometheus_client import Counter, Histogram
import time

# Metrics
request_counter = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up - initialize connections, caches, etc.")
    yield
    # Shutdown
    print("Shutting down - cleanup resources")

app = FastAPI(
    title="Data Platform API",
    description="No-code data analytics platform",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware stack (order matters!)
app.add_middleware(GZipMiddleware, minimum_size=1024)  # Compress responses > 1KB
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*.example.com", "localhost", "127.0.0.1"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Record metrics
    request_counter.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code
    ).inc()
    
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(process_time)
    
    return response

# Streaming response for large datasets
from fastapi.responses import StreamingResponse
import csv
import io

@app.get("/api/datasets/{dataset_id}/export")
async def export_dataset(
    dataset_id: str,
    current_user: User = Depends(require_role("analyst")),
    format: str = "csv"
):
    """Stream large datasets to avoid loading into memory"""
    
    def generate_csv():
        buffer = io.StringIO()
        writer = None
        
        # Stream data in chunks
        for chunk in fetch_dataset_chunks(dataset_id, chunk_size=5000):
            if writer is None:
                writer = csv.DictWriter(buffer, fieldnames=chunk[0].keys())
                writer.writeheader()
                yield buffer.getvalue()
                buffer.truncate(0)
                buffer.seek(0)
            
            for row in chunk:
                writer.writerow(row)
            
            yield buffer.getvalue()
            buffer.truncate(0)
            buffer.seek(0)
    
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=dataset_{dataset_id}.csv"}
    )

# Pagination for list endpoints
from pydantic import BaseModel

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int

@app.get("/api/datasets", response_model=PaginatedResponse)
async def list_datasets(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_role("viewer"))
):
    """List datasets with pagination"""
    offset = (page - 1) * page_size
    
    total = db.session.query(Dataset).filter_by(owner_id=current_user.id).count()
    datasets = (
        db.session.query(Dataset)
        .filter_by(owner_id=current_user.id)
        .offset(offset)
        .limit(page_size)
        .all()
    )
    
    return PaginatedResponse(
        items=[d.to_dict() for d in datasets],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )
```

## 3.4 Containerization (Docker)

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run with gunicorn for production
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "main:app"]
```

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine as builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production image
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

```yaml
# docker-compose.yml - Complete stack
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: dataplatform
      POSTGRES_PASSWORD: secure_password
      POSTGRES_DB: data_platform
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dataplatform"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://dataplatform:secure_password@postgres:5432/data_platform
      REDIS_URL: redis://redis:6379
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  celery_worker:
    build: ./backend
    command: celery -A worker.celery_app worker --loglevel=info -c 4
    environment:
      DATABASE_URL: postgresql://dataplatform:secure_password@postgres:5432/data_platform
      REDIS_URL: redis://redis:6379
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - postgres
      - redis
      - backend

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    environment:
      VITE_API_URL: http://backend:8000

  # Optional: Monitoring
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
```

---

# 4. PERFORMANCE OPTIMIZATIONS

## 4.1 Frontend Performance

### **Code Splitting Configuration**

```javascript
// vite.config.js - Aggressive code splitting
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  build: {
    target: 'esnext',
    minify: 'terser',
    sourcemap: false,
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunks
          'vendor-ui': ['react', 'react-dom'],
          'vendor-routing': ['react-router-dom'],
          'vendor-charts': ['recharts', 'ag-grid-react'],
          'vendor-utils': ['axios', 'date-fns', 'lodash-es'],
          
          // Feature chunks
          'dashboard': [
            './src/components/DashboardLayout.jsx',
            './src/components/DataQualityDashboard.jsx'
          ],
          'workflows': ['./src/components/WorkflowBuilder.jsx'],
          'analytics': [
            './src/components/AnalyticsWorkbench.jsx',
            './src/components/ExecutiveSummary.jsx'
          ]
        },
        // Consistent chunk names for better caching
        chunkFileNames: 'js/[name]-[hash].js',
        entryFileNames: 'js/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]'
      }
    }
  }
})
```

### **Lazy Loading Routes**

```jsx
// App.jsx - Route-based code splitting
import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Loading from './components/Loading'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Workflows = lazy(() => import('./pages/Workflows'))
const Settings = lazy(() => import('./pages/Settings'))

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={
            <Suspense fallback={<Loading />}>
              <Dashboard />
            </Suspense>
          }
        />
        <Route
          path="/analytics"
          element={
            <Suspense fallback={<Loading />}>
              <Analytics />
            </Suspense>
          }
        />
        <Route
          path="/workflows"
          element={
            <Suspense fallback={<Loading />}>
              <Workflows />
            </Suspense>
          }
        />
        <Route
          path="/settings"
          element={
            <Suspense fallback={<Loading />}>
              <Settings />
            </Suspense>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}
```

### **Image Optimization**

```jsx
// OptimizedImage.jsx - Lazy load images with srcset
import { useState, useEffect } from 'react'

export function OptimizedImage({ src, alt, srcSet, sizes = "100vw" }) {
  const [imageSrc, setImageSrc] = useState(null)
  const [isLoaded, setIsLoaded] = useState(false)

  useEffect(() => {
    // Preload image
    const img = new Image()
    img.src = src
    img.onload = () => {
      setImageSrc(src)
      setIsLoaded(true)
    }
  }, [src])

  return (
    <img
      src={imageSrc || 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg"/%3E'}
      srcSet={srcSet}
      sizes={sizes}
      alt={alt}
      loading="lazy"
      className={`transition-opacity duration-300 ${isLoaded ? 'opacity-100' : 'opacity-0'}`}
    />
  )
}
```

## 4.2 Backend Performance

### **Database Query Optimization**

```python
# backend/analytics_engine.py - Optimized queries
from sqlalchemy import func, select
from sqlalchemy.orm import Session
import polars as pl

def get_dashboard_metrics_optimized(
    db: Session,
    dataset_id: str,
    days: int = 30
) -> dict:
    """Optimized dashboard metrics query"""
    
    # Use window functions for efficiency
    stmt = select(
        Dataset.id,
        Dataset.name,
        func.count(WorkflowRun.id).over().label('total_runs'),
        func.avg(func.extract('epoch', WorkflowRun.completed_at - WorkflowRun.started_at)).label('avg_duration'),
        func.max(WorkflowRun.created_at).label('last_run_at')
    ).where(
        Dataset.id == dataset_id,
        WorkflowRun.created_at >= func.now() - interval(days)
    )
    
    results = db.execute(stmt).all()
    
    return {
        'dataset': results[0].name,
        'total_runs': results[0].total_runs,
        'avg_duration': results[0].avg_duration,
        'last_run_at': results[0].last_run_at
    }

# Index strategy
"""
CREATE INDEX idx_workflow_runs_dataset_date 
ON workflow_runs(dataset_id, created_at DESC);

CREATE INDEX idx_dataset_owner_updated 
ON datasets(owner_id, updated_at DESC);

CREATE INDEX idx_audit_logs_user_date 
ON audit_logs(user_id, created_at DESC);

-- Partial index for active workflows
CREATE INDEX idx_active_workflows 
ON workflow_runs(user_id) 
WHERE status IN ('pending', 'running');
"""
```

### **Celery Task Optimization**

```python
# backend/worker.py - Optimized task queue
from celery import Celery, group, chord
from celery.schedules import crontab
import os

celery_app = Celery(
    'data_platform',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # Hard limit 1 hour
    task_soft_time_limit=3300,  # Soft limit 55 min
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# Beat schedule (periodic tasks)
celery_app.conf.beat_schedule = {
    'cleanup-old-files': {
        'task': 'worker.cleanup_old_files',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'sync-external-data': {
        'task': 'worker.sync_external_datasets',
        'schedule': crontab(hour='*/6'),  # Every 6 hours
    },
}

@celery_app.task(bind=True, max_retries=3)
def async_run_automl(self, dataset_id: str, user_id: str):
    """Run AutoML with retry logic"""
    try:
        # Fetch dataset
        df = fetch_dataset(dataset_id)
        
        # Run AutoML
        result = run_automl_stateless(df)
        
        # Store result
        save_workflow_result(user_id, dataset_id, result)
        
        return {'status': 'completed', 'result': result}
    
    except Exception as exc:
        # Exponential backoff retry
        countdown = 2 ** self.request.retries
        raise self.retry(exc=exc, countdown=countdown)

# Parallel task execution
@app.post("/api/batch-process")
async def batch_process_datasets(request: BatchProcessRequest):
    """Process multiple datasets in parallel"""
    
    # Create parallel tasks
    job = group(
        async_run_automl.s(dataset_id, current_user.id)
        for dataset_id in request.dataset_ids
    )
    
    # Execute and get results
    result = job.apply_async()
    
    return {
        'task_id': result.id,
        'status': 'processing',
        'count': len(request.dataset_ids)
    }

# Monitor task progress
@app.get("/api/task/{task_id}/status")
async def get_task_status(task_id: str):
    """Get task progress"""
    from celery.result import AsyncResult
    
    task = AsyncResult(task_id, app=celery_app)
    
    return {
        'status': task.status,
        'current': task.info.get('current', 0) if isinstance(task.info, dict) else 0,
        'total': task.info.get('total', 100) if isinstance(task.info, dict) else 100,
        'percentage': int(100 * task.info.get('current', 0) / task.info.get('total', 100))
        if isinstance(task.info, dict) else 0,
        'result': task.result if task.successful() else None
    }
```

### **Async Processing**

```python
# backend/async_handler.py - Async patterns
from fastapi import BackgroundTasks
import asyncio
import aiofiles

@app.post("/api/datasets/{dataset_id}/process")
async def process_large_dataset(
    dataset_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role("editor"))
):
    """Process data asynchronously"""
    
    # Return immediately
    background_tasks.add_task(
        process_dataset_background,
        dataset_id,
        current_user.id
    )
    
    return {
        'status': 'processing',
        'dataset_id': dataset_id,
        'poll_url': f'/api/datasets/{dataset_id}/status'
    }

async def process_dataset_background(dataset_id: str, user_id: str):
    """Background processing with async file I/O"""
    try:
        # Async file reading
        async with aiofiles.open(f'./data/{dataset_id}.csv', 'r') as f:
            content = await f.read()
        
        # Async processing
        df = await asyncio.to_thread(
            pl.read_csv,
            content.encode()
        )
        
        # Async database save
        await save_to_db_async(dataset_id, df, user_id)
        
    except Exception as e:
        await log_error_async(dataset_id, str(e))
```

## 4.3 Infrastructure Performance

### **CDN Configuration (AWS CloudFront)**

```python
# CloudFront distribution for frontend
import boto3

cloudfront = boto3.client('cloudfront')

distribution_config = {
    'CallerReference': 'data-platform-cdn-v1',
    'Origins': {
        'Quantity': 1,
        'Items': [
            {
                'Id': 'myS3Origin',
                'DomainName': 'data-platform-frontend.s3.amazonaws.com',
                'S3OriginConfig': {
                    'OriginAccessIdentity': 'origin-access-identity/cloudfront/ABCDEFG1234567'
                }
            }
        ]
    },
    'DefaultCacheBehavior': {
        'AllowedMethods': {
            'Quantity': 2,
            'Items': ['GET', 'HEAD']
        },
        'Compress': True,  # Enable gzip compression
        'ViewerProtocolPolicy': 'redirect-to-https',
        'ForwardedValues': {
            'QueryString': False,
            'Cookies': {'Forward': 'none'}
        },
        'MinTTL': 0,
        'DefaultTTL': 3600,
        'MaxTTL': 31536000
    },
    'CacheBehaviors': [
        {
            'PathPattern': '/api/*',
            'AllowedMethods': {
                'Quantity': 7,
                'Items': ['GET', 'HEAD', 'OPTIONS', 'PUT', 'POST', 'PATCH', 'DELETE']
            },
            'ViewerProtocolPolicy': 'https-only',
            'ForwardedValues': {
                'QueryString': True,
                'Cookies': {'Forward': 'all'},
                'Headers': {
                    'Quantity': 1,
                    'Items': ['Authorization']
                }
            },
            'MinTTL': 0,
            'DefaultTTL': 0,
            'MaxTTL': 0
        }
    ]
}
```

### **Monitoring & Alerting (Prometheus + Grafana)**

```python
# backend/monitoring.py - Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
api_requests = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

api_latency = Histogram(
    'api_request_duration_seconds',
    'API request latency',
    ['method', 'endpoint'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0)
)

db_query_time = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['operation', 'table']
)

active_tasks = Gauge(
    'celery_active_tasks',
    'Number of active Celery tasks'
)

# Middleware to collect metrics
@app.middleware("http")
async def collect_metrics(request, call_next):
    start = time.time()
    response = await call_next(request)
    
    duration = time.time() - start
    api_requests.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    api_latency.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response
```

```yaml
# prometheus.yml - Scrape configuration
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'fastapi'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'

  - job_name: 'celery'
    static_configs:
      - targets: ['localhost:5555']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']

rule_files:
  - 'alert_rules.yml'
```

```yaml
# alert_rules.yml - Alert definitions
groups:
  - name: data_platform
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(api_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: HighLatency
        expr: histogram_quantile(0.95, api_request_duration_seconds) > 5
        for: 5m
        annotations:
          summary: "API latency is high"

      - alert: CeleryQueueBacklog
        expr: celery_active_tasks > 100
        for: 10m
        annotations:
          summary: "Celery task queue backlog"
```

---

# 5. IMPLEMENTATION ROADMAP

## Phase 1: Foundation (Weeks 1-4)
- [ ] Set up PostgreSQL database
- [ ] Implement caching layer (Redis optimization)
- [ ] Add Tailwind CSS + shadcn/ui
- [ ] Implement dark mode

## Phase 2: Backend Architecture (Weeks 5-8)
- [ ] Dockerize application
- [ ] Set up CI/CD pipeline (GitHub Actions or similar)
- [ ] Implement monitoring (Prometheus + Grafana)
- [ ] Database indexing strategy

## Phase 3: Frontend Modernization (Weeks 9-12)
- [ ] Code splitting and lazy loading
- [ ] PWA implementation
- [ ] Accessibility audit and fixes
- [ ] Mobile responsiveness

## Phase 4: Cloud Deployment (Weeks 13-16)
- [ ] Choose primary cloud platform
- [ ] Set up infrastructure as code (Terraform)
- [ ] Migrate to cloud database
- [ ] Set up CDN and caching

## Phase 5: Optimization & Scaling (Weeks 17-20)
- [ ] Load testing and optimization
- [ ] Real-time collaboration features
- [ ] Advanced analytics caching
- [ ] Performance monitoring dashboard

---

# 6. COST ESTIMATES SUMMARY

| Component | AWS | GCP | Azure | Vercel | Railway |
|-----------|-----|-----|-------|--------|---------|
| **Monthly** | $350-600 | $410-820 | $470-1070 | $0-50 | $50-150 |
| **First Year** | $5000-8000 | $6000-10000 | $7000-13000 | $500-1000 | $1000-2500 |
| **Scale-up (10x)** | $2000-4000 | $3000-6000 | $3500-8000 | $500-2000 | $2000-5000 |

---

# 7. RECOMMENDED TECHNOLOGY STACK FOR DEPLOYMENT

```
Frontend:
- React 18 + Vite (current ✓)
- Tailwind CSS + shadcn/ui
- PWA (vite-plugin-pwa)
- Deployment: Vercel or CloudFront

Backend:
- FastAPI (current ✓)
- PostgreSQL (relational data)
- DuckDB (analytics queries)
- Redis (caching + Celery)
- Docker (containerization)

Cloud Infrastructure:
- Primary: GCP (best ML/analytics)
- Alternative: AWS (mature, cost-competitive)
- Frontend: Vercel (optimized for React)
- CDN: Cloudflare (cost-effective)

Monitoring:
- Prometheus + Grafana (metrics)
- DataDog or New Relic (APM)
- ELK Stack or CloudWatch (logging)
```

---

# 8. QUICK START: Deploy to GCP

```bash
# 1. Create GCP project
gcloud projects create data-platform-prod --name="Data Platform"
gcloud config set project data-platform-prod

# 2. Enable APIs
gcloud services enable \
  run.googleapis.com \
  sql.googleapis.com \
  compute.googleapis.com \
  cloudbuild.googleapis.com

# 3. Create Cloud SQL PostgreSQL
gcloud sql instances create data-platform-db \
  --database-version POSTGRES_15 \
  --tier db-f1-micro \
  --region us-central1

# 4. Create database
gcloud sql databases create data_platform \
  --instance data-platform-db

# 5. Deploy backend to Cloud Run
gcloud run deploy data-platform-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars DATABASE_URL="postgresql://user:pass@10.0.0.2:5432/data_platform" \
  --allow-unauthenticated

# 6. Deploy frontend
vercel deploy --prod

# 7. Monitor
gcloud monitoring dashboards create --config-from-file dashboard.yaml
```

---

This comprehensive guide covers everything needed to scale your Stateless Data Platform from local development to production with enterprise-grade architecture.
