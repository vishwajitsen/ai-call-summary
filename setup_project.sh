#!/bin/bash

# Project root folder
PROJECT_NAME="ai-call-summary"

# Create directory structure
mkdir -p $PROJECT_NAME/{config,scripts,app/{nlu,models,integrations,ui_auth,utils},tests/sample_audio,docs}

# Create files
touch $PROJECT_NAME/README.md
touch $PROJECT_NAME/requirements.txt
touch $PROJECT_NAME/.env.example
touch $PROJECT_NAME/config/config.yml
touch $PROJECT_NAME/scripts/{run_pipeline.py,evaluate_all_models.py}
touch $PROJECT_NAME/app/__init__.py
touch $PROJECT_NAME/app/{ingestion.py,speech_transcribe.py,diarization.py,storage.py,orchestrator.py}
touch $PROJECT_NAME/app/nlu/{__init__.py,summarizer.py,extractor.py,sentiment.py}
touch $PROJECT_NAME/app/models/{model_registry.py,offline_models.py}
touch $PROJECT_NAME/app/integrations/{fhir_connector.py,servicenow_connector.py,salesforce_connector.py}
touch $PROJECT_NAME/app/ui_auth/ad_integration.py
touch $PROJECT_NAME/app/utils/{metrics.py,audio_utils.py,logger.py}
touch $PROJECT_NAME/tests/sample_audio/sample_call.wav
touch $PROJECT_NAME/docs/{architecture_diagram.png,runbook.md}

echo "✅ Project structure '$PROJECT_NAME' created successfully!"
