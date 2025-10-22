#!/bin/bash

# AWS Prior Authorization Agent - Setup Script
# This script sets up all required AWS infrastructure

set -e  # Exit on error

echo "🏥 AI Prior Authorization Agent - AWS Setup"
echo "============================================"
echo ""

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
PROJECT_NAME="pa-agent"

echo "AWS Region: $AWS_REGION"
echo "AWS Account: $AWS_ACCOUNT_ID"
echo ""

# Step 1: Create S3 Buckets
echo "📦 Step 1: Creating S3 Buckets..."

CLINICAL_NOTES_BUCKET="${PROJECT_NAME}-clinical-notes-${AWS_ACCOUNT_ID}"
EVIDENCE_BUCKET="${PROJECT_NAME}-evidence-docs-${AWS_ACCOUNT_ID}"

aws s3 mb "s3://${CLINICAL_NOTES_BUCKET}" --region $AWS_REGION 2>/dev/null || echo "Bucket already exists: ${CLINICAL_NOTES_BUCKET}"
aws s3 mb "s3://${EVIDENCE_BUCKET}" --region $AWS_REGION 2>/dev/null || echo "Bucket already exists: ${EVIDENCE_BUCKET}"

echo "✅ S3 buckets created"
echo "   - ${CLINICAL_NOTES_BUCKET}"
echo "   - ${EVIDENCE_BUCKET}"
echo ""

# Step 2: Create DynamoDB Table
echo "📊 Step 2: Creating DynamoDB Table..."

TABLE_NAME="${PROJECT_NAME}-cases"

aws dynamodb create-table \
    --table-name $TABLE_NAME \
    --attribute-definitions AttributeName=case_id,AttributeType=S \
    --key-schema AttributeName=case_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region $AWS_REGION \
    2>/dev/null || echo "Table already exists: ${TABLE_NAME}"

echo "✅ DynamoDB table created: ${TABLE_NAME}"
echo ""

# Step 3: Create IAM Role for Lambda
echo "🔐 Step 3: Creating IAM Role for Lambda..."

ROLE_NAME="${PROJECT_NAME}-lambda-role"

# Create trust policy
cat > /tmp/trust-policy.json <<EOF
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
EOF

# Create role
aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document file:///tmp/trust-policy.json \
    2>/dev/null || echo "Role already exists: ${ROLE_NAME}"

# Attach policies
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

echo "✅ IAM role created: ${ROLE_NAME}"
echo ""

# Wait for role to be available
echo "⏳ Waiting for IAM role to propagate..."
sleep 10

# Step 4: Create .env file
echo "⚙️  Step 4: Creating .env file..."

cat > .env <<EOF
# AWS Configuration
AWS_REGION=$AWS_REGION
AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID

# S3 Buckets
S3_CLINICAL_NOTES_BUCKET=$CLINICAL_NOTES_BUCKET
S3_EVIDENCE_BUCKET=$EVIDENCE_BUCKET

# DynamoDB
DYNAMODB_TABLE=$TABLE_NAME

# Bedrock
BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
BEDROCK_REGION=$AWS_REGION

# Lambda Role
LAMBDA_ROLE_ARN=arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}
EOF

echo "✅ .env file created"
echo ""

# Step 5: Upload sample data to S3
echo "📄 Step 5: Uploading sample clinical notes..."

if [ -f "sample_data/clinical_note_1.txt" ]; then
    aws s3 cp sample_data/clinical_note_1.txt "s3://${CLINICAL_NOTES_BUCKET}/notes/sample_note_1.txt"
    aws s3 cp sample_data/clinical_note_2.txt "s3://${CLINICAL_NOTES_BUCKET}/notes/sample_note_2.txt" 2>/dev/null || true
    echo "✅ Sample data uploaded"
else
    echo "⚠️  Sample data not found (optional)"
fi
echo ""

# Summary
echo "============================================"
echo "✅ AWS Setup Complete!"
echo "============================================"
echo ""
echo "📝 Next Steps:"
echo "   1. Deploy Lambda functions: ./deploy_lambdas.sh"
echo "   2. Request Bedrock model access in AWS Console"
echo "   3. Run dashboard: cd frontend && streamlit run streamlit_app.py"
echo ""
echo "🔗 Resources Created:"
echo "   - S3 Bucket: ${CLINICAL_NOTES_BUCKET}"
echo "   - S3 Bucket: ${EVIDENCE_BUCKET}"
echo "   - DynamoDB Table: ${TABLE_NAME}"
echo "   - IAM Role: ${ROLE_NAME}"
echo ""
echo "⚠️  IMPORTANT: Request Bedrock model access before deploying:"
echo "   AWS Console → Bedrock → Model Access → Request Access to Amazon Nova Pro"
echo ""

