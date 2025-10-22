# Syntrix AI - Prior Authorization System - Architecture

**Account**: 365844621293  
**Region**: us-east-1  
**Deployment**: Production-Ready

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
│                                                                               │
│  Next.js 15 Application (React 19 + TypeScript)                             │
│  ├─ Server-Side Rendering                                                    │
│  ├─ API Routes (Backend-for-Frontend)                                        │
│  ├─ Static Assets                                                            │
│  └─ WebSocket Support (future)                                               │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS SERVICES                                    │
│                                                                               │
│  ┌─────────────────────┐  ┌──────────────────┐  ┌─────────────────────┐   │
│  │   Amazon S3         │  │  AWS Lambda      │  │  Amazon DynamoDB    │   │
│  │                     │  │                  │  │                     │   │
│  │  3 Buckets:         │  │  7 Functions:    │  │  Table:             │   │
│  │  • Clinical Notes   │  │  • Extraction    │  │  pa-agent-cases     │   │
│  │  • Evidence Docs    │  │  • Orchestrator  │  │                     │   │
│  │  • Access Logs      │  │  • Validator     │  │  Schema:            │   │
│  │                     │  │  • Checker       │  │  PK: case_id        │   │
│  │  Encryption:        │  │  • Payer API     │  │  Billing: On-demand │   │
│  │  Server-side (AWS)  │  │  • Get Case      │  │  Encryption: AWS    │   │
│  │                     │  │  • Q Source      │  │                     │   │
│  │  Lifecycle: 90d     │  │                  │  │  Items: Variable    │   │
│  └─────────────────────┘  │  Runtime: 3.11   │  └─────────────────────┘   │
│                            │  Memory: 512MB   │                             │
│                            │  Timeout: 60s    │                             │
│                            └──────────────────┘                             │
│                                     │                                        │
│                                     ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Amazon Bedrock                                │   │
│  │                                                                       │   │
│  │  Model: amazon.nova-pro-v1:0                                         │   │
│  │  • Input tokens: 5000 max                                            │   │
│  │  • Output tokens: 5000 max                                           │   │
│  │  • Temperature: 0.2-0.7                                              │   │
│  │                                                                       │   │
│  │  APIs:                                                                │   │
│  │  • InvokeModel (legacy)                                              │   │
│  │  • Converse (primary)                                                │   │
│  │                                                                       │   │
│  │  Primary: amazon.nova-pro-v1:0                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│                                     ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Amazon Bedrock Agents                             │   │
│  │                                                                       │   │
│  │  Agent ID: D9SG74SCEZ                                                │   │
│  │  Alias ID: XCFULRHH4I                                                │   │
│  │  Name: pa-orchestration-agent                                        │   │
│  │  Status: PREPARED                                                    │   │
│  │                                                                       │   │
│  │  Configuration: USE_BEDROCK_AGENT=true                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     External Services                                │   │
│  │                                                                       │   │
│  │  NIH Clinical Tables API                                             │   │
│  │  Endpoint: clinicaltables.nlm.nih.gov/api/icd10cm/v3/search         │   │
│  │  Purpose: ICD-10 code validation                                     │   │
│  │  Rate Limit: Unspecified                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Lambda Functions

### pa-extraction-agent
**Runtime**: Python 3.11  
**Memory**: 512 MB  
**Timeout**: 60s  
**Handler**: extraction_agent.lambda_handler

**Input**:
```json
{
  "bucket": "string",
  "key": "string"
}
```

**Output**:
```json
{
  "case_id": "uuid",
  "extracted_data": {
    "patient_name": "string",
    "diagnosis": "string",
    "ICD10": ["string"],
    "CPT": ["string"],
    "summary": "string",
    "evidence": {}
  }
}
```

**Dependencies**:
- boto3
- Amazon Bedrock (nova-pro-v1:0)
- DynamoDB (write)
- S3 (read)

---

### pa-orchestrator
**Runtime**: Python 3.11  
**Memory**: 512 MB  
**Timeout**: 60s  
**Handler**: agent_orchestrator.lambda_handler

**Modes**:
1. Bedrock Agent Mode (USE_BEDROCK_AGENT=true)
2. Simple Orchestration Mode (fallback)

**Input**:
```json
{
  "case_id": "uuid"
}
```

**Output**:
```json
{
  "status": "approved|denied",
  "authorization_number": "string",
  "reason": "string",
  "validation": {},
  "evidence": {},
  "payer": {}
}
```

**Invokes**:
- pa-code-validator
- pa-evidence-checker
- pa-mock-payer-api

---

### pa-code-validator
**Runtime**: Python 3.11  
**Memory**: 512 MB  
**Timeout**: 60s  
**Handler**: code_validator.lambda_handler

**External APIs**:
- NIH Clinical Tables (ICD-10)
- Amazon Bedrock (medical necessity)

**Input**:
```json
{
  "extracted_data": {
    "ICD10": ["string"],
    "CPT": ["string"],
    "diagnosis": "string",
    "summary": "string"
  }
}
```

**Output**:
```json
{
  "all_valid": "boolean",
  "icd10_validations": [],
  "cpt_validations": [],
  "code_pairings": [],
  "warnings": [],
  "errors": []
}
```

---

### pa-evidence-checker
**Runtime**: Python 3.11  
**Memory**: 512 MB  
**Timeout**: 60s  
**Handler**: evidence_checker.lambda_handler

**Input**:
```json
{
  "case_id": "uuid",
  "cpt_codes": ["string"]
}
```

**Output**:
```json
{
  "is_complete": "boolean",
  "required_docs": ["string"],
  "found_docs": ["string"],
  "missing_docs": ["string"],
  "completeness_percentage": "decimal"
}
```

---

### pa-mock-payer-api
**Runtime**: Python 3.11  
**Memory**: 512 MB  
**Timeout**: 60s  
**Handler**: mock_payer_api.lambda_handler

**Input**:
```json
{
  "patient": {},
  "diagnosis": ["string"],
  "procedures": ["string"],
  "evidence": {},
  "clinical_summary": "string"
}
```

**Output**:
```json
{
  "status": "Approved|Denied",
  "authorization_number": "string",
  "reason": "string",
  "code_appropriateness": "string",
  "medical_necessity": "string",
  "confidence": "high|medium|low"
}
```

---

### pa-get-case-data
**Runtime**: Python 3.11  
**Memory**: 128 MB  
**Timeout**: 30s  
**Handler**: get_case_data.lambda_handler

**Input**:
```json
{
  "case_id": "uuid"
}
```

**Output**:
```json
{
  "success": "boolean",
  "case_data": {}
}
```

---

### pa-q-data-source
**Runtime**: Python 3.11  
**Memory**: 512 MB  
**Timeout**: 60s  
**Handler**: q_data_source.lambda_handler  
**Status**: Deployed, not integrated

---

## API Routes (Next.js)

### POST /api/upload
**Purpose**: Upload clinical note to S3, trigger extraction

**Request**:
```typescript
FormData {
  file: File
}
```

**Response**:
```json
{
  "case_id": "uuid",
  "extracted_data": {},
  "message": "string"
}
```

**AWS Operations**:
- S3.PutObject
- Lambda.Invoke (pa-extraction-agent)

---

### POST /api/orchestrate
**Purpose**: Trigger case orchestration workflow

**Request**:
```json
{
  "case_id": "uuid"
}
```

**Response**:
```json
{
  "success": "boolean",
  "status": "string",
  "authorization_number": "string",
  "reason": "string"
}
```

**AWS Operations**:
- Lambda.Invoke (pa-orchestrator)

---

### GET /api/cases
**Purpose**: Retrieve all cases

**Response**:
```json
[
  {
    "case_id": "uuid",
    "patient_name": "string",
    "status": "string",
    "created_at": "iso8601"
  }
]
```

**AWS Operations**:
- DynamoDB.Scan

---

### GET /api/cases/[id]
**Purpose**: Retrieve specific case

**Response**:
```json
{
  "case_id": "uuid",
  "patient_name": "string",
  "diagnosis": "string",
  "ICD10": [],
  "CPT": [],
  "status": "string",
  "payer_response": {},
  "timeline": []
}
```

**AWS Operations**:
- DynamoDB.GetItem

---

### POST /api/chat
**Purpose**: Conversational AI assistant

**Request**:
```json
{
  "message": "string",
  "history": []
}
```

**Response**:
```json
{
  "success": "boolean",
  "response": "string"
}
```

**Implementation**: Bedrock Converse API with tool calling

**Tools**:
- query_cases
- get_case_details
- get_statistics

**AWS Operations**:
- Bedrock.Converse
- DynamoDB (via tools)

---

### GET /api/statistics
**Purpose**: Calculate case statistics

**Response**:
```json
{
  "total_cases": "integer",
  "approved": "integer",
  "denied": "integer",
  "pending": "integer",
  "approval_rate": "float"
}
```

**AWS Operations**:
- DynamoDB.Scan

---

## DynamoDB Schema

**Table Name**: pa-agent-cases  
**Partition Key**: case_id (String)  
**Billing Mode**: PAY_PER_REQUEST

### Attributes

```typescript
{
  case_id: string;                    // UUID
  patient_name: string;
  diagnosis: string;
  ICD10: string[];
  CPT: string[];
  summary: string;
  status: "extracted" | "processing" | "approved" | "denied" | "pending";
  created_at: string;                 // ISO 8601
  updated_at: string;                 // ISO 8601
  authorization_number?: string;
  payer_response?: {
    status: string;
    reason?: string;
    code_appropriateness?: string;
    medical_necessity?: string;
  };
  payer_result?: {};                  // Alternative field
  validation_result?: {
    all_valid: boolean;
    icd10_validations: [];
    cpt_validations: [];
    code_pairings: [];
  };
  evidence_result?: {
    is_complete: boolean;
    missing_docs: string[];
    completeness_percentage: number;
  };
  evidence?: {
    pt_notes?: boolean;
    clinical_notes?: boolean;
    xray?: boolean;
    referral?: boolean;
  };
  timeline?: [
    {
      timestamp: string;
      event: string;
      status: string;
    }
  ];
  s3_key?: string;
  processing_started_at?: string;
  processed_at?: string;
}
```

---

## IAM Configuration

### Lambda Execution Role
**Name**: pa-agent-lambda-role  
**ARN**: arn:aws:iam::365844621293:role/pa-agent-lambda-role

**Attached Policies**:
- arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
- arn:aws:iam::aws:policy/AmazonS3FullAccess
- arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
- arn:aws:iam::aws:policy/AmazonBedrockFullAccess

**Trust Relationship**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

---

## Environment Variables

### Lambda Functions
```bash
BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
BEDROCK_AGENT_ID=D9SG74SCEZ
BEDROCK_AGENT_ALIAS_ID=XCFULRHH4I
USE_BEDROCK_AGENT=true
MASK_PHI=true
DYNAMODB_TABLE=pa-agent-cases
S3_CLINICAL_NOTES_BUCKET=pa-agent-clinical-notes-365844621293
S3_EVIDENCE_BUCKET=pa-agent-evidence-docs-365844621293
AWS_REGION=us-east-1
```

### Next.js Application
```bash
# Public (Client-side)
NEXT_PUBLIC_AWS_REGION=us-east-1
NEXT_PUBLIC_AWS_ACCOUNT_ID=365844621293
NEXT_PUBLIC_S3_CLINICAL_NOTES_BUCKET=pa-agent-clinical-notes-365844621293
NEXT_PUBLIC_S3_EVIDENCE_BUCKET=pa-agent-evidence-docs-365844621293
NEXT_PUBLIC_DYNAMODB_TABLE=pa-agent-cases
NEXT_PUBLIC_BEDROCK_MODEL_ID=amazon.nova-pro-v1:0

# Server-side Only
AWS_ACCESS_KEY_ID=AKIAVKLQJ47WWJH6MF4O
AWS_SECRET_ACCESS_KEY=[REDACTED]
AWS_REGION=us-east-1
```

---

## Data Flow Sequences

### 1. Case Submission Flow

```
┌──────┐                ┌─────────┐              ┌────┐              ┌─────────────┐            ┌─────────┐            ┌─────────┐
│Client│                │Next.js  │              │ S3 │              │pa-extraction│            │Bedrock  │            │DynamoDB │
│      │                │/api/up  │              │    │              │   -agent    │            │         │            │         │
└──┬───┘                └────┬────┘              └─┬──┘              └──────┬──────┘            └────┬────┘            └────┬────┘
   │                         │                     │                        │                        │                     │
   │ POST FormData{file}     │                     │                        │                        │                     │
   ├────────────────────────>│                     │                        │                        │                     │
   │                         │                     │                        │                        │                     │
   │                         │ PutObject()         │                        │                        │                     │
   │                         │ Bucket: clinical-notes                       │                        │                     │
   │                         │ Key: notes/{ts}_{fn}│                        │                        │                     │
   │                         ├────────────────────>│                        │                        │                     │
   │                         │                     │                        │                        │                     │
   │                         │      200 OK         │                        │                        │                     │
   │                         │      {ETag}         │                        │                        │                     │
   │                         │<────────────────────┤                        │                        │                     │
   │                         │                     │                        │                        │                     │
   │                         │ Invoke()            │                        │                        │                     │
   │                         │ FunctionName: pa-extraction-agent            │                        │                     │
   │                         │ Payload: {bucket, key}                       │                        │                     │
   │                         ├──────────────────────────────────────────────>│                        │                     │
   │                         │                     │                        │                        │                     │
   │                         │                     │   GetObject()          │                        │                     │
   │                         │                     │   Bucket: clinical-notes                        │                     │
   │                         │                     │   Key: notes/{ts}_{fn} │                        │                     │
   │                         │                     │<───────────────────────┤                        │                     │
   │                         │                     │                        │                        │                     │
   │                         │                     │   200 OK               │                        │                     │
   │                         │                     │   Body: <file content> │                        │                     │
   │                         │                     ├───────────────────────>│                        │                     │
   │                         │                     │                        │                        │                     │
   │                         │                     │                        │ InvokeModel()          │                     │
   │                         │                     │                        │ Model: nova-pro-v1:0   │                     │
   │                         │                     │                        │ Body: {messages:[{role,content}]}            │
   │                         │                     │                        ├───────────────────────>│                     │
   │                         │                     │                        │                        │                     │
   │                         │                     │                        │ 200 OK                 │                     │
   │                         │                     │                        │ Body: {output:{message:{content}}}           │
   │                         │                     │                        │<───────────────────────┤                     │
   │                         │                     │                        │                        │                     │
   │                         │                     │                        │ PutItem()              │                     │
   │                         │                     │                        │ TableName: pa-agent-cases                   │
   │                         │                     │                        │ Item: {case_id, patient_name, ICD10, CPT...}│
   │                         │                     │                        ├────────────────────────────────────────────>│
   │                         │                     │                        │                        │                     │
   │                         │                     │                        │                        │   200 OK            │
   │                         │                     │                        │<────────────────────────────────────────────┤
   │                         │                     │                        │                        │                     │
   │                         │ 200 OK              │                        │                        │                     │
   │                         │ {statusCode:200, body:{case_id, extracted_data}}                      │                     │
   │                         │<──────────────────────────────────────────────┤                        │                     │
   │                         │                     │                        │                        │                     │
   │ 200 OK                  │                     │                        │                        │                     │
   │ {case_id, extracted_data, message}           │                        │                        │                     │
   │<────────────────────────┤                     │                        │                        │                     │
   │                         │                     │                        │                        │                     │
```

**Returns**:
- Client receives: `{case_id: "uuid", extracted_data: {...}, message: "string"}`
- S3 stores: File at `notes/{timestamp}_{filename}`
- DynamoDB stores: Case record with status="extracted"

---

### 2. Orchestration Flow (Simple Mode)

```
┌──────┐        ┌─────────┐        ┌──────────┐        ┌─────────┐        ┌──────────┐        ┌──────────┐        ┌─────────┐
│Client│        │Next.js  │        │pa-orch   │        │DynamoDB │        │pa-code   │        │pa-evid   │        │pa-payer │
│      │        │/api/orch│        │          │        │         │        │-validator│        │-checker  │        │-api     │
└──┬───┘        └────┬────┘        └────┬─────┘        └────┬────┘        └────┬─────┘        └────┬─────┘        └────┬────┘
   │                 │                   │                   │                   │                   │                   │
   │ POST {case_id}  │                   │                   │                   │                   │                   │
   ├────────────────>│                   │                   │                   │                   │                   │
   │                 │                   │                   │                   │                   │                   │
   │                 │ Invoke()          │                   │                   │                   │                   │
   │                 │ Payload:{case_id} │                   │                   │                   │                   │
   │                 ├──────────────────>│                   │                   │                   │                   │
   │                 │                   │                   │                   │                   │                   │
   │                 │                   │ GetItem()         │                   │                   │                   │
   │                 │                   │ Key:{case_id}     │                   │                   │                   │
   │                 │                   ├──────────────────>│                   │                   │                   │
   │                 │                   │                   │                   │                   │                   │
   │                 │                   │ Item:{...caseData}│                   │                   │                   │
   │                 │                   │<──────────────────┤                   │                   │                   │
   │                 │                   │                   │                   │                   │                   │
   │                 │                   │ UpdateItem()      │                   │                   │                   │
   │                 │                   │ status:processing │                   │                   │                   │
   │                 │                   ├──────────────────>│                   │                   │                   │
   │                 │                   │ 200 OK            │                   │                   │                   │
   │                 │                   │<──────────────────┤                   │                   │                   │
   │                 │                   │                   │                   │                   │                   │
   │                 │                   │ Invoke()          │                   │                   │                   │
   │                 │                   │ Payload:{extracted_data:{ICD10,CPT}}  │                   │                   │
   │                 │                   ├──────────────────────────────────────>│                   │                   │
   │                 │                   │                   │                   │                   │                   │
   │                 │                   │                   │    [NIH API Call] │                   │                   │
   │                 │                   │                   │    [Bedrock Call] │                   │                   │
   │                 │                   │                   │                   │                   │                   │
   │                 │                   │ 200 OK            │                   │                   │                   │
   │                 │                   │ {all_valid, validations[], pairings[]}│                   │                   │
   │                 │                   │<──────────────────────────────────────┤                   │                   │
   │                 │                   │                   │                   │                   │                   │
   │                 │                   │ Invoke()          │                   │                   │                   │
   │                 │                   │ Payload:{case_id, cpt_codes}          │                   │                   │
   │                 │                   ├───────────────────────────────────────────────────────────>│                   │
   │                 │                   │                   │                   │                   │                   │
   │                 │                   │                   │                   │                   │ [S3 Check Docs]   │
   │                 │                   │                   │                   │                   │                   │
   │                 │                   │ 200 OK            │                   │                   │                   │
   │                 │                   │ {is_complete, missing_docs[], found_docs[]}               │                   │
   │                 │                   │<───────────────────────────────────────────────────────────┤                   │
   │                 │                   │                   │                   │                   │                   │
   │                 │                   │ Invoke()          │                   │                   │                   │
   │                 │                   │ Payload:{patient, diagnosis[], procedures[], evidence{}}   │                   │
   │                 │                   ├───────────────────────────────────────────────────────────────────────────────>│
   │                 │                   │                   │                   │                   │                   │
   │                 │                   │                   │                   │                   │    [Bedrock Nova] │
   │                 │                   │                   │                   │                   │    [AI Review]    │
   │                 │                   │                   │                   │                   │                   │
   │                 │                   │ 200 OK            │                   │                   │                   │
   │                 │                   │ {status:Approved/Denied, authorization_number, reason, ...}│                   │
   │                 │                   │<───────────────────────────────────────────────────────────────────────────────┤
   │                 │                   │                   │                   │                   │                   │
   │                 │                   │ UpdateItem()      │                   │                   │                   │
   │                 │                   │ status:approved/denied                │                   │                   │
   │                 │                   │ validation_result, evidence_result, payer_result          │                   │
   │                 │                   ├──────────────────>│                   │                   │                   │
   │                 │                   │ 200 OK            │                   │                   │                   │
   │                 │                   │<──────────────────┤                   │                   │                   │
   │                 │                   │                   │                   │                   │                   │
   │                 │ 200 OK            │                   │                   │                   │                   │
   │                 │ {status, auth_number, reason, validation, evidence, payer}│                   │                   │
   │                 │<──────────────────┤                   │                   │                   │                   │
   │                 │                   │                   │                   │                   │                   │
   │ 200 OK          │                   │                   │                   │                   │                   │
   │ {success:true, status, ...}         │                   │                   │                   │                   │
   │<────────────────┤                   │                   │                   │                   │                   │
   │                 │                   │                   │                   │                   │                   │
```

**Returns**:
- Client receives: `{success:true, status:"approved/denied", authorization_number, reason, ...}`
- DynamoDB updated: Case record with final status, all results, timeline events

---

### 3. Chat Flow (Bedrock Converse with Tools)

```
┌──────┐          ┌─────────┐          ┌─────────┐          ┌─────────┐
│Client│          │Next.js  │          │Bedrock  │          │DynamoDB │
│      │          │/api/chat│          │Converse │          │         │
└──┬───┘          └────┬────┘          └────┬────┘          └────┬────┘
   │                   │                     │                    │
   │ POST              │                     │                    │
   │ {message, history}│                     │                    │
   ├──────────────────>│                     │                    │
   │                   │                     │                    │
   │                   │ Converse()          │                    │
   │                   │ modelId: nova-pro   │                    │
   │                   │ messages: [{role,content}]               │
   │                   │ toolConfig: {tools:[query_cases,...]}    │
   │                   ├────────────────────>│                    │
   │                   │                     │                    │
   │                   │                     │ [AI Processing]    │
   │                   │                     │ stopReason:tool_use│
   │                   │                     │                    │
   │                   │ Response            │                    │
   │                   │ {output:{message:{content:[{toolUse}]}}} │
   │                   │<────────────────────┤                    │
   │                   │                     │                    │
   │                   │ Execute Tool        │                    │
   │                   │ if toolName=="query_cases"               │
   │                   ├─────────────────────────────────────────>│
   │                   │                     │    Scan()          │
   │                   │                     │    FilterExpression│
   │                   │                     │                    │
   │                   │ Tool Result         │    Items:[]        │
   │                   │ {cases:[...]}       │                    │
   │                   │<─────────────────────────────────────────┤
   │                   │                     │                    │
   │                   │ Converse() [2nd]    │                    │
   │                   │ messages: [..., {role:user, content:[{toolResult}]}]
   │                   ├────────────────────>│                    │
   │                   │                     │                    │
   │                   │                     │ [AI Synthesizes]   │
   │                   │                     │ stopReason:end     │
   │                   │                     │                    │
   │                   │ Response            │                    │
   │                   │ {output:{message:{content:[{text}]}}}    │
   │                   │<────────────────────┤                    │
   │                   │                     │                    │
   │                   │ Strip <thinking>    │                    │
   │                   │ regex.replace()     │                    │
   │                   │                     │                    │
   │ 200 OK            │                     │                    │
   │ {success:true, response:"Natural language answer"}           │
   │<──────────────────┤                     │                    │
   │                   │                     │                    │
```

**Returns**:
- Client receives: `{success:true, response:"Natural language answer with data"}`
- No database writes (read-only)
- Bedrock receives tool results, synthesizes final answer

---

### 4. Case Retrieval Flow

```
┌──────┐          ┌─────────┐          ┌─────────┐
│Client│          │Next.js  │          │DynamoDB │
│      │          │/api/cases│         │         │
└──┬───┘          └────┬────┘          └────┬────┘
   │                   │                     │
   │ GET /api/cases    │                     │
   ├──────────────────>│                     │
   │                   │                     │
   │                   │ Scan()              │
   │                   │ TableName: pa-agent-cases
   │                   ├────────────────────>│
   │                   │                     │
   │                   │ Items: [...]        │
   │                   │<────────────────────┤
   │                   │                     │
   │                   │ Sort by created_at  │
   │                   │                     │
   │ 200 OK            │                     │
   │ [{case_id, patient_name, status, ...}] │
   │<──────────────────┤                     │
   │                   │                     │
   │                   │                     │
   │ GET /api/cases/123│                     │
   ├──────────────────>│                     │
   │                   │                     │
   │                   │ GetItem()           │
   │                   │ Key: {case_id:"123"}│
   │                   ├────────────────────>│
   │                   │                     │
   │                   │ Item: {...}         │
   │                   │<────────────────────┤
   │                   │                     │
   │ 200 OK            │                     │
   │ {case_id, patient_name, ICD10, CPT, ...}
   │<──────────────────┤                     │
   │                   │                     │
```

**Returns**:
- GET /api/cases → Array of case summaries
- GET /api/cases/[id] → Full case object with all fields

---

### 5. Statistics Calculation Flow

```
┌──────┐          ┌─────────┐          ┌─────────┐
│Client│          │Next.js  │          │DynamoDB │
│      │          │/api/stats│         │         │
└──┬───┘          └────┬────┘          └────┬────┘
   │                   │                     │
   │ GET /api/statistics                     │
   ├──────────────────>│                     │
   │                   │                     │
   │                   │ Scan()              │
   │                   │ TableName: pa-agent-cases
   │                   ├────────────────────>│
   │                   │                     │
   │                   │ Items: [all cases]  │
   │                   │<────────────────────┤
   │                   │                     │
   │                   │ Calculate:          │
   │                   │ - total_cases       │
   │                   │ - approved (filter) │
   │                   │ - denied (filter)   │
   │                   │ - pending (filter)  │
   │                   │ - approval_rate     │
   │                   │                     │
   │ 200 OK            │                     │
   │ {total_cases, approved, denied, pending, approval_rate}
   │<──────────────────┤                     │
   │                   │                     │
```

**Returns**:
- Client receives: `{total_cases:N, approved:N, denied:N, pending:N, approval_rate:X.X%}`
- Calculated in-memory from DynamoDB scan results

---

## Network Architecture

```
Internet
    │
    ├─ HTTPS → Next.js Application
    │           │
    │           ├─ /api/* → AWS SDK calls
    │           │           │
    │           │           ├─ S3 API (TLS 1.2+)
    │           │           ├─ Lambda API (TLS 1.2+)
    │           │           ├─ DynamoDB API (TLS 1.2+)
    │           │           └─ Bedrock API (TLS 1.2+)
    │           │
    │           └─ Pages → Static assets
    │
    └─ AWS VPC (Lambda)
            │
            ├─ NAT Gateway → Internet (for NIH API)
            ├─ VPC Endpoints → S3, DynamoDB, Bedrock
            └─ Security Groups → Port 443 outbound
```

---

## Performance Characteristics

### Lambda Cold Start
- First invocation: 1-3 seconds
- Warm invocation: 500ms - 2s
- Concurrent executions: 1-1000

### DynamoDB
- Read latency: < 10ms (p99)
- Write latency: < 10ms (p99)
- Throughput: On-demand (unlimited)

### Bedrock
- Nova Pro latency: 2-5 seconds
- Token processing: ~50 tokens/second
- Concurrent requests: 100+

### S3
- Upload latency: < 200ms
- Download latency: < 100ms
- Throughput: 3,500 PUT/s, 5,500 GET/s per prefix

---

## Monitoring

### CloudWatch Metrics

**Lambda**:
- Invocations
- Duration
- Errors
- Throttles
- ConcurrentExecutions

**DynamoDB**:
- ConsumedReadCapacityUnits
- ConsumedWriteCapacityUnits
- UserErrors
- SystemErrors

**S3**:
- AllRequests
- GetRequests
- PutRequests
- 4xxErrors
- 5xxErrors

### CloudWatch Logs

**Log Groups**:
- /aws/lambda/pa-extraction-agent
- /aws/lambda/pa-orchestrator
- /aws/lambda/pa-code-validator
- /aws/lambda/pa-evidence-checker
- /aws/lambda/pa-mock-payer-api
- /aws/lambda/pa-get-case-data
- /aws/lambda/pa-q-data-source

**Retention**: 7 days (default)

---

## Cost Model

### Monthly Estimates (1000 cases)

**Lambda**:
- Requests: 6000 × $0.0000002 = $0.0012
- Duration: 6000 × 3s × 512MB = $1.80
- **Subtotal**: $1.80

**Bedrock**:
- Input: 4M tokens × $0.80/M = $3.20
- Output: 4M tokens × $3.20/M = $12.80
- **Subtotal**: $16.00

**DynamoDB**:
- Writes: 1000 × $1.25/M = $0.00125
- Reads: 5000 × $0.25/M = $0.00125
- Storage: 1GB × $0.25/GB = $0.25
- **Subtotal**: $2.00

**S3**:
- Storage: 1GB × $0.023/GB = $0.023
- PUT: 1000 × $0.005/1000 = $0.005
- GET: 2000 × $0.0004/1000 = $0.0008
- **Subtotal**: $0.50

**Total**: $20.30/month

---

## Deployment

### Prerequisites
- AWS CLI v2.x
- Python 3.11
- Node.js 18+
- npm 9+

### Lambda Deployment
```bash
./deploy_lambdas.sh
```

### Frontend Deployment
```bash
cd frontend-modern
npm install
npm run build
npm start
```

### Infrastructure Setup
```bash
./setup_aws.sh
```

---

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | Next.js | 15.x |
| UI Library | React | 19.x |
| Language | TypeScript | 5.x |
| Backend | Python | 3.11 |
| Compute | AWS Lambda | Serverless |
| Database | DynamoDB | On-demand |
| Storage | S3 | Standard |
| AI | Bedrock Nova Pro | v1:0 |
| Orchestration | Bedrock Agents | v1 |

---

## API Endpoints Summary

| Endpoint | Method | Purpose | AWS Services |
|----------|--------|---------|--------------|
| /api/upload | POST | Upload clinical note | S3, Lambda |
| /api/orchestrate | POST | Trigger orchestration | Lambda |
| /api/cases | GET | List all cases | DynamoDB |
| /api/cases/[id] | GET | Get case details | DynamoDB |
| /api/chat | POST | AI assistant | Bedrock, DynamoDB |
| /api/statistics | GET | Get statistics | DynamoDB |

---

## Security

### Data Encryption
- S3: Server-side encryption (AES-256)
- DynamoDB: Encryption at rest (AWS managed)
- In-transit: TLS 1.2+

### Access Control
- IAM roles with least privilege
- S3 bucket policies
- DynamoDB table policies
- Lambda execution roles

### PHI Protection
- MASK_PHI flag enabled
- No PHI in CloudWatch logs
- Secure credential storage

---

**Document Version**: 2.0  
**Last Updated**: 2025-10-22  
**Status**: Production  
**Changelog**: Added detailed sequence diagrams with request/response flows

