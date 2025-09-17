# Try to read default project from gcloud if not provided
PROJECT_ID ?= $(shell gcloud config get-value project 2>/dev/null)
REGION ?= us-central1
STAGING_BUCKET ?= dataflow-staging-$(PROJECT_ID)
TEMPLATE_SPEC ?= gs://$(STAGING_BUCKET)/flex_templates/dividends_spec.json
IMAGE ?= us-central1-docker.pkg.dev/$(PROJECT_ID)/artreg/dividends-beam:latest

.PHONY: help doctor build-pipeline push-pipeline publish-template pack-function tf-init tf-plan tf-apply upload-sample

help:
	@echo "Make targets:"
	@echo "  doctor              - Check required tools and config"
	@echo "  build-pipeline      - Docker build Beam image"
	@echo "  push-pipeline       - Docker push Beam image"
	@echo "  publish-template    - Upload Flex Template spec to GCS"
	@echo "  pack-function       - Zip function and upload to staging bucket"
	@echo "  tf-init/plan/apply  - Terraform lifecycle"
	@echo "  upload-sample       - Put sample CSV in raw bucket"

# Quick environment check
DOCKER ?= $(shell command -v docker 2>/dev/null)
GCLOUD ?= $(shell command -v gcloud 2>/dev/null)
GSUTIL ?= $(shell command -v gsutil 2>/dev/null)

doctor:
	@if [ -z "$(DOCKER)" ]; then echo "[X] docker not found"; exit 1; else echo "[✓] docker: $(DOCKER)"; fi
	@if ! docker info >/dev/null 2>&1; then echo "[X] Docker daemon not running or permission denied"; exit 1; else echo "[✓] Docker daemon running"; fi
	@if [ -z "$(GCLOUD)" ]; then echo "[X] gcloud not found"; exit 1; else echo "[✓] gcloud: $(GCLOUD)"; fi
	@if [ -z "$(PROJECT_ID)" ]; then echo "[X] PROJECT_ID not set (run 'gcloud config set project <id>' or pass PROJECT_ID=)"; exit 1; else echo "[✓] PROJECT_ID=$(PROJECT_ID)"; fi
	@echo "[i] Using IMAGE=$(IMAGE)"

build-pipeline: doctor
	cd dataflow && docker build -t $(IMAGE) .

push-pipeline: doctor
	docker push $(IMAGE)

publish-template: doctor
	gsutil cp dataflow/flex_template_spec.json /tmp/flex_spec.json
	python3 -c "import json,os; p='/tmp/flex_spec.json'; \
spec=json.load(open(p)); spec['image']=os.environ.get('IMAGE'); \
open(p,'w').write(json.dumps(spec))"
	gsutil cp /tmp/flex_spec.json $(TEMPLATE_SPEC)

pack-function: doctor
	cd function_launcher && zip -r /tmp/function_launcher_src.zip .
	gsutil cp /tmp/function_launcher_src.zip gs://$(STAGING_BUCKET)/function_launcher_src.zip

tf-init:
	cd terraform && terraform init

tf-plan:
	cd terraform && terraform plan

tf-apply:
	cd terraform && terraform apply -auto-approve

upload-sample: doctor
	gsutil cp samples/sample_dividends.csv gs://dividends-raw-$(PROJECT_ID)/
