# ESIG'Guard — Independent Data Scoring & ML Pipeline

This pipeline represents the **independent DATA analysis flow** for phishing detection.
It does NOT rely on the cyber team's scoring logic.

## Principle
- Read fully processed emails (status='done')
- Build features from email headers, URLs and attachments
- Compute:
    - score_data (rule-based, explainable)
    - proba_data (machine learning)
- Write results back to Azure MySQL

## Automation
This script can run continuously and automatically process new emails.

## Run
```bash
python service.py
```