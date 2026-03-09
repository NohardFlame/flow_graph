# Module: Deployment and Cloud MVP

## Goal

Package the MVP into a small, understandable cloud deployment that can process several documents concurrently without overspending or overengineering.

## Recommended topology

### Minimum production-like topology
- API container
- worker container
- PostgreSQL
- Redis
- S3-compatible object storage
- optional LiteLLM Proxy
- optional Qdrant disabled by default

## Deployment stance

Prefer one deployable application repo with two process roles:
- `api`
- `worker`

Do not split into many microservices at MVP stage.

## Containerization

Provide:
- one shared base image or build strategy,
- separate entrypoints for API and worker,
- environment-driven config,
- health checks.

## Environment tiers

- `local`
- `test`
- `staging`
- `prod`

Keep feature flags explicit across tiers.

## Startup order expectations

1. DB available
2. Redis available
3. object storage available
4. API and worker start
5. optional LiteLLM proxy if used
6. optional vector index

Use startup validation for config, not deep warming of every dependency.

## Operational policies

### Scaling
- scale workers horizontally before scaling API aggressively
- API is mostly coordination
- worker capacity determines throughput

### Cost control
- keep prefilter enabled in all non-debug environments
- enable LLM caching
- keep raw LLM artifact retention limited
- monitor average accepted chunks per document

### Security baseline
- secrets from environment/secret store
- least-privilege access to buckets and DB
- private network placement where possible
- no public raw artifact buckets

## CI/CD expectations

Pipeline should run:
1. lint/format
2. unit tests
3. integration tests
4. migration smoke tests
5. build image
6. deploy

## Acceptance criteria

- one command or pipeline deploys both API and worker roles,
- rollback is straightforward,
- worker and API share the same domain code,
- environment variables fully configure deployment,
- optional services can stay disabled safely.

## Common pitfalls

- introducing Kubernetes complexity too early,
- coupling deploy config to developer machines,
- no separation between API and worker process roles,
- treating Qdrant as required before semantic search proves its value.
