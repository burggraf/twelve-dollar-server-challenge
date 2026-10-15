#!/usr/bin/env bash
# Owner-authorized resumed cohort; original one-attempt history is preserved.
# One earlier scored probe + at most eleven further scored attempts = twelve total.
set -euo pipefail
cd /opt/twelve-dollar-baas-pocketbase-16g/src
bash services/pocketbase/run.sh search --max-vus 20000 --max-attempts 11 2>&1 | tee results/pocketbase/vps16-linux-amd64/setup-evidence/capacity-campaign-resumed-20261015T1521Z.log
