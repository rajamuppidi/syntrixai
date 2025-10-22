"""
Bedrock Extraction Agent
Extracts ICD-10 codes, CPT codes, and clinical summary from uploaded notes
Supports both plain text clinical notes and FHIR R4 bundles
"""

import boto3
import json
import uuid
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path for FHIR modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION', 'us-east-1'))
dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))
s3_client = boto3.client('s3')

DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE', 'pa-cases')
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'amazon.nova-pro-v1:0')

# Try to import FHIR parser (may not be available in Lambda without layer)
try:
    from fhir.fhir_parser import FHIRParser
    FHIR_AVAILABLE = True
except ImportError:
    FHIR_AVAILABLE = False
    print("FHIR parser not available, will only process plain text")


def extract_text_from_s3(bucket: str, key: str) -> str:
    """Download and read clinical note from S3"""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        return content
    except Exception as e:
        print(f"Error reading from S3: {str(e)}")
        raise


def is_fhir_bundle(content: str) -> bool:
    """Check if content is a FHIR bundle"""
    try:
        data = json.loads(content)
        return (isinstance(data, dict) and 
                data.get('resourceType') == 'Bundle' and
                'entry' in data)
    except:
        return False


def parse_fhir_input(content: str) -> Dict[str, Any]:
    """Parse FHIR bundle and extract PA data"""
    if not FHIR_AVAILABLE:
        raise Exception("FHIR parser not available")
    
    try:
        fhir_data = json.loads(content)
        parser = FHIRParser()
        return parser.parse_bundle(fhir_data)
    except Exception as e:
        raise Exception(f"Error parsing FHIR bundle: {str(e)}")


def call_bedrock_extraction(clinical_note: str) -> Dict[str, Any]:
    """Use Bedrock Nova Pro to extract structured data from clinical note"""
    
    prompt = f"""You are a medical coding AI assistant. Extract the following information from the clinical note below:

1. Patient name
2. Primary diagnosis (in plain language)
3. ICD-10 codes (as an array)
4. CPT procedure codes (as an array)
5. Clinical summary (1-2 sentences explaining why the procedure is needed)
6. Evidence/Documentation flags - Check if the clinical note MENTIONS having or attaching these documents:
   - pt_notes: Physical therapy notes/records (look for "PT notes", "physical therapy", "therapy progress notes")
   - xray: X-ray or imaging results (look for "X-ray", "imaging", "radiograph")
   - clinical_notes: Clinical examination notes (look for "clinical notes", "exam findings", "physical examination")
   - referral: Referral from another provider (look for "referral", "referred by")

Clinical Note:
{clinical_note}

Return ONLY valid JSON with exactly these keys: patient_name, diagnosis, ICD10, CPT, summary, evidence
Do not include any explanatory text, just the JSON object.

Example format:
{{
  "patient_name": "John Smith",
  "diagnosis": "Right knee pain",
  "ICD10": ["M25.561"],
  "CPT": ["73721"],
  "summary": "MRI needed for persistent right knee pain after 6 weeks of conservative treatment",
  "evidence": {{
    "pt_notes": true,
    "xray": false,
    "clinical_notes": true,
    "referral": true
  }}
}}
"""

    # Construct request body based on model type
    if 'nova' in BEDROCK_MODEL_ID.lower():
        # Nova Pro format
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "temperature": 0.3,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
    else:
        # Nova format (and other models)
        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ],
            "inferenceConfig": {
                "temperature": 0.3,
                "maxTokens": 2000
            }
        }

    try:
        # Invoke Bedrock model
        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(request_body)
        )

        # Parse response
        response_body = json.loads(response['body'].read())
        
        # Extract the text content based on model type
        if 'nova' in BEDROCK_MODEL_ID.lower():
            content = response_body['content'][0]['text']
        else:
            # Nova and other models
            content = response_body['output']['message']['content'][0]['text']
        
        # Parse the JSON from the response
        # Nova Pro might wrap it in markdown code blocks, so we need to clean it
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]  # Remove ```json
        if content.startswith('```'):
            content = content[3:]  # Remove ```
        if content.endswith('```'):
            content = content[:-3]  # Remove trailing ```
        content = content.strip()
        
        extracted_data = json.loads(content)
        
        return extracted_data
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from Bedrock response: {str(e)}")
        print(f"Raw content: {content}")
        # Return a default structure if parsing fails
        return {
            "patient_name": "Unknown",
            "diagnosis": "Extraction failed",
            "ICD10": [],
            "CPT": [],
            "summary": "Failed to extract structured data"
        }
    except Exception as e:
        print(f"Error calling Bedrock: {str(e)}")
        raise


def save_to_dynamodb(case_id: str, extracted_data: Dict, s3_key: str) -> None:
    """Save extracted case data to DynamoDB"""
    
    table = dynamodb.Table(DYNAMODB_TABLE)
    
    item = {
        'case_id': case_id,
        'patient_name': extracted_data.get('patient_name', 'Unknown'),
        'diagnosis': extracted_data.get('diagnosis', ''),
        'ICD10': extracted_data.get('ICD10', []),
        'CPT': extracted_data.get('CPT', []),
        'summary': extracted_data.get('summary', ''),
        'evidence': extracted_data.get('evidence', {}),  # Store evidence flags
        'status': 'extracted',
        's3_key': s3_key,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'timeline': [
            {
                'timestamp': datetime.now().isoformat(),
                'event': 'Clinical note uploaded and extracted',
                'status': 'extracted'
            }
        ]
    }
    
    try:
        table.put_item(Item=item)
        print(f"Saved case {case_id} to DynamoDB")
    except Exception as e:
        print(f"Error saving to DynamoDB: {str(e)}")
        raise


def lambda_handler(event, context):
    """
    Lambda handler for extraction agent
    
    Expected event format:
    {
        "bucket": "pa-agent-clinical-notes-xxx",
        "key": "notes/patient123.txt"
    }
    """
    
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract S3 location from event
        # Support both direct invocation and S3 trigger
        if 'Records' in event:
            # S3 trigger format
            bucket = event['Records'][0]['s3']['bucket']['name']
            key = event['Records'][0]['s3']['object']['key']
        else:
            # Direct invocation format
            bucket = event.get('bucket')
            key = event.get('key')
        
        if not bucket or not key:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing bucket or key parameter'})
            }
        
        # Generate unique case ID
        case_id = str(uuid.uuid4())
        
        # Step 1: Read clinical note from S3
        print(f"Reading clinical note from s3://{bucket}/{key}")
        clinical_note = extract_text_from_s3(bucket, key)
        
        # Step 2: Check if input is FHIR or plain text
        if is_fhir_bundle(clinical_note):
            print("Detected FHIR bundle input")
            if not FHIR_AVAILABLE:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'FHIR parser not available in this deployment'})
                }
            extracted_data = parse_fhir_input(clinical_note)
            print(f"Extracted from FHIR: {json.dumps(extracted_data, default=str)}")
        else:
            # Plain text - use Bedrock extraction
            print(f"Detected plain text input, using Bedrock model: {BEDROCK_MODEL_ID}")
            extracted_data = call_bedrock_extraction(clinical_note)
        
        # Step 3: Save to DynamoDB
        print(f"Saving case {case_id} to DynamoDB")
        save_to_dynamodb(case_id, extracted_data, f"s3://{bucket}/{key}")
        
        # Return success response
        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'case_id': case_id,
                'extracted_data': extracted_data,
                'message': 'Clinical note extracted successfully'
            })
        }
        
        print(f"Extraction complete for case {case_id}")
        return response
        
    except Exception as e:
        print(f"Error in extraction agent: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to extract clinical note'
            })
        }


# For local testing
if __name__ == '__main__':
    test_event = {
        'bucket': 'pa-agent-clinical-notes-test',
        'key': 'notes/test_note.txt'
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))

