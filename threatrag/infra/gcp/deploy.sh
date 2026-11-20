#!/usr/bin/env bash
# Deploy ThreatRAG to Cloud Run: billed per request, nothing running (or billed) while idle.
#
#   bash threatrag/infra/gcp/deploy.sh            # setup (idempotent) + build + deploy
#   SKIP_BUILD=1 bash threatrag/infra/gcp/deploy.sh   # redeploy the last images (e.g. new secrets)
#
# Reads GCP_PROJECT_ID / GCP_REGION from threatrag/backend/.env.cloud. That whole file becomes ONE
# Secret Manager secret mounted at /secrets/threatrag.env (one secret stays inside the free tier).
# Idle-cost rules: min instances 0, CPU only during requests, max 2 instances, no Cloud SQL/VMs.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
ENV_FILE="$ROOT/threatrag/backend/.env.cloud"
val() { grep -E "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"'"'"; }

PROJECT="$(val GCP_PROJECT_ID)"; REGION="$(val GCP_REGION)"; REGION="${REGION:-europe-west1}"
[ -n "$PROJECT" ] || { echo "GCP_PROJECT_ID is empty in $ENV_FILE"; exit 1; }
REPO="$REGION-docker.pkg.dev/$PROJECT/threatrag"
TAG="$(git -C "$ROOT" rev-parse --short HEAD)$(git -C "$ROOT" diff --quiet HEAD -- threatrag || echo -dirty)"
SA="threatrag-run@$PROJECT.iam.gserviceaccount.com"
G="gcloud --project=$PROJECT --quiet"
step() { printf '\n== %s\n' "$*"; }

step "APIs"
$G services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com \
  secretmanager.googleapis.com cloudscheduler.googleapis.com

step "Image registry (keeps the newest 2 images per name)"
$G artifacts repositories describe threatrag --location="$REGION" >/dev/null 2>&1 || \
  $G artifacts repositories create threatrag --repository-format=docker --location="$REGION" 2>&1 \
  | grep -v ALREADY_EXISTS || true  # describe can fail briefly right after the API is enabled
POLICY="$(mktemp)"; cat > "$POLICY" <<'JSON'
[{"name":"keep-2","action":{"type":"Keep"},"mostRecentVersions":{"keepCount":2}},
 {"name":"delete-rest","action":{"type":"Delete"},"condition":{"tagState":"any"}}]
JSON
$G artifacts repositories set-cleanup-policies threatrag --location="$REGION" --policy="$POLICY" --no-dry-run >/dev/null
rm -f "$POLICY"

step "Runtime service account (reads its two secrets, nothing else)"
$G iam service-accounts describe "$SA" >/dev/null 2>&1 || \
  $G iam service-accounts create threatrag-run --display-name="ThreatRAG Cloud Run"

put_secret() {  # name, file: add a version only when the content changed; destroy older versions
  local name="$1" file="$2" latest
  $G secrets describe "$name" >/dev/null 2>&1 || $G secrets create "$name" --replication-policy=automatic
  latest="$($G secrets versions access latest --secret="$name" 2>/dev/null || true)"
  if [ "$latest" != "$(cat "$file")" ]; then
    $G secrets versions add "$name" --data-file="$file" >/dev/null
    for v in $($G secrets versions list "$name" --filter="state=ENABLED" --sort-by=~createTime --format="value(name)" | tail -n +2); do
      $G secrets versions destroy "$v" --secret="$name" >/dev/null
    done
    echo "$name: new version"
  else echo "$name: unchanged"; fi
  $G secrets add-iam-policy-binding "$name" --member="serviceAccount:$SA" \
    --role=roles/secretmanager.secretAccessor >/dev/null
}
step "Build permissions (new projects build as the default compute account, which starts with none)"
NUM="$($G projects describe "$PROJECT" --format='value(projectNumber)')"
$G projects add-iam-policy-binding "$PROJECT" --condition=None --role=roles/cloudbuild.builds.builder \
  --member="serviceAccount:$NUM-compute@developer.gserviceaccount.com" >/dev/null

step "Secrets"
ENV_SECRET="$(mktemp)"; KEY_SECRET="$(mktemp)"; trap 'rm -f "$ENV_SECRET" "$KEY_SECRET"' EXIT
# Drop comments, deploy-only GCP_ lines and blank values (blank = default; an empty list fails to parse)
grep -vE '^(GCP_|#|$)|^[A-Z0-9_]+=[[:space:]]*$' "$ENV_FILE" > "$ENV_SECRET"
printf '%s' "$(val API_KEY)" > "$KEY_SECRET"
put_secret threatrag-env "$ENV_SECRET"
put_secret threatrag-api-key "$KEY_SECRET"

if [ -z "${SKIP_BUILD:-}" ]; then
  step "Build images on Cloud Build (amd64), tag $TAG"
  $G builds submit "$ROOT/threatrag/backend" --region="$REGION" --tag="$REPO/backend:$TAG"
  $G builds submit "$ROOT/threatrag/web" --region="$REGION" --tag="$REPO/web:$TAG"
else
  TAG="$($G artifacts docker tags list "$REPO/backend" --sort-by=~UPDATE_TIME --limit=1 --format='value(tag)')"
fi

COMMON=(--region="$REGION" --service-account="$SA" --min-instances=0 --max-instances=2 --cpu-throttling)
step "Deploy API"
$G run deploy threatrag-api "${COMMON[@]}" --image="$REPO/backend:$TAG" --allow-unauthenticated \
  --cpu=1 --memory=1Gi --concurrency=20 --timeout=900 --port=8080 \
  --set-secrets=/secrets/threatrag.env=threatrag-env:latest \
  --set-env-vars=FORWARDED_ALLOW_IPS=*
API_URL="$($G run services describe threatrag-api --region="$REGION" --format='value(status.url)')"

step "Deploy web"
$G run deploy threatrag-web "${COMMON[@]}" --image="$REPO/web:$TAG" --allow-unauthenticated \
  --cpu=1 --memory=256Mi --concurrency=80 --timeout=900 --port=80 \
  --set-env-vars=BACKEND_URL="$API_URL" --set-secrets=API_KEY=threatrag-api-key:latest
WEB_URL="$($G run services describe threatrag-web --region="$REGION" --format='value(status.url)')"
# Report links point at the site; the env var wins over the secret file
$G run services update threatrag-api --region="$REGION" \
  --update-env-vars="^@^PUBLIC_BASE_URL=$WEB_URL@CORS_ORIGINS=[\"$WEB_URL\"]" >/dev/null  # @ = separator

step "Daily feed refresh: a Cloud Run job, billed only while it runs"
JOB_ARGS=(--region="$REGION" --image="$REPO/backend:$TAG" --service-account="$SA" --cpu=1 --memory=1Gi
  --task-timeout=3600 --max-retries=0 --set-secrets=/secrets/threatrag.env=threatrag-env:latest
  --command=python --args=-m,app.scripts.refresh_feeds)
$G run jobs describe threatrag-feeds --region="$REGION" >/dev/null 2>&1 \
  && $G run jobs update threatrag-feeds "${JOB_ARGS[@]}" >/dev/null \
  || $G run jobs create threatrag-feeds "${JOB_ARGS[@]}" >/dev/null
$G run jobs add-iam-policy-binding threatrag-feeds --region="$REGION" --member="serviceAccount:$SA" \
  --role=roles/run.invoker >/dev/null
RUN_URI="https://run.googleapis.com/v2/projects/$PROJECT/locations/$REGION/jobs/threatrag-feeds:run"
$G scheduler jobs describe threatrag-feeds-daily --location="$REGION" >/dev/null 2>&1 || \
  $G scheduler jobs create http threatrag-feeds-daily --location="$REGION" --schedule="30 3 * * *" \
    --time-zone=UTC --http-method=POST --uri="$RUN_URI" --oauth-service-account-email="$SA"

step "Done"
echo "Site: $WEB_URL"
echo "API:  $API_URL  (direct calls need X-API-Key; the site adds it server side)"
