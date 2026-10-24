# Mingo System Architecture

## Overview

```mermaid
flowchart LR
    learner["Learner's browser<br/>React + TypeScript<br/>Microphone and audio playback"]
    cognito["Amazon Cognito<br/>OIDC sign-in and JWT issuance"]

    subgraph aws["AWS production environment"]
        ingress["ECS Express Mode<br/>HTTPS / WebSocket"]
        app["ECS task (1 task)<br/>Docker container<br/><br/>FastAPI<br/>REST API and WebSocket<br/>JWT verification and daily usage limits<br/>React static file hosting"]
        sqlite[("SQLite memo.db<br/>Memos, mastery records, and usage counts")]
        efs["Amazon EFS<br/>Persistent volume"]
        secrets["AWS Secrets Manager<br/>External API keys"]
        ecr["Amazon ECR<br/>Docker image"]
        actions["GitHub Actions<br/>Test, build, and deploy"]
    end

    gemini_live["Google Gemini Live API<br/>Voice conversation and transcription"]
    gemini["Google Gemini API<br/>Grammar, memo categorization, and hints"]
    openai["OpenAI API<br/>Embeddings and text-to-speech"]
    azure["Azure AI Speech<br/>Pronunciation assessment"]

    learner <-->|"Sign-in and obtain JWT"| cognito
    learner -->|"HTTPS: REST + JWT"| ingress
    learner <-->|"WSS: audio and conversation events"| ingress
    ingress --> app
    app <-->|"Read and write"| sqlite
    sqlite ---|"EFS mount<br/>/mnt/mingo-data"| efs
    secrets -.->|"Injected as environment variables"| app

    app <-->|"Audio streaming"| gemini_live
    app <-->|"Text generation"| gemini
    app <-->|"Embeddings and TTS"| openai
    app <-->|"Pronunciation assessment"| azure

    actions -->|"Push after AWS OIDC authentication"| ecr
    actions -->|"Update service"| ingress
    ecr -->|"Pull image"| app

    subgraph local["Local development only (optional)"]
        local_app["Locally running FastAPI"]
        files["Files on the developer's machine"]
        claude["Claude Agent SDK<br/>Read-only code analysis"]
    end
    app -->|"Verify JWT using Cognito JWKS"| cognito
    local_app -.->|"ENABLE_CODE_ANALYSIS=true"| claude
    claude -->|"Read / Grep / Glob"| files
```

## Main request flows

1. The browser signs in with Cognito and obtains a JWT. FastAPI verifies the token in the `Authorization` header for REST API requests and in the connection query string for the conversation WebSocket.
2. The React app is served from the same ECS Express Mode URL. API requests use HTTPS, while voice conversations connect to FastAPI over WebSocket.
3. FastAPI relays conversation audio to the Gemini Live API and calls the AI APIs for tasks such as grammar checks and hint generation. Azure AI Speech is used for pronunciation assessment.
4. Memos, learning progress, and API usage counts are stored in SQLite. In production, the SQLite file resides on EFS and the service is limited to one task.
5. GitHub Actions runs the backend tests, builds and pushes a Docker image to ECR, and updates the ECS Express Mode service.

## Notes

- The ECS task mounts EFS at `/mnt/mingo-data` and sets `MEMO_DB_PATH=/mnt/mingo-data/memo.db`.
- External API keys are managed in Secrets Manager and passed to the application as task environment variables.
- Code analysis is an optional local-development feature. When `ENABLE_CODE_ANALYSIS=true`, the Claude Agent SDK reads project files on the developer's machine. It is not part of the normal production request flow.
