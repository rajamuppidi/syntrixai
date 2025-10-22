#!/bin/bash

# Deploy Lambda Functions Script
# Packages and deploys all Lambda functions for the PA Agent

set -e

echo "🚀 Deploying Lambda Functions"
echo "=============================="
echo ""

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ Error: .env file not found. Run ./setup_aws.sh first"
    exit 1
fi

# Create deployment directory
DEPLOY_DIR="lambda_deploy"
mkdir -p $DEPLOY_DIR

# Function to deploy a Lambda function
deploy_lambda() {
    FUNCTION_NAME=$1
    SOURCE_FILE=$2
    HANDLER=$3
    
    echo "📦 Packaging ${FUNCTION_NAME}..."
    
    # Create deployment package
    cd $DEPLOY_DIR
    rm -rf package 2>/dev/null || true
    rm -f deployment.zip 2>/dev/null || true
    
    # Install dependencies
    pip install -q -t package/ boto3 requests 2>/dev/null || true
    
    # Copy Lambda function
    cp ../${SOURCE_FILE} package/
    
    # Create zip
    cd package
    zip -q -r ../deployment.zip .
    cd ..
    
    # Deploy or update Lambda
    if aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION 2>/dev/null; then
        echo "   Updating existing function..."
        aws lambda update-function-code \
            --function-name $FUNCTION_NAME \
            --zip-file fileb://deployment.zip \
            --region $AWS_REGION \
            > /dev/null
    else
        echo "   Creating new function..."
        aws lambda create-function \
            --function-name $FUNCTION_NAME \
            --runtime python3.11 \
            --handler $HANDLER \
            --role $LAMBDA_ROLE_ARN \
            --zip-file fileb://deployment.zip \
            --timeout 60 \
            --memory-size 512 \
            --region $AWS_REGION \
            --environment "Variables={DYNAMODB_TABLE=${DYNAMODB_TABLE},S3_CLINICAL_NOTES_BUCKET=${S3_CLINICAL_NOTES_BUCKET},S3_EVIDENCE_BUCKET=${S3_EVIDENCE_BUCKET},BEDROCK_MODEL_ID=${BEDROCK_MODEL_ID}}" \
            > /dev/null
    fi
    
    cd ..
    
    echo "✅ ${FUNCTION_NAME} deployed"
    echo ""
}

# Deploy Extraction Agent
deploy_lambda \
    "pa-extraction-agent" \
    "backend/lambda_functions/extraction_agent.py" \
    "extraction_agent.lambda_handler"

# Deploy Code Validator
deploy_lambda \
    "pa-code-validator" \
    "backend/lambda_functions/code_validator.py" \
    "code_validator.lambda_handler"

# Deploy Evidence Checker
deploy_lambda \
    "pa-evidence-checker" \
    "backend/lambda_functions/evidence_checker.py" \
    "evidence_checker.lambda_handler"

# Deploy Mock Payer API
deploy_lambda \
    "pa-mock-payer-api" \
    "backend/lambda_functions/mock_payer_api.py" \
    "mock_payer_api.lambda_handler"

# Deploy Orchestrator (Bedrock AgentCore)
deploy_lambda \
    "pa-orchestrator" \
    "backend/orchestrator/agent_orchestrator.py" \
    "agent_orchestrator.lambda_handler"

# Deploy Amazon Q Data Source
deploy_lambda \
    "pa-q-data-source" \
    "backend/lambda_functions/q_data_source.py" \
    "q_data_source.lambda_handler"

# Clean up
rm -rf $DEPLOY_DIR

echo "=============================="
echo "✅ All Lambda Functions Deployed!"
echo "=============================="
echo ""
echo "Deployed functions:"
echo "   - pa-extraction-agent"
echo "   - pa-code-validator"
echo "   - pa-evidence-checker"
echo "   - pa-mock-payer-api"
echo "   - pa-orchestrator"
echo "   - pa-q-data-source (Amazon Q)"
echo ""
echo "📝 Next Steps:"
echo "   1. Test extraction: aws lambda invoke --function-name pa-extraction-agent --payload '{\"bucket\":\"${S3_CLINICAL_NOTES_BUCKET}\",\"key\":\"notes/sample_note_1.txt\"}' response.json"
echo "   2. Run dashboard: cd frontend && streamlit run streamlit_app.py"
echo ""

