# VA Calibration Platform - Deployment Guide

## Render.com Deployment

This project is configured for easy deployment on Render.com with automatic setup via `render.yaml`.

### Architecture

- **Frontend**: React + Vite static site
- **Backend**: FastAPI Python application
- **Worker**: Celery background job processor
- **Database**: Redis (for job queue and caching)

### Quick Deploy

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Add Render deployment configuration"
   git push origin main
   ```

2. **Create Render Account**
   - Go to https://render.com
   - Sign up/login with GitHub

3. **Deploy via Blueprint**
   - Click "New +" → "Blueprint"
   - Select your repository: `cliu238/vacalibration`
   - Render will automatically read `render.yaml`
   - Click "Apply" to create all services

4. **Services Created**
   - `va-calibration-api` - Backend API (free tier)
   - `va-calibration-worker` - Celery worker (free tier)
   - `va-calibration-frontend` - React frontend (free tier)
   - `va-calibration-redis` - Redis database (free tier)

### Environment Variables

All environment variables are configured automatically via `render.yaml`:

- `REDIS_URL` - Auto-configured from Redis service
- `CELERY_BROKER_URL` - Auto-configured from Redis service
- `VITE_API_BASE_URL` - Auto-configured to point to backend

### Custom Domain (Optional)

1. Go to your frontend service in Render dashboard
2. Click "Settings" → "Custom Domain"
3. Add your domain and follow DNS instructions

### Monitoring

- **Logs**: Available in Render dashboard for each service
- **Health Checks**: Backend has `/` endpoint for health monitoring
- **Metrics**: View in Render dashboard

### Local Development

```bash
# Backend
cd api
poetry install
poetry run uvicorn app.main_direct:app --reload

# Frontend
cd mock-to-real
npm install
npm run dev

# Redis (via Docker)
docker run -p 6379:6379 redis:latest
```

### Costs

Free tier includes:
- 750 hours/month per service
- Enough for 4 services with some usage
- Services sleep after 15 min of inactivity
- No credit card required

Upgrade to paid tier ($7/month per service) for:
- No sleeping
- Better performance
- Custom domains
- More resources

### Troubleshooting

**Build fails:**
- Check logs in Render dashboard
- Verify `poetry.lock` is committed
- Ensure R packages are available

**Services can't connect:**
- Verify environment variables in dashboard
- Check service health endpoints
- Review service logs

**Frontend can't reach backend:**
- Verify `VITE_API_BASE_URL` is set correctly
- Check CORS settings in backend
- Ensure backend service is running

### Support

- Render Docs: https://render.com/docs
- Project Issues: https://github.com/cliu238/vacalibration/issues
