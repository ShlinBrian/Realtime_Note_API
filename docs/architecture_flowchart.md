# Realtime Notes API - Architecture Flow Chart

## System Overview

```mermaid
graph TB
    %% External Clients
    Client[🖥️ Web Client]
    Mobile[📱 Mobile App]
    IoT[🤖 IoT Device]
    CLI[💻 CLI Tool]

    %% Load Balancer / Gateway
    LB[⚖️ Load Balancer<br/>Kubernetes Ingress]

    %% API Surfaces
    REST[🌐 REST API<br/>Port 8000<br/>FastAPI]
    WS[🔌 WebSocket API<br/>/ws/notes/note_id<br/>Real-time Collaboration]
    GRPC[⚡ gRPC API<br/>Port 50051<br/>High Performance]

    %% Authentication & Authorization
    Auth[🔐 Authentication Layer<br/>API Keys & OAuth 2.1]
    RateLimit[🚦 Rate Limiting<br/>Redis Token Bucket<br/>Per Organization]

    %% Core Application Layer
    Router[🎯 FastAPI Routers<br/>Notes | Search | Auth | Admin | API Keys]

    %% Business Logic Services
    NotesService[📝 Notes Service<br/>CRUD & Versioning]
    SearchService[🔍 Search Service<br/>Vector Embeddings]
    CollabService[👥 Collaboration Service<br/>WebSocket Manager]
    BillingService[💰 Billing Service<br/>Usage Tracking]

    %% Data Storage Layer
    PostgresDB[(🐘 PostgreSQL<br/>Primary Database<br/>Notes & Users)]
    Redis[(📦 Redis<br/>Pub/Sub & Rate Limiting<br/>WebSocket Scaling)]
    FAISS[(🧠 FAISS Index<br/>Vector Search<br/>Semantic Similarity)]

    %% External Services
    Embedding[🤖 Embedding Model<br/>Text to Vector<br/>384 Dimensions]

    %% Infrastructure
    Docker[🐳 Docker Compose<br/>Local Development]
    K8s[☸️ Kubernetes<br/>Production Deployment<br/>Helm Charts]

    %% Flow Connections
    Client --> LB
    Mobile --> LB
    IoT --> LB
    CLI --> LB

    LB --> REST
    LB --> WS
    LB --> GRPC

    REST --> Auth
    WS --> Auth
    GRPC --> Auth

    Auth --> RateLimit
    RateLimit --> Router

    Router --> NotesService
    Router --> SearchService
    Router --> CollabService
    Router --> BillingService

    %% WebSocket Flow
    WS --> CollabService
    CollabService --> Redis
    Redis --> WS

    %% Search Flow
    SearchService --> FAISS
    SearchService --> Embedding
    NotesService --> Embedding
    Embedding --> FAISS

    %% Data Layer
    NotesService --> PostgresDB
    Auth --> PostgresDB
    BillingService --> PostgresDB

    CollabService --> Redis
    RateLimit --> Redis

    %% Deployment
    REST -.-> Docker
    Docker -.-> K8s

    %% Styling
    classDef client fill:#e1f5fe
    classDef api fill:#f3e5f5
    classDef auth fill:#fff3e0
    classDef service fill:#e8f5e8
    classDef storage fill:#fff8e1
    classDef infra fill:#fce4ec

    class Client,Mobile,IoT,CLI client
    class REST,WS,GRPC,Router api
    class Auth,RateLimit auth
    class NotesService,SearchService,CollabService,BillingService service
    class PostgresDB,Redis,FAISS,Embedding storage
    class Docker,K8s,LB infra
```

## Alternative: Left-to-Right Layout

```mermaid
graph LR
    Client[Web Client] --> REST[REST API]
    REST --> Auth[Auth Layer]
    Auth --> Notes[Notes Service]
    Notes --> DB[(PostgreSQL)]

    Client --> WS[WebSocket]
    WS --> Collab[Collaboration]
    Collab --> Redis[(Redis)]

    Notes --> Search[Search Service]
    Search --> FAISS[(FAISS Index)]
```

## Simplified Architecture Diagram

```mermaid
graph TB
    %% Client Layer
    Client[Web Client]
    Mobile[Mobile App]
    CLI[CLI Tool]

    %% API Gateway
    Gateway[Load Balancer]

    %% API Layer
    REST[REST API<br/>FastAPI]
    WS[WebSocket API<br/>Real-time]
    GRPC[gRPC API<br/>High Performance]

    %% Auth Layer
    Auth[Authentication<br/>API Keys & OAuth]
    RateLimit[Rate Limiting<br/>Redis]

    %% Services
    Notes[Notes Service<br/>CRUD]
    Search[Search Service<br/>Vector Search]
    Collab[Collaboration<br/>WebSocket Manager]
    Billing[Billing<br/>Usage Tracking]

    %% Storage
    DB[(PostgreSQL<br/>Primary DB)]
    Cache[(Redis<br/>Pub/Sub)]
    Index[(FAISS<br/>Vector Index)]

    %% Connections
    Client --> Gateway
    Mobile --> Gateway
    CLI --> Gateway

    Gateway --> REST
    Gateway --> WS
    Gateway --> GRPC

    REST --> Auth
    WS --> Auth
    GRPC --> Auth

    Auth --> RateLimit

    RateLimit --> Notes
    RateLimit --> Search
    RateLimit --> Collab
    RateLimit --> Billing

    Notes --> DB
    Search --> Index
    Collab --> Cache
    Billing --> DB

    %% Styling
    classDef client fill:#e3f2fd
    classDef api fill:#f3e5f5
    classDef service fill:#e8f5e8
    classDef storage fill:#fff8e1

    class Client,Mobile,CLI client
    class REST,WS,GRPC api
    class Notes,Search,Collab,Billing service
    class DB,Cache,Index storage
```

## Horizontal Flow Diagram

```mermaid
graph LR
    %% Client to API
    Client[Client Apps] --> Gateway[Load Balancer]
    Gateway --> API[API Layer<br/>REST/WS/gRPC]

    %% Auth Flow
    API --> Auth[Authentication]
    Auth --> RL[Rate Limiting]

    %% Services
    RL --> Services[Core Services]
    Services --> Notes[Notes CRUD]
    Services --> Search[Vector Search]
    Services --> Realtime[Real-time Collab]

    %% Data Layer
    Notes --> DB[(PostgreSQL)]
    Search --> FAISS[(FAISS Index)]
    Realtime --> Redis[(Redis Pub/Sub)]

    %% Styling
    classDef primary fill:#1976d2,stroke:#fff,color:#fff
    classDef secondary fill:#388e3c,stroke:#fff,color:#fff
    classDef storage fill:#f57c00,stroke:#fff,color:#fff

    class Gateway,API primary
    class Auth,RL,Services secondary
    class DB,FAISS,Redis storage
```

## Component Breakdown

### API Layer

- **REST API**: Standard HTTP endpoints for CRUD operations
- **WebSocket**: Real-time collaboration with JSON patches
- **gRPC**: High-performance binary protocol

### Authentication

- **API Keys**: Primary authentication method
- **OAuth 2.1**: Device code flow for IoT/CLI
- **Rate Limiting**: Redis-based token bucket

### Core Services

- **Notes Service**: CRUD with versioning
- **Search Service**: Vector similarity search
- **Collaboration**: Real-time multi-user editing
- **Billing**: Usage tracking and metering

### Data Storage

- **PostgreSQL**: Primary relational database
- **Redis**: Pub/sub and caching
- **FAISS**: Vector search indices

## Usage

1. Open this file in VS Code
2. Use Ctrl+Shift+V (Cmd+Shift+V on Mac) to preview
3. The Mermaid diagrams will render automatically
4. You can also copy the mermaid code to online tools like:
   - [Mermaid Live Editor](https://mermaid.live)
   - [GitHub/GitLab markdown files](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams)

## Data Flow Examples

### Note Creation Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant Auth as Auth Service
    participant DB as PostgreSQL
    participant S as Search Service
    participant F as FAISS

    C->>A: POST /v1/notes
    A->>Auth: Validate API Key
    Auth-->>A: User & Org Info
    A->>DB: Insert Note
    DB-->>A: Note Created
    A->>S: Index Note Content
    S->>F: Add Vector Embedding
    F-->>S: Index Updated
    A-->>C: 201 Created
```

### Real-time Collaboration Flow

```mermaid
sequenceDiagram
    participant C1 as Client 1
    participant C2 as Client 2
    participant WS as WebSocket API
    participant R as Redis
    participant DB as PostgreSQL

    C1->>WS: Connect to /ws/notes/123
    C2->>WS: Connect to /ws/notes/123

    C1->>WS: Send JSON Patch
    WS->>DB: Update Note
    WS->>R: Publish Change
    R->>WS: Broadcast to All
    WS->>C2: Send Patch
    WS->>C1: Confirm Update
```
