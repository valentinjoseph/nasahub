#!/usr/bin/env bash
set -euo pipefail

cd /home/hl-lenovo/projects/nasahub
/usr/bin/docker compose -f infra/docker-compose.yml run --rm ingestor python -m ingestors.eonet.categories >> logs/eonet_categories.log 2>&1