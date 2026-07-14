# DataSaaS Frontend

React + Vite-based frontend for DataSaaS Pro featuring enterprise authentication and real-time dashboards.

## Features

- **Modern UI**: React 18 + Vite for fast builds and hot module replacement (HMR)
- **Enterprise Auth**: JWT-based login, email verification, password reset
- **Responsive Design**: Mobile-friendly layout with CSS Grid and Flexbox
- **Real-Time Charts**: Interactive dashboards with live data updates
- **Session Management**: Automatic logout on token expiry, auth state persistence
- **Multi-Role Support**: Admin, analyst, and viewer role-based UI

## Quick Start

### 1. Install Dependencies

```bash
cd my-data-platform/frontend
npm ci
```

### 2. Configure Environment

Create a `.env.local` file (optional, for non-standard API URLs):

```bash
# For production builds targeting a specific backend
VITE_API_BASE_URL=https://your-api.example.com:8000
```

For local development, the frontend automatically uses `http://localhost:8000`.

### 3. Development Server

```bash
npm run dev
```

The app will start on `http://localhost:5173` (or next available port) with hot module reloading.

### 4. Production Build

```bash
npm run build
```

Built artifacts go to `dist/` folder (ready for deployment to GitHub Pages or any static host).

### 5. Preview Production Build

```bash
npm run preview
```

Serves the `dist/` folder locally to preview production output.

## Project Structure

```
src/
├── main.jsx              # App entry point
├── App.jsx               # Main component
├── config.js             # API base URL configuration
├── styles.css            # Global styles
├── context/
│   └── AuthContext.jsx   # Auth state and API integration
├── pages/
│   ├── Login.jsx         # Login/Register/Verify/Reset UI
│   ├── Dashboard.jsx     # Main dashboard
│   └── [other pages]
└── components/
    ├── Header.jsx        # Navigation header
    ├── Sidebar.jsx       # Sidebar menu
    └── [feature components]
```

## Authentication Flow

### Login & Registration

1. User enters credentials on `/login`
2. Frontend calls `POST /api/auth/login` or `POST /api/auth/register`
3. Backend returns JWT `access_token` (valid for configured hours, default 2)
4. Token stored in `sessionStorage` with expiry timestamp
5. Axios default header updated: `Authorization: Bearer <token>`

### Email Verification

1. New users receive verification email with token link (24-hour expiry default)
2. Link redirects to `GET /login?verify_token=<token>`
3. Frontend extracts token from URL, calls `GET /api/auth/verify-email?token=<token>`
4. User can now login

### Password Reset

1. User requests reset: `POST /api/auth/password-reset/request` with email
2. Receives email with reset link: `GET /login?reset_token=<token>` (30-min expiry default)
3. Frontend extracts token, allows user to enter new password
4. Calls `POST /api/auth/password-reset/confirm` with token + new_password
5. Password updated; user can login with new credentials

### Auto-Logout on 401

Axios response interceptor checks for 401 status:
- Clears token and auth state
- Redirects to login (optional, configured in AuthContext)
- User can re-login

## Configuration

### API Base URL

**File**: `src/config.js`

```javascript
// Local dev: auto-uses http://localhost:8000
// Production (Pages): requires VITE_API_BASE_URL env var during build

export const API_BASE_URL = 
  import.meta.env.VITE_API_BASE_URL || 
  (isLocalHost ? 'http://localhost:8000' : null);
```

**During Build**:

```bash
# Local dev (auto-configured)
npm run dev

# Production targeting external backend
VITE_API_BASE_URL=https://api.example.com npm run build

# Production on GitHub Pages (no backend, Pages-only demo)
npm run build
# (App shows "Backend API not configured" message)
```

### Vite Base Path

**File**: `vite.config.js`

For GitHub Pages deployment on subdomain `https://username.github.io/repo-name/`:

```javascript
export default defineConfig({
  plugins: [react()],
  base: process.env.NODE_ENV === 'production' 
    ? '/master_data_analytics/'  // Match repo name
    : '/',
});
```

This ensures assets (`/assets/index.js`, `/assets/style.css`) resolve correctly.

## Build & Deployment

### Local Build

```bash
npm run build
# Output: dist/ folder with index.html, assets/, and SPA fallback (404.html)
```

### Deploy to GitHub Pages

The repository includes a GitHub Actions workflow (`.github/workflows/*.yml`) that:

1. Builds frontend on push to `master`
2. Publishes artifacts to `gh-pages` branch
3. GitHub Pages automatically serves from `gh-pages`

**Manual Deploy** (using worktree):

```bash
# Build first
npm run build

# Navigate to repo root, create temp worktree on gh-pages
git worktree add temp-gh-pages gh-pages
cd temp-gh-pages

# Copy dist contents
cp -r ../my-data-platform/frontend/dist/* .

# Commit and push
git add -A
git commit -m "Update gh-pages"
git push origin gh-pages

# Cleanup
cd ..
git worktree remove temp-gh-pages
```

### Deploy to Other Hosts (Netlify, Vercel, etc.)

1. Connect repo to host
2. Set build command: `npm run build`
3. Set output directory: `dist`
4. Set environment variable: `VITE_API_BASE_URL=<your-backend-url>`
5. Deploy

## Development

### Hot Module Reloading (HMR)

Vite automatically reloads changed modules without full page reload during dev:

```bash
npm run dev
# Edit any .jsx or .css file → browser updates instantly
```

### Debugging

**Browser DevTools**:

- Open DevTools (F12)
- **Sources**: View source-mapped React components
- **Network**: Inspect API calls (XHR requests to `/api/auth/*`)
- **Application**: Check `sessionStorage` for auth token
- **Console**: View logs and errors

**Redux DevTools** (if integrated):

- Chrome/Firefox extension shows state changes and dispatch history

### Linting

```bash
npm run lint  # Check for issues (if configured)
npm run lint --fix  # Auto-fix issues
```

### Testing

```bash
npm run test  # Run Jest/Vitest tests (if configured)
npm run test -- --watch  # Watch mode
```

## Dependencies

Key packages (see `package.json` for full list):

- `react` — UI library
- `react-dom` — React DOM rendering
- `vite` — Build tool and dev server
- `axios` — HTTP client (for API calls)
- `react-router-dom` — Client-side routing (if using)
- `ag-grid-react`, `ag-grid-community` — Data grid for tables
- `chart.js`, `react-chartjs-2` — Charts (if included)

Install:

```bash
npm ci  # Clean install, respects package-lock.json
npm install <package>  # Add new package
npm install --save-dev <dev-package>  # Add dev dependency
```

## Environment Variables

Create `.env.local` in frontend root for local-only overrides:

```bash
# Backend API URL (for production builds)
VITE_API_BASE_URL=https://your-backend.example.com

# Other Vite variables (prefix with VITE_)
VITE_APP_NAME=DataSaaS Pro
```

**Build-time variables** (must start with `VITE_`):

```bash
# Available in app as import.meta.env.VITE_*
console.log(import.meta.env.VITE_API_BASE_URL);
```

## Troubleshooting

### Issue: "Backend API not configured"

**Cause**: Frontend running on GitHub Pages without `VITE_API_BASE_URL` set.

**Fix**: 
- For local dev: just run `npm run dev` (auto-uses port 8000)
- For production: rebuild with `VITE_API_BASE_URL=<your-url> npm run build`

### Issue: 404 on assets (`.js`, `.css` files)

**Cause**: Vite `base` path doesn't match deployment path.

**Fix**: Update `vite.config.js`:

```javascript
base: '/your-subdomain/'  // Match GitHub repo name or deployment path
```

Then rebuild:

```bash
npm run build
```

### Issue: "Mixed Content" errors in browser console

**Cause**: Frontend over HTTPS calling API over HTTP.

**Fix**: 
- Ensure `VITE_API_BASE_URL` uses HTTPS
- Update `src/config.js` to enforce HTTPS for non-local hosts

### Issue: CORS errors when calling backend

**Cause**: Backend doesn't allow frontend origin.

**Fix**: 
1. Ensure backend has CORS middleware:
   ```python
   # In FastAPI backend (main.py)
   from fastapi.middleware.cors import CORSMiddleware
   app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])
   ```
2. Or: Use proxy during dev (update `vite.config.js` server section)

### Issue: Token not persisting across sessions

**Cause**: Browser blocking `sessionStorage` or token expired.

**Fix**:
- Check DevTools → Application → Session Storage for token
- Verify token expiry: default is 2 hours (update `JWT_EXPIRE_HOURS` in backend `.env`)
- Check `403` errors in Network tab = token invalid or expired

### Issue: Slow build or dev server startup

**Cause**: Many modules or large dependencies.

**Fix**:
- Use `npm ci` instead of `npm install`
- Update Vite: `npm install vite@latest`
- Check for unused dependencies: `npm audit`

## Production Checklist

- [ ] Run `npm run build` and verify `dist/` folder
- [ ] Test production build locally: `npm run preview`
- [ ] Set `VITE_API_BASE_URL` to production backend URL
- [ ] Verify asset paths in built `index.html` (check `<script>` and `<link>` tags)
- [ ] Deploy `dist/` to static host (GitHub Pages, S3, etc.)
- [ ] Clear browser cache and verify live site loads
- [ ] Check DevTools Network → no 404s for `.js`, `.css`
- [ ] Test login/logout flows end-to-end
- [ ] Verify SSL/HTTPS is enabled
- [ ] Monitor console for errors and warnings

## Performance Optimization

- **Code Splitting**: Vite automatically splits chunks for async imports
- **CSS Minification**: Vite includes in production build
- **Lazy Loading**: Wrap route components in `React.lazy()`
- **Image Optimization**: Use WEBP format where possible
- **Caching Headers**: Set far-future expires on `/assets/` (static host config)

## Useful Commands

```bash
npm run dev              # Start dev server (http://localhost:5173)
npm run build            # Build production artifacts
npm run preview          # Preview production build locally
npm run lint             # Check code quality (if configured)
npm ci                   # Clean install dependencies
npm install <pkg>        # Add new dependency
npm install -D <pkg>     # Add dev dependency
npm audit                # Check for vulnerabilities
npm outdated             # Check for outdated packages
npm update               # Update packages
```

## Debugging API Calls

**In Browser Console**:

```javascript
// Check stored auth token
console.log(sessionStorage.getItem('my_data_platform_auth'));

// Check API base URL
import { API_BASE_URL } from './config';
console.log(API_BASE_URL);

// Make manual API call (if logged in)
fetch('http://localhost:8000/api/auth/me', {
  headers: { 'Authorization': `Bearer ${JSON.parse(sessionStorage.getItem('my_data_platform_auth')).token}` }
}).then(r => r.json()).then(console.log);
```

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and test locally: `npm run dev`
3. Run linter and tests: `npm run lint && npm run test`
4. Commit with clear message: `git commit -m "Add feature"`
5. Push and open a PR

## License

Same as parent project.
