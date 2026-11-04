# Agentic Software Engineering Interview Prototype

## Important scope note
This is a **working deterministic multi-agent workflow prototype**, not a fully autonomous LLM coding system. It includes six role-based agents, a dependency-aware orchestrator, automated test execution, risk review, and explicit approval. The Code Agent verifies a prebuilt template rather than synthesizing arbitrary code. Brownfield classification is implemented, but repository impact analysis is not. State these limitations in the interview.

## Setup (Windows PowerShell)
```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python agents.py
python agents.py --approve
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs for interactive Swagger API.

## Demo API
POST `/api/links` with `{"url":"https://example.com"}` -> `201` with short code and short URL.
GET `/{code}` -> HTTP 307 redirect; records one click.
GET `/api/links/{code}/analytics` -> aggregate click count.

## Agent workflow
1. Requirement Agent: normalize and flag ambiguities.
2. Planning Agent: create dependent engineering tasks.
3. Architecture Agent: specify components and API endpoints.
4. Code Agent: verify prebuilt engineering files.
5. Test Agent: run pytest subprocess and capture results.
6. Review Agent: assess tests, artifacts, risks, and limitations.
7. Orchestrator: topologically schedule ready tasks, block review on failing tests, log execution.
8. Human gate: `--approve` records explicit approval; default pending.

## Three scenarios
```powershell
python agents.py "Build a scalable URL shortener service with APIs, persistence, and analytics"
python agents.py "Enhance an existing URL shortener with click analytics"
python agents.py "Make links fast"
```
The scenario input changes requirement classification and ambiguities; the implementation template remains the same. This is an intentional limitation, not dynamic greenfield/brownfield generation.

## Tests
`python -m pytest -q tests`

## Jenkins deployment to Kubernetes Dev
The root `Jenkinsfile` runs tests for every build. Builds of `main` also build and
push an image tagged with the commit SHA, then apply `k8s/dev.yaml` and wait for
the Dev Deployment rollout. The Kubernetes Service is internal to the cluster;
configure an Ingress or your platform's Dev routing if external access is needed.

The Jenkins agent needs Python 3, Docker access, `kubectl`, and a configured
multibranch pipeline that checks out this repository. Set the pipeline parameters:

- `IMAGE_REPOSITORY`: writable registry/repository, such as
  `registry.example.com/team/url-shortener`.
- `REGISTRY_CREDENTIAL_ID`: Jenkins username/password credential for pushing images.
- `KUBECONFIG_CREDENTIAL_ID`: Jenkins secret-file credential whose kubeconfig can
  create/update resources in the `dev` namespace.

The Kubernetes cluster also needs a default StorageClass capable of provisioning
the 1 GiB SQLite data volume. For a private registry, configure an image-pull
secret for the `dev` namespace (or otherwise grant the cluster access to pull the
image). The manifest sets `BASE_URL` to the in-cluster Service address; change it
to the Dev URL when adding external routing.

## Architecture and production tradeoffs
Client -> FastAPI -> SQLite tables (links, clicks). Random URL-safe tokens with unique database key and collision retries. Use PostgreSQL, Redis cache, asynchronous event queue, distributed rate limits, abuse screening, authorization, and monitoring for a production deployment. Add migrations, concurrency/load tests, observability, and retention policy before production.

## Interview questions
- What distinguishes an agent from a function? Agent roles have defined inputs/outputs; these are deterministic and not LLM autonomous.
- Why orchestrate? Enforce dependencies, gates, retries, failure propagation, and traceability.
- Why SQLite? Zero-setup demo, not scalable distributed storage.
- How do you avoid unsafe generated code? Sandboxed execution, allowlists, approvals, test gates; not yet implemented here.
- How would brownfield reasoning work? Repository indexing, dependency analysis, diff generation, test selection, reviewer approval.
- How would you improve resilience? Retry transient tool errors, checkpoints, idempotency keys, timeout budgets, rollback.
- How to scale analytics? Event queue and async aggregation; eventual consistency.
