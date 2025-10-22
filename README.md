# Syntrix AI - Prior Authorization System

[![AWS](https://img.shields.io/badge/AWS-CloudFormation-orange?logo=amazon-aws)](https://aws.amazon.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)](https://nextjs.org/)
[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue?logo=typescript)](https://typescriptlang.org/)
[![Bedrock](https://img.shields.io/badge/Amazon-Bedrock-purple?logo=amazon-aws)](https://aws.amazon.com/bedrock/)

AI-powered prior authorization automation system built on AWS serverless architecture. Extracts clinical data from unstructured notes, validates medical codes against NIH databases, checks evidence requirements, and performs AI-driven medical necessity reviews.

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/rajamuppidi/syntrixai.git
cd syntrixai

# Install dependencies
cd frontend
npm install

# Start development server
npm run dev
```

## 📋 Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- AWS CLI configured
- AWS Account with Bedrock access

## Architecture

### Frontend
- **Framework**: Next.js 16 with React 19, TypeScript
- **Styling**: Tailwind CSS 4
- **State Management**: React hooks with AWS SDK integration
- **UI Components**: Framer Motion for animations, Lucide React icons

### Backend
- **Compute**: AWS Lambda (Python 3.11)
- **Orchestration**: Bedrock Agent
- **AI Models**: Amazon Nova Pro v1.0 (all AI operations)
- **Storage**: Amazon S3 (clinical notes, evidence documents)
- **Database**: DynamoDB (on-demand, single-table design)
- **Security**: IAM roles with least-privilege policies

### Lambda Functions

```
backend/lambda_functions/
├── extraction_agent.py      # Clinical data extraction via Bedrock
├── code_validator.py         # ICD-10/CPT validation via NIH API + AI
├── evidence_checker.py       # Document verification in S3
├── mock_payer_api.py         # Medical necessity review via Bedrock
└── get_case_data.py          # DynamoDB case retrieval

backend/orchestrator/
└── agent_orchestrator.py     # Workflow coordination (Agent/Simple mode)

backend/
└── ai_assistant.py           # Conversational AI with tool calling
```

## Data Flow

### Case Submission
```
User Upload → S3 Storage → Lambda (Extraction) → Bedrock Nova → DynamoDB
```

### Orchestration
```
Frontend → Orchestrator Lambda → Bedrock Agent → [Validators] → DynamoDB → Response
```

### AI Chat
```
User Query → Next.js API → ai_assistant.py → Bedrock Converse → Tool Execution → DynamoDB
```

## Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- AWS CLI configured
- AWS Account with Bedrock access in us-east-1

### Backend Deployment

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Deploy Lambda functions:
```bash
./deploy_lambdas.sh
```

3. Deploy infrastructure (optional):
```bash
aws cloudformation create-stack \
  --stack-name pa-system \
  --template-body file://infrastructure/cloudformation/pa-system-clean.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### Frontend Deployment

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Configure environment:
```bash
# Create .env.local
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
```

3. Run development server:
```bash
npm run dev
```

4. Build for production:
```bash
npm run build
npm run start
```

## AWS Resources

### Lambda Functions (7)
- pa-extraction-agent (512MB, 60s timeout)
- pa-orchestrator (512MB, 60s timeout)
- pa-code-validator (512MB, 60s timeout)
- pa-evidence-checker (512MB, 60s timeout)
- pa-mock-payer-api (512MB, 60s timeout)
- pa-get-case-data (128MB, 30s timeout)
- pa-q-data-source (512MB, 60s timeout)

### S3 Buckets (3)
- pa-agent-clinical-notes-{account-id} (versioned, HIPAA 7-year retention)
- pa-agent-evidence-docs-{account-id} (versioned)
- pa-agent-access-logs-{account-id} (audit logs)

### DynamoDB Table
- pa-agent-cases (on-demand billing, PITR enabled)
- Primary Key: case_id (String)

### Bedrock Agent
- Agent ID: D9SG74SCEZ
- Alias (Production): XCFULRHH4I
- Action Groups: CodeValidator, EvidenceChecker, PayerSubmission, GetCaseDataGroup

## API Endpoints

### Upload Clinical Note
```typescript
POST /api/upload
Content-Type: multipart/form-data
Body: FormData { file: File }
Response: { case_id: string, extracted_data: object }
```

### Orchestrate Workflow
```typescript
POST /api/orchestrate
Body: { case_id: string }
Response: { status: string, authorization_number: string, ... }
```

### AI Chat
```typescript
POST /api/chat
Body: { messages: Array<{role: string, content: string}> }
Response: { response: string }
```

### Get Cases
```typescript
GET /api/cases
Response: Array<Case>
```

### Get Case Details
```typescript
GET /api/cases/[id]
Response: Case
```

### Get Statistics
```typescript
GET /api/statistics
Response: { total_cases: number, approval_rate: number, ... }
```

## AI Assistant

The AI assistant (`backend/ai_assistant.py`) uses Bedrock Converse API with function calling to provide conversational access to case data.

### Available Tools
- `query_cases`: Search cases by status, patient, diagnosis
- `get_case_details`: Retrieve complete case information
- `get_statistics`: Calculate approval rates and metrics

### Tool Execution Flow
```python
User Query → Bedrock Converse → Tool Request → Execute Function → Tool Result → Bedrock → Response
```

## Security

### IAM Policies
- Scoped DynamoDB access (specific table ARN)
- Scoped S3 access (specific bucket ARNs)
- Scoped Bedrock access (Nova Pro model only)
- Lambda invocation limited to pa-* functions

### Data Protection
- S3 server-side encryption (AES-256)
- DynamoDB encryption at rest
- S3 access logging enabled
- CloudWatch logging for all Lambda functions
- HIPAA-compliant 7-year retention with lifecycle policies

### Network Security
- S3 public access blocked
- IAM role-based authentication
- TLS 1.2+ for all Bedrock communication

## Cost Estimate

Monthly costs for 1000 cases:
- Bedrock AI: $16
- Lambda compute: $2
- DynamoDB: $2
- S3 storage: $2
- CloudWatch logs: $1
- **Total: ~$23/month**

## Development

### Project Structure
```
syntrix-ai/
├── backend/
│   ├── lambda_functions/        # Individual Lambda handlers
│   ├── orchestrator/            # Workflow orchestration
│   ├── ai_assistant.py          # Conversational AI
│   └── fhir/                    # FHIR parsing utilities
├── frontend/
│   ├── app/
│   │   ├── api/                 # Next.js API routes
│   │   ├── cases/               # Case management pages
│   │   ├── chat/                # AI assistant interface
│   │   ├── upload/              # Case submission
│   │   └── components/          # Shared React components
│   └── lib/                     # Utilities and AWS SDK wrappers
├── infrastructure/
│   └── cloudformation/          # IaC templates
├── sample_data/                 # Test clinical notes
└── tests/                       # Unit tests
```

### Testing

Run with sample data:
```bash
python test_local.py
```

Test individual components:
```bash
# Test extraction
python -m backend.lambda_functions.extraction_agent

# Test AI assistant
python -m backend.ai_assistant
```

### Deployment Scripts

- `deploy_lambdas.sh`: Deploy all Lambda functions
- `deploy_fhir_lambdas.sh`: Deploy FHIR-specific functions
- `setup_aws.sh`: Initial AWS resource setup

## Orchestration

Uses Bedrock Agent for autonomous workflow orchestration with action groups.

```python
USE_BEDROCK_AGENT=true
BEDROCK_AGENT_ID=D9SG74SCEZ
BEDROCK_AGENT_ALIAS_ID=XCFULRHH4I
```

## External Dependencies

### NIH Clinical Tables API
- ICD-10 code validation
- CPT code lookup
- Endpoint: `https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search`

### Required Python Packages
```
boto3>=1.40.56
botocore>=1.40.56
python-dateutil>=2.9.0
```

### Required npm Packages
```
@aws-sdk/client-bedrock-runtime: ^3.914.0
@aws-sdk/client-dynamodb: ^3.914.0
@aws-sdk/client-lambda: ^3.914.0
@aws-sdk/client-s3: ^3.914.0
next: 16.0.0
react: 19.2.0
```

## Limitations

- Single AWS region deployment (us-east-1)
- Bedrock model access required in deployment region
- NIH API rate limits apply for code validation
- DynamoDB single-table design (no GSIs)
- No built-in authentication (implement with Cognito/Auth0)

## License

MIT

## Environment Variables

### Backend Lambda Functions
```bash
DYNAMODB_TABLE=pa-agent-cases
S3_CLINICAL_NOTES_BUCKET=pa-agent-clinical-notes-{account-id}
S3_EVIDENCE_BUCKET=pa-agent-evidence-docs-{account-id}
BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
BEDROCK_AGENT_ID=D9SG74SCEZ
BEDROCK_AGENT_ALIAS_ID=XCFULRHH4I
USE_BEDROCK_AGENT=true
MASK_PHI=true
AWS_REGION=us-east-1
```

### Frontend
```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
NEXT_PUBLIC_AWS_REGION=us-east-1
```

## Infrastructure as Code

CloudFormation template available at `infrastructure/cloudformation/pa-system-clean.yaml`

Provisions:
- 3 S3 buckets with policies
- 1 DynamoDB table
- 1 IAM role with least-privilege policies
- 7 Lambda functions with placeholder code
- 1 Bedrock Agent with 4 action groups
- Lambda permissions for Bedrock invocation

Deploy with:
```bash
aws cloudformation create-stack \
  --stack-name pa-system-prod \
  --template-body file://infrastructure/cloudformation/pa-system-clean.yaml \
  --parameters \
    ParameterKey=Environment,ParameterValue=production \
    ParameterKey=AccountId,ParameterValue=365844621293 \
  --capabilities CAPABILITY_NAMED_IAM
```

## Monitoring

All Lambda functions log to CloudWatch Logs:
- `/aws/lambda/pa-extraction-agent`
- `/aws/lambda/pa-orchestrator`
- `/aws/lambda/pa-code-validator`
- `/aws/lambda/pa-evidence-checker`
- `/aws/lambda/pa-mock-payer-api`
- `/aws/lambda/pa-get-case-data`
- `/aws/lambda/pa-q-data-source`

S3 access logs stored in `pa-agent-access-logs-{account-id}` bucket.

## Production Deployment

1. Backend already deployed to AWS Lambda
2. Frontend deployment options:
   - **Vercel**: One-click deployment from GitHub
   - **AWS Amplify**: Full AWS integration
   - **EC2**: Self-hosted with PM2 and Nginx
   - **ECS/Fargate**: Containerized deployment

Recommended: Vercel for rapid deployment, AWS Amplify for production.

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

For support, email rmuppidi@mtu.edu or create an issue in this repository.
