# CareerAssist - AWS Architecture Diagram

## High-Level System Architecture

```mermaid
flowchart TB
    subgraph User["👤 User Layer"]
        Browser[Browser/Client]
    end

    subgraph Frontend["🖥️ Frontend Layer (Part 7)"]
        CF[CloudFront CDN]
        S3FE[S3 Static Website<br/>Next.js App]
        APIGW[API Gateway HTTP API]
    end

    subgraph API["🔌 Backend API"]
        APILambda[Lambda: career-api<br/>FastAPI + Mangum]
        Clerk[Clerk Auth<br/>JWT Validation]
    end

    subgraph Queue["📬 Message Queue (Part 6)"]
        SQS[SQS Queue<br/>career-analysis-jobs]
        DLQ[Dead Letter Queue<br/>career-analysis-jobs-dlq]
    end

    subgraph Agents["🤖 AI Agents Layer (Part 6)"]
        Orch[Lambda: career-orchestrator<br/>Request Router]
        Ext[Lambda: career-extractor<br/>CV & Job Parser]
        Ana[Lambda: career-analyzer<br/>Gap Analysis + Rewrites]
        Cha[Lambda: career-charter<br/>Application Analytics]
        Int[Lambda: career-interviewer<br/>Interview Prep]
    end

    subgraph Research["🔬 Research Layer (Part 4)"]
        AppRunner[App Runner Service<br/>career-researcher<br/>FastAPI + MCP]
        EventBridge[EventBridge Scheduler<br/>Every 2 hours]
    end

    subgraph AI["🧠 AI Services"]
        Bedrock[Amazon Bedrock<br/>Nova Pro LLM]
        SageMaker[SageMaker Endpoint<br/>career-embedding<br/>HuggingFace Embeddings]
    end

    subgraph Storage["💾 Data Layer"]
        Aurora[(Aurora Serverless v2<br/>PostgreSQL 15<br/>career database)]
        S3Vec[S3 Vectors Bucket<br/>career-vectors<br/>RAG Knowledge Base]
        Secrets[Secrets Manager<br/>DB Credentials]
    end

    subgraph Ingestion["📥 Ingestion Layer (Part 3)"]
        IngestAPI[API Gateway REST<br/>career-api /ingest]
        IngestLambda[Lambda: career-ingest<br/>Document Ingestion]
    end

    subgraph Monitoring["📊 Observability (Part 8)"]
        CWDash[CloudWatch Dashboards<br/>AI Model Usage<br/>Agent Performance]
        CWLogs[CloudWatch Logs<br/>7-day retention]
    end

    %% User Flow
    Browser --> CF
    CF --> S3FE
    CF -->|/api/*| APIGW
    APIGW --> APILambda
    APILambda --> Clerk

    %% API to Queue
    APILambda -->|Create Job| Aurora
    APILambda -->|Send Message| SQS
    SQS -->|Trigger| Orch
    SQS -.->|Failed msgs| DLQ

    %% Orchestrator to Agents
    Orch -->|Lambda Invoke| Ext
    Orch -->|Lambda Invoke| Ana
    Orch -->|Lambda Invoke| Cha
    Orch -->|Lambda Invoke| Int

    %% All Agents to Services
    Orch & Ext & Ana & Cha & Int -->|LLM Inference| Bedrock
    Orch & Ext & Ana & Cha & Int -->|Data API| Aurora
    Ana & Int -->|Vector Search| S3Vec
    Ana & Int -->|Get Embeddings| SageMaker

    %% Research Flow
    EventBridge -.->|Trigger| AppRunner
    AppRunner -->|Bedrock| Bedrock
    AppRunner -->|Ingest API| IngestAPI

    %% Ingestion Flow
    IngestAPI --> IngestLambda
    IngestLambda --> SageMaker
    IngestLambda --> S3Vec

    %% Monitoring
    Orch & Ext & Ana & Cha & Int --> CWLogs
    Bedrock & SageMaker --> CWDash

    %% Database Access
    Aurora --> Secrets
```

---

## Agent Communication Flow

```mermaid
sequenceDiagram
    autonumber
    participant U as 👤 User
    participant FE as 🖥️ Frontend
    participant API as 🔌 FastAPI
    participant SQS as 📬 SQS Queue
    participant O as 🎯 Orchestrator
    participant E as 📄 Extractor
    participant A as 📊 Analyzer
    participant I as 🎤 Interviewer
    participant C as 📈 Charter
    participant DB as 💾 Aurora DB
    participant AI as 🧠 Bedrock

    U->>FE: Upload CV + Job Posting
    FE->>API: POST /api/analyze
    API->>DB: Create job (status: pending)
    API->>SQS: Send job message
    API-->>FE: Return job_id
    
    SQS->>O: Trigger (batch_size=1)
    O->>DB: Update job (status: processing)
    
    rect rgb(230, 245, 255)
        Note over O,E: CV Extraction
        O->>E: invoke_extractor("cv", cv_text)
        E->>AI: Parse CV (Structured Output)
        AI-->>E: CVProfile JSON
        E->>DB: Store cv_versions
        E-->>O: CVProfile
    end

    rect rgb(230, 245, 255)
        Note over O,E: Job Extraction
        O->>E: invoke_extractor("job", job_text)
        E->>AI: Parse Job (Structured Output)
        AI-->>E: JobProfile JSON
        E->>DB: Store job_postings
        E-->>O: JobProfile
    end

    rect rgb(255, 245, 230)
        Note over O,A: Gap Analysis & CV Rewrite
        O->>A: invoke_analyzer("full_analysis")
        A->>AI: Analyze gaps + Rewrite CV
        A->>DB: Store gap_analyses
        A->>DB: Store cv_rewrites
        A-->>O: GapAnalysis + CVRewrite
    end

    rect rgb(245, 255, 230)
        Note over O,I: Interview Preparation
        O->>I: invoke_interviewer()
        I->>AI: Generate interview pack
        I->>DB: Store interview_sessions
        I-->>O: InterviewPack
    end

    O->>DB: Update job (status: completed, results)
    
    loop Poll for results
        FE->>API: GET /api/jobs/{job_id}
        API->>DB: Get job status
        API-->>FE: Job status + results
    end
    
    FE-->>U: Display Results
```

---

## AWS Infrastructure Topology

```mermaid
flowchart TB
    subgraph Internet["🌐 Internet"]
        User[User Browser]
    end

    subgraph AWS["☁️ AWS Account"]
        subgraph Edge["Edge Layer"]
            CloudFront[CloudFront Distribution<br/>HTTPS Termination<br/>SPA Routing]
        end

        subgraph Compute["Compute Layer"]
            subgraph Lambdas["Lambda Functions"]
                L1[career-api<br/>512MB / 30s]
                L2[career-orchestrator<br/>2GB / 15min]
                L3[career-extractor<br/>1GB / 5min]
                L4[career-analyzer<br/>1GB / 5min]
                L5[career-charter<br/>1GB / 5min]
                L6[career-interviewer<br/>1GB / 5min]
                L7[career-ingest<br/>512MB / 30s]
            end
            
            AppRunner[App Runner<br/>career-researcher<br/>1 vCPU / 2GB]
        end

        subgraph AI_Services["AI Services"]
            Bedrock[Bedrock<br/>Nova Pro v1.0<br/>Cross-region]
            SageMaker[SageMaker Serverless<br/>career-embedding<br/>3072MB / MaxConc 2]
        end

        subgraph Data["Data Layer"]
            subgraph VPC["VPC"]
                Aurora[(Aurora Serverless v2<br/>PostgreSQL 15.12<br/>0.5-1 ACU)]
                SG[Security Group<br/>Port 5432]
            end
            
            S3_FE[S3 Bucket<br/>career-frontend<br/>Static Hosting]
            S3_Vec[S3 Bucket<br/>career-vectors<br/>Vector Storage]
            S3_Pkg[S3 Bucket<br/>career-lambda-packages<br/>Deployment]
        end

        subgraph Messaging["Messaging"]
            SQS_Main[SQS Queue<br/>career-analysis-jobs<br/>Visibility 15min]
            SQS_DLQ[SQS DLQ<br/>career-analysis-jobs-dlq<br/>maxReceiveCount 3]
            EB[EventBridge<br/>Scheduler]
        end

        subgraph Security["Security & Config"]
            SM[Secrets Manager<br/>Aurora Credentials]
            IAM[IAM Roles<br/>career-*-role]
        end

        subgraph Gateway["API Layer"]
            APIGW_HTTP[API Gateway HTTP<br/>career-api-gateway<br/>CORS Enabled]
            APIGW_REST[API Gateway REST<br/>career-api<br/>API Key Auth]
        end

        subgraph Monitoring["Monitoring"]
            CW_Logs[CloudWatch Logs<br/>7-day retention]
            CW_Dash[CloudWatch Dashboards<br/>AI Model Usage<br/>Agent Performance]
        end
    end

    User --> CloudFront
    CloudFront --> S3_FE
    CloudFront --> APIGW_HTTP
    APIGW_HTTP --> L1
    APIGW_REST --> L7
    
    L1 --> SQS_Main
    SQS_Main --> L2
    SQS_Main -.-> SQS_DLQ
    
    L2 --> L3 & L4 & L5 & L6
    
    L1 & L2 & L3 & L4 & L5 & L6 --> Aurora
    L3 & L4 & L5 & L6 --> Bedrock
    L4 & L6 --> SageMaker
    L4 & L6 --> S3_Vec
    L7 --> SageMaker
    L7 --> S3_Vec
    
    Aurora --> SM
    Aurora --> SG
    
    EB -.-> AppRunner
    AppRunner --> Bedrock
    AppRunner --> APIGW_REST
    
    L1 & L2 & L3 & L4 & L5 & L6 & L7 --> CW_Logs
    Bedrock & SageMaker --> CW_Dash
```

---

## Database Schema (Simplified)

```mermaid
erDiagram
    user_profiles {
        uuid user_id PK
        string clerk_user_id UK
        string email
        string name
        timestamp created_at
    }
    
    cv_versions {
        uuid cv_id PK
        uuid user_id FK
        string version_name
        text raw_text
        jsonb structured_data
        boolean is_primary
        timestamp created_at
    }
    
    job_postings {
        uuid job_id PK
        uuid user_id FK
        text raw_text
        jsonb structured_data
        string company
        string role_title
        timestamp created_at
    }
    
    gap_analyses {
        uuid analysis_id PK
        uuid user_id FK
        uuid cv_id FK
        uuid job_id FK
        integer fit_score
        integer ats_score
        jsonb analysis_data
        timestamp created_at
    }
    
    cv_rewrites {
        uuid rewrite_id PK
        uuid analysis_id FK
        text rewritten_summary
        jsonb rewritten_bullets
        text cover_letter
        timestamp created_at
    }
    
    interview_sessions {
        uuid session_id PK
        uuid user_id FK
        uuid job_id FK
        jsonb questions
        string session_type
        timestamp created_at
    }
    
    jobs {
        uuid job_id PK
        uuid user_id FK
        string job_type
        string status
        jsonb input_data
        jsonb result
        timestamp created_at
    }

    user_profiles ||--o{ cv_versions : "has"
    user_profiles ||--o{ job_postings : "saved"
    user_profiles ||--o{ gap_analyses : "generated"
    user_profiles ||--o{ interview_sessions : "practiced"
    user_profiles ||--o{ jobs : "submitted"
    cv_versions ||--o{ gap_analyses : "analyzed"
    job_postings ||--o{ gap_analyses : "compared"
    gap_analyses ||--o| cv_rewrites : "produces"
    job_postings ||--o{ interview_sessions : "prepares"
```

---

## Terraform Deployment Order

```mermaid
flowchart LR
    subgraph Phase1["Phase 1: Foundation"]
        T2[2_sagemaker<br/>Embedding Endpoint]
        T5[5_database<br/>Aurora Serverless]
    end

    subgraph Phase2["Phase 2: Data Layer"]
        T3[3_ingestion<br/>S3 Vectors + Ingest API]
    end

    subgraph Phase3["Phase 3: Processing"]
        T4[4_researcher<br/>App Runner Service]
        T6[6_agents<br/>Lambda Agents + SQS]
    end

    subgraph Phase4["Phase 4: Frontend"]
        T7[7_frontend<br/>CloudFront + API GW]
    end

    subgraph Phase5["Phase 5: Observability"]
        T8[8_enterprise<br/>CloudWatch Dashboards]
    end

    T2 --> T3
    T3 --> T4
    T5 --> T6
    T2 & T3 & T5 --> T6
    T5 & T6 --> T7
    T7 --> T8
    T4 --> T8

    style T2 fill:#e1f5fe
    style T3 fill:#e1f5fe
    style T4 fill:#fff3e0
    style T5 fill:#e8f5e9
    style T6 fill:#fff3e0
    style T7 fill:#fce4ec
    style T8 fill:#f3e5f5
```

---

## Agent Capabilities Summary

| Agent | Input | Output | Tools | AI Model |
|-------|-------|--------|-------|----------|
| **Orchestrator** | Job request | Coordinated results | `invoke_extractor`, `invoke_analyzer`, `invoke_interviewer`, `invoke_charter` | Bedrock Nova Pro |
| **Extractor** | Raw text (CV/Job) | `CVProfile` or `JobProfile` | None (Structured Outputs) | Bedrock Nova Pro |
| **Analyzer** | CV + Job profiles | `GapAnalysis` + `CVRewrite` | `get_bullet_templates`, `get_ats_keywords` | Bedrock Nova Pro |
| **Interviewer** | CV + Job + Gap | `InterviewPack` | `get_interview_questions` | Bedrock Nova Pro |
| **Charter** | User applications | Analytics charts | None | Bedrock Nova Pro |
| **Researcher** | Research topics | Research findings | `store_research`, `ingest_document`, MCP Playwright | Bedrock Nova Pro |

---

## Request Types Handled

```mermaid
flowchart LR
    subgraph Requests["Request Types"]
        R1[cv_parse]
        R2[job_parse]
        R3[gap_analysis]
        R4[cv_rewrite]
        R5[interview_prep]
        R6[get_analytics]
        R7[full_analysis]
    end

    subgraph Agents["Agents"]
        Ext[Extractor]
        Ana[Analyzer]
        Int[Interviewer]
        Cha[Charter]
    end

    R1 --> Ext
    R2 --> Ext
    R3 --> Ana
    R4 --> Ana
    R5 --> Int
    R6 --> Cha
    R7 --> Ext & Ana & Int
```

---

*Generated: January 2026 | CareerAssist v1.0*
