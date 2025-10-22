#!/bin/bash

# Deploy FHIR-enabled Lambda functions
# This script packages the FHIR parser with the extraction agent

set -e

# Load environment
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

AWS_REGION=${AWS_REGION:-us-east-1}

echo "🚀 Deploying FHIR-enabled Lambda functions..."

# Create temp directory for packaging
TEMP_DIR=$(mktemp -d)
echo "📦 Using temp directory: $TEMP_DIR"

# Package extraction agent with FHIR modules
echo ""
echo "📦 Packaging pa-extraction-agent with FHIR support..."
mkdir -p $TEMP_DIR/extraction
cp backend/lambda_functions/extraction_agent.py $TEMP_DIR/extraction/
mkdir -p $TEMP_DIR/extraction/fhir
cp backend/fhir/*.py $TEMP_DIR/extraction/fhir/

cd $TEMP_DIR/extraction
zip -q -r extraction_agent.zip .
cd -

# Update Lambda function
echo "🔼 Updating pa-extraction-agent..."
aws lambda update-function-code \
    --function-name pa-extraction-agent \
    --zip-file fileb://$TEMP_DIR/extraction/extraction_agent.zip \
    --region $AWS_REGION > /dev/null

echo "✅ pa-extraction-agent updated with FHIR support"

# Clean up
rm -rf $TEMP_DIR

echo ""
echo "✅ FHIR-enabled Lambda deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Test with FHIR bundle: Upload sample_data/fhir/lumbar_mri_request.json"
echo "2. System will auto-detect FHIR vs plain text"
echo "3. FHIR bundles are parsed directly (no AI inference needed)"

