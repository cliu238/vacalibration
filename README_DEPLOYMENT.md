# VA Calibration Platform - Deployment Guide

## Render.com Deployment with Upstash Redis

This project is configured for deployment on Render.com's free tier with Upstash Redis for job queue management.

### Architecture

- **Frontend**: React + Vite static site
- **Backend**: FastAPI Python application with Celery
- **Worker**: Celery background job processor (listening to `calibration` queue)
- **Database**: Upstash Redis (external SSL/TLS Redis service)

### Prerequisites

1. **GitHub Repository**
   - Fork/clone: https://github.com/cliu238/vacalibration
   - Ensure you have push access

2. **Upstash Redis Account**
   - Sign up at https://upstash.com
   - Create a new Redis database (free tier available)
   - Note your Redis URL (starts with `rediss://`)

3. **Render Account**
   - Sign up at https://render.com
   - Connect your GitHub account

### Step-by-Step Deployment

#### 1. Set Up Upstash Redis

```bash
# Create Upstash account at https://upstash.com
# Create a new Redis database
# Copy the Redis URL - it should look like:
# rediss://default:YOUR_PASSWORD@YOUR_DATABASE.upstash.io:6379
```

**Important**: Use the `rediss://` URL (with SSL), NOT `redis://`

#### 2. Deploy to Render via Blueprint

```bash
# 1. Push your code to GitHub
git add .
git commit -m "Deploy to Render"
git push origin main

# 2. In Render Dashboard:
# - Click "New +" → "Blueprint"
# - Select repository: cliu238/vacalibration
# - Render reads render.yaml automatically
# - Click "Apply"
```

#### 3. Configure Environment Variables

**CRITICAL**: After blueprint deployment, update environment variables for BOTH services:

**For `va-calibration-api` service:**
```bash
REDIS_URL=rediss://default:YOUR_PASSWORD@YOUR_DATABASE.upstash.io:6379
CELERY_BROKER_URL=rediss://default:YOUR_PASSWORD@YOUR_DATABASE.upstash.io:6379
CELERY_RESULT_BACKEND=rediss://default:YOUR_PASSWORD@YOUR_DATABASE.upstash.io:6379
```

**For `va-calibration-worker` service:**
```bash
REDIS_URL=rediss://default:YOUR_PASSWORD@YOUR_DATABASE.upstash.io:6379
CELERY_BROKER_URL=rediss://default:YOUR_PASSWORD@YOUR_DATABASE.upstash.io:6379
CELERY_RESULT_BACKEND=rediss://default:YOUR_PASSWORD@YOUR_DATABASE.upstash.io:6379
```

**⚠️ Important Notes:**
- Use `rediss://` (double 's' for SSL), NOT `redis://`
- Both API and Worker need identical Redis URLs
- After updating env vars, manually trigger redeployment

#### 4. Manual Redeployment (Required After Env Changes)

```bash
# In Render Dashboard:
# For each service (api and worker):
# 1. Go to service page
# 2. Click "Manual Deploy" → "Deploy latest commit"
# 3. Wait 2-3 minutes for deployment
```

#### 5. Verify Deployment

```bash
# Check API health
curl https://va-calibration-api.onrender.com/

# Check Celery debug endpoint
curl https://va-calibration-api.onrender.com/debug/celery

# Expected response:
# {
#   "celery_status": "connected",
#   "active_workers": ["celery@srv-..."],
#   "worker_count": 1
# }

# Check worker health with diagnostics
curl https://va-calibration-worker.onrender.com/health

# Expected response:
# {
#   "status": "healthy",
#   "celery_status": "connected",
#   "worker_count": 1,
#   "broker_connected": true
# }
```

### Services Created

1. **va-calibration-api** - Backend API
   - FastAPI application
   - Handles job creation and status
   - Port: 10000 (auto-assigned)

2. **va-calibration-worker** - Celery Worker
   - Processes calibration jobs from `calibration` queue
   - Health check endpoint at `/health`
   - Runs with `--queues=calibration` flag

3. **va-calibration-frontend** - React Frontend
   - Static site deployment
   - Connects to API via `VITE_API_BASE_URL`

### Key Configuration Files

**`render.yaml`** - Blueprint configuration:
```yaml
services:
  - type: web
    name: va-calibration-api
    envVars:
      - key: REDIS_URL
        sync: false  # Set manually in dashboard
      - key: CELERY_BROKER_URL
        sync: false
      - key: CELERY_RESULT_BACKEND
        sync: false
```

**`api/start_worker.sh`** - Worker startup script:
```bash
# Key configuration:
# - Checks environment variables are set
# - Starts health check server
# - Starts Celery worker with --queues=calibration
poetry run celery -A app.job_endpoints.celery_app worker \
  --loglevel=info \
  --pool=solo \
  --queues=calibration
```

**`api/app/job_endpoints.py`** - Celery SSL configuration:
```python
# SSL configuration for rediss:// URLs
if broker_url.startswith("rediss://"):
    import ssl
    celery_app.conf.update(
        broker_use_ssl={'ssl_cert_reqs': ssl.CERT_NONE},
        redis_backend_use_ssl={'ssl_cert_reqs': ssl.CERT_NONE}
    )
```

### Common Commands

**Test job creation:**
```bash
curl -X POST 'https://va-calibration-api.onrender.com/jobs/calibrate' \
  -H 'Content-Type: application/json' \
  -d '{"age_group": "neonate", "country": "Mozambique"}'
```

**Check job status:**
```bash
curl https://va-calibration-api.onrender.com/jobs/JOB_ID
```

**List all jobs:**
```bash
curl https://va-calibration-api.onrender.com/jobs
```

**View worker logs:**
```bash
# In Render Dashboard:
# va-calibration-worker → Logs tab
# Look for:
# - "Starting Celery worker..."
# - "CELERY_BROKER_URL: rediss://..."
# - "celery@srv-... ready"
```

### Known Limitations

1. **No R Runtime on Render Free Tier**
   - Rscript is not available in the worker environment
   - Jobs will fail with "No such file or directory: 'Rscript'"
   - For production use, upgrade to paid tier and install R
   - Or use a different platform (e.g., AWS, Google Cloud)

2. **Cold Starts**
   - Free tier services sleep after 15 minutes of inactivity
   - First request may take 50+ seconds to wake up

3. **Resource Limits**
   - Free tier has limited CPU/memory
   - May timeout on large calibration jobs

### Troubleshooting

#### Worker Not Connecting to Broker

**Symptoms:**
```json
{"celery_status": "no_workers", "worker_count": 0}
```

**Solutions:**
1. Check environment variables use `rediss://` (not `redis://`)
2. Verify BOTH api and worker have identical Redis URLs
3. Manually trigger worker redeployment
4. Check worker logs for connection errors

#### CORS Errors

**Symptoms:**
```
Access-Control-Allow-Origin header is not present
```

**Solutions:**
1. API already configured with `allow_origins=["*"]`
2. Usually caused by API 500 errors before CORS middleware
3. Check API logs for actual error
4. Verify API is responding to requests

#### Jobs Stuck in "Pending"

**Symptoms:**
- Jobs created but never progress
- Status remains "pending" indefinitely

**Solutions:**
1. Verify worker is connected: `/debug/celery`
2. Check worker is listening to correct queue: `--queues=calibration`
3. Restart worker service in Render dashboard
4. Check worker logs for task pickup

#### Environment Variables Not Taking Effect

**Symptoms:**
- Changes to env vars don't apply
- Still seeing old Redis URLs in logs

**Solutions:**
1. **MUST manually redeploy after env var changes**
2. In Render Dashboard: "Manual Deploy" → "Deploy latest commit"
3. Wait for deployment to complete (2-3 minutes)
4. Verify changes in logs: check for "CELERY_BROKER_URL: rediss://..."

#### SSL Certificate Errors with Redis

**Symptoms:**
```
ValueError: A rediss:// URL must have parameter ssl_cert_reqs
```

**Solution:**
- Already fixed in code with `ssl_cert_reqs=ssl.CERT_NONE`
- If still occurring, verify latest code is deployed

### Cost Breakdown

**Free Tier (Current Setup):**
- Render: 750 hours/month per service (3 services = free)
- Upstash Redis: 10,000 commands/day free tier
- Total: $0/month

**Paid Upgrade Options:**
- Render ($7/month per service):
  - No sleeping
  - Better performance
  - Custom domains
  - More resources
- Upstash ($10/month):
  - More commands
  - Better performance
  - Higher limits

### Local Development

```bash
# Start Upstash Redis connection locally
export REDIS_URL="rediss://default:YOUR_PASSWORD@YOUR_DATABASE.upstash.io:6379"
export CELERY_BROKER_URL="$REDIS_URL"
export CELERY_RESULT_BACKEND="$REDIS_URL"

# Backend API
cd api
poetry install
poetry run uvicorn app.main_direct:app --reload --port 8000

# Celery Worker (in another terminal)
cd api
poetry run celery -A app.job_endpoints.celery_app worker \
  --loglevel=info \
  --pool=solo \
  --queues=calibration

# Frontend (in another terminal)
cd mock-to-real
npm install
export VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

### Production Checklist

Before going to production:

- [ ] Upgrade Render plan to avoid cold starts
- [ ] Install R runtime for actual calibration processing
- [ ] Set up custom domain for frontend
- [ ] Configure proper authentication
- [ ] Set up monitoring and alerts
- [ ] Implement rate limiting
- [ ] Add database backups
- [ ] Configure SSL certificates
- [ ] Set up CI/CD pipeline
- [ ] Add comprehensive error logging

### Support & Resources

- **Render Documentation**: https://render.com/docs
- **Upstash Documentation**: https://docs.upstash.com/redis
- **Celery Documentation**: https://docs.celeryq.dev/
- **Project Issues**: https://github.com/cliu238/vacalibration/issues

### Quick Reference

**Important URLs:**
- API: https://va-calibration-api.onrender.com
- Frontend: https://va-frontend-direct.onrender.com
- Worker Health: https://va-calibration-worker.onrender.com/health

**Debug Endpoints:**
- `/debug/celery` - Check worker connectivity
- `/debug/redis` - Test Redis operations
- `/debug/test-job` - Create test job with diagnostics

**Environment Variables Format:**
```bash
# ✅ CORRECT (SSL with rediss://)
REDIS_URL=rediss://default:password@host.upstash.io:6379

# ❌ WRONG (no SSL with redis://)
REDIS_URL=redis://default:password@host.upstash.io:6379
```
