"""
Evidence Checker Agent
Validates that required supporting documents exist for a PA request
"""

import boto3
import json
import os
from typing import Dict, List, Any
from datetime import datetime
from decimal import Decimal

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))

EVIDENCE_BUCKET = os.getenv('S3_EVIDENCE_BUCKET', 'pa-agent-evidence-docs')
DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE', 'pa-cases')


# Define evidence requirements by CPT code
EVIDENCE_REQUIREMENTS = {
    '73721': ['pt_notes', 'clinical_summary'],  # MRI knee
    '73722': ['pt_notes', 'clinical_summary'],  # MRI joint
    '70551': ['clinical_notes', 'referral'],    # MRI brain
    '99241': ['referral', 'medical_records'],   # Consultation
    '27447': ['xray', 'pt_notes', 'clinical_notes'],  # Knee replacement
    '29881': ['pt_notes', 'mri_report'],        # Arthroscopy
}


def get_required_documents(cpt_codes: List[str]) -> List[str]:
    """Determine required documents based on procedure codes"""
    required = set()
    
    for cpt in cpt_codes:
        if cpt in EVIDENCE_REQUIREMENTS:
            required.update(EVIDENCE_REQUIREMENTS[cpt])
        else:
            # Default requirements for unknown procedures
            required.add('clinical_notes')
    
    return list(required)


def check_document_exists(case_id: str, doc_type: str) -> bool:
    """Check if a specific document exists in S3"""
    
    # Possible file extensions
    extensions = ['.pdf', '.txt', '.jpg', '.png', '.dcm']
    
    for ext in extensions:
        key = f"evidence/{case_id}/{doc_type}{ext}"
        try:
            s3_client.head_object(Bucket=EVIDENCE_BUCKET, Key=key)
            print(f"Found document: {key}")
            return True
        except s3_client.exceptions.ClientError:
            continue
    
    print(f"Document not found: {doc_type} for case {case_id}")
    return False


def verify_evidence(case_id: str, cpt_codes: List[str]) -> Dict[str, Any]:
    """Verify all required evidence documents exist"""
    
    required_docs = get_required_documents(cpt_codes)
    
    found_docs = []
    missing_docs = []
    
    for doc_type in required_docs:
        if check_document_exists(case_id, doc_type):
            found_docs.append(doc_type)
        else:
            missing_docs.append(doc_type)
    
    is_complete = len(missing_docs) == 0
    
    # Calculate percentage and convert to Decimal for DynamoDB
    if required_docs:
        percentage = Decimal(str(round((len(found_docs) / len(required_docs) * 100), 2)))
    else:
        percentage = Decimal('0')
    
    result = {
        'case_id': case_id,
        'required_docs': required_docs,
        'found_docs': found_docs,
        'missing_docs': missing_docs,
        'is_complete': is_complete,
        'completeness_percentage': percentage,
        'checked_at': datetime.now().isoformat(),
        'has_sufficient_evidence': is_complete  # Add this for orchestrator
    }
    
    return result


def update_case_in_dynamodb(case_id: str, evidence_result: Dict) -> None:
    """Update case record with evidence check results"""
    
    table = dynamodb.Table(DYNAMODB_TABLE)
    
    try:
        # Get existing case
        response = table.get_item(Key={'case_id': case_id})
        case = response.get('Item', {})
        
        # Add timeline event
        timeline = case.get('timeline', [])
        timeline.append({
            'timestamp': datetime.now().isoformat(),
            'event': f"Evidence check: {len(evidence_result['found_docs'])} of {len(evidence_result['required_docs'])} documents found",
            'status': 'evidence_checked'
        })
        
        # Update case
        table.update_item(
            Key={'case_id': case_id},
            UpdateExpression='SET evidence_check = :evidence, timeline = :timeline, updated_at = :updated',
            ExpressionAttributeValues={
                ':evidence': evidence_result,
                ':timeline': timeline,
                ':updated': datetime.now().isoformat()
            }
        )
        
        print(f"Updated case {case_id} with evidence check results")
        
    except Exception as e:
        print(f"Error updating DynamoDB: {str(e)}")
        raise


def lambda_handler(event, context):
    """
    Lambda handler for evidence checker
    
    Expected event:
    {
        "case_id": "uuid",
        "cpt_codes": ["73721", "99213"]
    }
    """
    
    print(f"Received event: {json.dumps(event)}")
    
    try:
        case_id = event.get('case_id')
        cpt_codes = event.get('cpt_codes', [])
        
        if not case_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing case_id parameter'})
            }
        
        # If CPT codes not provided, get from DynamoDB
        if not cpt_codes:
            table = dynamodb.Table(DYNAMODB_TABLE)
            response = table.get_item(Key={'case_id': case_id})
            case = response.get('Item', {})
            cpt_codes = case.get('CPT', [])
        
        # Verify evidence
        print(f"Checking evidence for case {case_id} with CPT codes: {cpt_codes}")
        evidence_result = verify_evidence(case_id, cpt_codes)
        
        # Update DynamoDB
        update_case_in_dynamodb(case_id, evidence_result)
        
        # Convert Decimal to float for JSON serialization
        def decimal_to_float(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            return obj
        
        # Convert evidence_result for JSON serialization
        json_safe_result = {k: decimal_to_float(v) if isinstance(v, Decimal) else v 
                           for k, v in evidence_result.items()}
        
        # Return result
        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(json_safe_result)
        }
        
        print(f"Evidence check complete: {evidence_result['is_complete']}")
        return response
        
    except Exception as e:
        print(f"Error in evidence checker: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to check evidence'
            })
        }


# For local testing
if __name__ == '__main__':
    test_event = {
        'case_id': 'test-case-123',
        'cpt_codes': ['73721']
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))

