#!/usr/bin/env python3
"""Patch Pinto plugin manifest so Hermes config/dashboard can edit settings."""
from pathlib import Path

p = Path('/opt/hermes-pinto-plugin/plugin.yaml')
if not p.exists():
    raise SystemExit(f'{p} not found')

p.write_text('''name: pinto-platform
label: Pinto Chat
kind: platform
version: 1.2.0
description: >
  Pinto Chat gateway adapter for Hermes Agent.
  Receives Pinto webhooks, sends replies, generating status, and media uploads.
author: Theeraphat S

requires_env:
  - name: PINTO_BOT_ID
    description: "Bot ID from Pinto Developer Console"
    prompt: "Pinto Bot ID"
    password: false

optional_env:
  - name: PINTO_API_URL
    description: "Pinto API URL. Dev: https://api-dev.pinto-app.com, Prod: https://api.pinto-app.com"
    prompt: "Pinto API URL"
    password: false
  - name: PINTO_WEBHOOK_URL
    description: "Copy this URL into Pinto Developer Console > Bot Webhook URL"
    prompt: "Developer Console Webhook URL"
    password: false
  - name: PINTO_WEBHOOK_SECRET
    description: "Copy this secret into Pinto Developer Console. Generated automatically if blank."
    prompt: "Developer Console Webhook Secret"
    password: false
''', encoding='utf-8')
print('Patched Pinto plugin.yaml config metadata')
