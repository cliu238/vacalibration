# VA-Calibration Implementation Roadmap

## Project Overview
The VA-Calibration project provides an API interface for calibrating computer-coded verbal autopsy (CCVA) algorithm outputs using the vacalibration R package. The system consists of:
- **R Package**: Core calibration logic (vacalibration)
- **API Layer**: FastAPI backend for RESTful interface
- **Frontend**: React-based visualization dashboard (info-visual-scape submodule)

## Current Status Summary

### ✅ Completed Components

#### Phase 1: Core Functionality
- [x] **Basic calibration endpoint** - `/calibrate` endpoint implemented in `main_direct.py`
- [x] **Sample data integration** - COMSAMOZ datasets loaded from R package
- [x] **Direct R package execution** - R scripts called via subprocess
- [x] **Health check endpoint** - `/` endpoint with R status verification
- [x] **Example data endpoint** - `/example-data` for testing
- [x] **CORS support** - Enabled for frontend integration
- [x] **Poetry-based dependency management** - Python environment setup
- [x] **API documentation** - Comprehensive API design document
- [x] **Frontend submodule** - React dashboard integrated (info-visual-scape)

#### Infrastructure
- [x] **Docker support** - Dockerfile created for containerization
- [x] **R script integration** - `run_calibration.R` wrapper script
- [x] **Error handling** - Basic exception handling in API
- [x] **Data validation** - Pydantic models for request/response

### 🚧 In Progress

#### Phase 2: Enhanced Features
- [ ] **Full endpoint implementation** - Several endpoints designed but not implemented:
  - [ ] GET `/datasets` - List available sample datasets
  - [ ] GET `/datasets/{dataset_id}/preview` - Preview sample data
  - [ ] POST `/convert/causes` - Convert specific to broad causes
  - [ ] POST `/validate` - Validate input data format
  - [ ] GET `/cause-mappings/{age_group}` - Get cause mappings
  - [ ] GET `/supported-configurations` - Get supported configs

### 📋 To Be Implemented

#### Phase 2: Enhanced Features (Continued)
- [ ] **Asynchronous processing** - WebSocket and job queue system:
  - [ ] WebSocket `/calibrate/{job_id}/logs` - Real-time log streaming
  - [ ] GET `/calibrate/{job_id}/status` - Job status polling
  - [ ] Background job processing with Redis/Celery
- [ ] **Batch processing** - Multiple calibration requests
- [ ] **Result caching** - Cache calibration results for sample datasets
- [ ] **Comprehensive validation** - Input data validation beyond basic checks
- [ ] **OpenVA integration** - Direct integration with openVA outputs (currently users must pre-process)

#### Phase 3: Production Ready
- [ ] **Authentication system** - API key or JWT authentication
- [ ] **Rate limiting** - Request throttling per client
- [ ] **Advanced monitoring & logging**:
  - [ ] Structured logging with log levels
  - [ ] Metrics collection (Prometheus/Grafana)
  - [ ] Error tracking (Sentry integration)
- [ ] **Database integration** - Store job history and results
- [ ] **Docker Compose setup** - Multi-container orchestration
- [ ] **Kubernetes deployment** - Production-ready K8s manifests:
  - [ ] Deployment configurations
  - [ ] Service definitions
  - [ ] Ingress rules
  - [ ] ConfigMaps and Secrets
  - [ ] Horizontal Pod Autoscaling

#### Phase 4: Advanced Features
- [ ] **Real-time calibration updates** - Live progress during MCMC iterations
- [ ] **Custom misclassification matrices** - User-provided calibration matrices
- [ ] **Multi-country ensemble calibration** - Cross-country calibration support
- [ ] **GraphQL API option** - Alternative API interface
- [ ] **API versioning** - `/v1/` prefix with version management
- [ ] **Advanced caching strategies** - Redis for distributed caching
- [ ] **Data export formats** - CSV, Excel, JSON export options
- [ ] **Webhook notifications** - Notify clients when jobs complete

## Testing Requirements

### Test Infrastructure Setup
- [ ] Install test framework (pytest, pytest-asyncio, pytest-cov)
- [ ] Set up test directory structure (`tests/unit`, `tests/integration`, `tests/performance`)
- [ ] Create test fixtures and mock data
- [ ] Configure test coverage reporting
- [ ] Set up CI/CD test pipeline

### Unit Tests - Implemented Endpoints
- [ ] **UT-001: Health Check Tests** (`GET /`)
  - [ ] Test with R available
  - [ ] Test with R unavailable
  - [ ] Test data files availability
  - [ ] Performance baseline test
- [ ] **UT-002: Calibration Tests** (`POST /calibrate`)
  - [ ] Test with example data
  - [ ] Test with custom specific causes
  - [ ] Test with binary matrix
  - [ ] Test with death counts
  - [ ] Test validation errors
  - [ ] Test R script errors
  - [ ] Test timeout scenarios
- [ ] **UT-003: Example Data Tests** (`GET /example-data`)
  - [ ] Test data structure response
  - [ ] Test format specification
  - [ ] Test sample counts

### Unit Tests - Unimplemented Endpoints
- [ ] **UT-004: Datasets Tests** (`GET /datasets`)
- [ ] **UT-005: Dataset Preview Tests** (`GET /datasets/{id}/preview`)
- [ ] **UT-006: Convert Causes Tests** (`POST /convert/causes`)
- [ ] **UT-007: Validate Data Tests** (`POST /validate`)
- [ ] **UT-008: Cause Mappings Tests** (`GET /cause-mappings/{age_group}`)
- [ ] **UT-009: Supported Configurations Tests** (`GET /supported-configurations`)
- [ ] **UT-010: Job Status Tests** (`GET /calibrate/{job_id}/status`)
- [ ] **UT-011: WebSocket Tests** (`WS /calibrate/{job_id}/logs`)

### Integration Tests
- [ ] **IT-001: End-to-End Workflows**
  - [ ] Complete sync calibration workflow
  - [ ] Complete async calibration workflow
  - [ ] Multi-step validation → conversion → calibration
  - [ ] Ensemble calibration workflow
- [ ] **IT-002: Error Recovery**
  - [ ] R script failure recovery
  - [ ] Timeout and retry mechanisms
  - [ ] Partial data handling
- [ ] **IT-003: Data Format Compatibility**
  - [ ] All format conversions
  - [ ] Mixed format ensemble

### Performance Tests
- [ ] **PT-001: Load Testing**
  - [ ] Response time benchmarks (small/medium/large datasets)
  - [ ] Concurrent user testing (100+ users)
  - [ ] Requests per second baseline
  - [ ] Memory usage profiling
- [ ] **PT-002: Stress Testing**
  - [ ] 500 concurrent calibrations
  - [ ] Large dataset processing (10K+ deaths)
  - [ ] Memory leak detection
  - [ ] R process cleanup verification

### Security Tests
- [ ] **ST-001: Input Validation Security**
  - [ ] SQL injection prevention
  - [ ] Command injection prevention
  - [ ] Path traversal prevention
  - [ ] JSON bomb protection
- [ ] **ST-003: Data Privacy**
  - [ ] No PII in logs
  - [ ] Temp file cleanup
  - [ ] Error message sanitization

### Test Automation
- [ ] Create pytest fixtures for common test data
- [ ] Implement mock R service for testing
- [ ] Set up automated test execution in CI
- [ ] Configure code coverage thresholds (≥80%)
- [ ] Create smoke test suite for deployment validation
- [ ] Set up performance test automation with Locust

### Test Documentation
- [ ] Document test execution procedures
- [ ] Create test data preparation guide
- [ ] Write test troubleshooting guide
- [ ] Maintain test case traceability matrix

## Documentation Requirements

### Completed
- [x] API design document
- [x] Basic README with setup instructions
- [x] How to generate OpenVA output guide

### To Be Completed
- [ ] OpenAPI/Swagger specification
- [ ] Interactive API explorer (Swagger UI)
- [ ] Code examples in multiple languages (Python, R, JavaScript)
- [ ] User guides:
  - [ ] Getting started tutorial
  - [ ] OpenVA integration guide
  - [ ] Data preparation guidelines
  - [ ] Interpretation of results
- [ ] Developer documentation:
  - [ ] Architecture overview
  - [ ] Contributing guide
  - [ ] API client SDKs

## Implementation Priorities

### Immediate (Sprint 1)
1. **Complete core API endpoints** - Implement remaining GET endpoints
2. **Add async support** - Basic job queue for long-running calibrations
3. **Enhance error handling** - Better error messages and validation

### Short-term (Sprint 2-3)
1. **Add authentication** - Basic API key authentication
2. **Implement caching** - Cache results for common requests
3. **Add monitoring** - Basic logging and metrics
4. **Write tests** - Core unit and integration tests

### Medium-term (Sprint 4-6)
1. **Production deployment** - Docker Compose and basic K8s setup
2. **Performance optimization** - Connection pooling, caching
3. **Complete documentation** - OpenAPI spec and user guides
4. **Frontend enhancements** - Full integration with all endpoints

### Long-term
1. **Advanced features** - GraphQL, webhooks, custom matrices
2. **Scalability** - Horizontal scaling, distributed processing
3. **Multi-region support** - CDN and geo-distributed deployment
4. **Enterprise features** - SSO, audit logs, compliance

## Technical Debt

### Current Issues
- No test coverage
- Limited error handling in R scripts
- No database for job persistence
- Synchronous processing only
- No request validation middleware
- Missing OpenAPI documentation
- No CI/CD pipeline

### Refactoring Needs
- Separate business logic from API routes
- Create service layer for R interaction
- Implement dependency injection
- Add configuration management
- Standardize error responses

## Success Metrics

### API Performance
- Response time < 2s for small datasets
- Support 100+ concurrent users
- 99.9% uptime SLA
- < 1% error rate

### User Experience
- Complete calibration in < 30s for typical datasets
- Real-time progress feedback
- Clear error messages
- Comprehensive documentation

### Development
- 80%+ test coverage
- Automated deployment pipeline
- < 1 day from commit to production
- Active monitoring and alerting

## Next Steps

1. **Review and prioritize** this roadmap with stakeholders
2. **Set up project board** with GitHub Issues/Projects
3. **Define sprint goals** for next 2-3 sprints
4. **Recruit contributors** if needed for parallel development
5. **Establish CI/CD pipeline** for automated testing and deployment

---

*Last Updated: 2024-01-18*
*Status: Planning Phase*
*Version: 1.0.0*