#!/usr/bin/env python3
"""Watchdog cleanup of exact-owned runner/reset-tool names ONLY; never servers."""
import json,os,subprocess
from pathlib import Path
os.environ['DOCKER_CONFIG']='/opt/twelve-dollar-baas-benchmark-16g/.docker'
p=Path('/opt/twelve-dollar-baas-convexpg-16g');assert json.loads((p/'.benchmark-owned').read_text())['project']=='baas-convexpg-vps16'
for name,role in [('baas-convexpg-vps16-load','k6'),('baas-convexpg-vps16-reset-tools','tools')]:
 probe=subprocess.run(['docker','inspect',name],capture_output=True,text=True)
 if probe.returncode:continue
 item=json.loads(probe.stdout)[0];labels=item['Config']['Labels']
 assert item['Name']=='/'+name and labels.get('com.docker.compose.project')=='baas-convexpg-vps16' and labels.get('com.docker.compose.service')==role
 subprocess.run(['docker','rm','--force',item['Id']],check=True,capture_output=True)
print('ONLY_EXACT_OWNED_RUNNER_RESET_TOOLS_CLEANED_NEVER_SERVING_RESTART_OR_REVIVAL',flush=True)
