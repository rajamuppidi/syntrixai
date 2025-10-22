"""
Amazon Q Business Data Source Lambda
Provides DynamoDB case data to Amazon Q for staff assistant queries
"""

import json
import os
import boto3
from datetime import datetime
from typing import Dict, Any, List
from decimal import Decimal

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))
DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE', 'pa-agent-cases')


def convert_decimals(obj):
    """Convert Decimal types to float/int for JSON serialization"""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        # Convert to int if it's a whole number, otherwise float
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj


def get_case_by_id(case_id: str) -> Dict[str, Any]:
    """Retrieve a specific case by ID"""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.get_item(Key={'case_id': case_id})
        
        if 'Item' in response:
            return {
                'success': True,
                'case': response['Item']
            }
        else:
            return {
                'success': False,
                'error': f'Case {case_id} not found'
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_recent_cases(limit: int = 10) -> Dict[str, Any]:
    """Get most recent cases"""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.scan(Limit=limit)
        
        cases = response.get('Items', [])
        # Sort by created_at descending
        cases.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return {
            'success': True,
            'cases': cases[:limit]
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_denied_cases() -> Dict[str, Any]:
    """Get all denied cases"""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.scan(
            FilterExpression='#status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':status': 'denied'}
        )
        
        return {
            'success': True,
            'cases': response.get('Items', [])
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_pending_cases() -> Dict[str, Any]:
    """Get cases awaiting action"""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.scan(
            FilterExpression='#status IN (:pending, :extracted, :validating)',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':pending': 'pending',
                ':extracted': 'extracted',
                ':validating': 'validating'
            }
        )
        
        return {
            'success': True,
            'cases': response.get('Items', [])
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_case_statistics() -> Dict[str, Any]:
    """Get overall statistics"""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.scan()
        
        cases = response.get('Items', [])
        
        stats = {
            'total_cases': len(cases),
            'approved': len([c for c in cases if c.get('status') == 'approved']),
            'denied': len([c for c in cases if c.get('status') == 'denied']),
            'pending': len([c for c in cases if c.get('status') in ['pending', 'extracted', 'validating']]),
            'approval_rate': 0
        }
        
        if stats['total_cases'] > 0:
            completed = stats['approved'] + stats['denied']
            if completed > 0:
                stats['approval_rate'] = round((stats['approved'] / completed) * 100, 1)
        
        return {
            'success': True,
            'statistics': stats
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def format_case_for_q(case: Dict[str, Any]) -> str:
    """Format case data into natural language for Q"""
    patient = case.get('patient_name', 'Unknown')
    diagnosis = case.get('diagnosis', 'Unknown')
    status = case.get('status', 'unknown')
    icd10 = ', '.join(case.get('ICD10', []))
    cpt = ', '.join(case.get('CPT', []))
    
    text = f"Case {case.get('case_id', 'Unknown')}: "
    text += f"Patient {patient}, Diagnosis: {diagnosis} (ICD-10: {icd10}), "
    text += f"Procedures: CPT {cpt}, Status: {status}"
    
    # Add denial reason if denied
    payer_response = case.get('payer_response', {})
    if status == 'denied' and payer_response.get('reason'):
        text += f", Denial Reason: {payer_response['reason']}"
    
    # Add missing documents if any
    evidence = case.get('evidence_check', {})
    if evidence.get('missing_docs'):
        text += f", Missing Documents: {', '.join(evidence['missing_docs'])}"
    
    return text


def lambda_handler(event, context):
    """
    Lambda handler for Amazon Q data source
    
    Expected event:
    {
        "action": "get_case|recent_cases|denied_cases|pending_cases|statistics",
        "case_id": "optional-case-id",
        "limit": 10
    }
    """
    
    print(f"Q Data Source invoked: {json.dumps(event)}")
    
    try:
        action = event.get('action', 'recent_cases')
        
        if action == 'get_case':
            case_id = event.get('case_id')
            if not case_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Missing case_id parameter'})
                }
            result = get_case_by_id(case_id)
            
        elif action == 'recent_cases':
            limit = event.get('limit', 10)
            result = get_recent_cases(limit)
            
        elif action == 'denied_cases':
            result = get_denied_cases()
            
        elif action == 'pending_cases':
            result = get_pending_cases()
            
        elif action == 'statistics':
            result = get_case_statistics()
            
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unknown action: {action}'})
            }
        
        # Format cases for Q if present
        if result.get('success') and 'cases' in result:
            formatted_cases = [format_case_for_q(case) for case in result['cases']]
            result['formatted_text'] = '\n\n'.join(formatted_cases)
        elif result.get('success') and 'case' in result:
            result['formatted_text'] = format_case_for_q(result['case'])
        
        # Convert all Decimal types to float/int for JSON serialization
        result = convert_decimals(result)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error in Q data source: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }


# For local testing
if __name__ == '__main__':
    # Test statistics
    print("=== Testing Statistics ===")
    test_event = {'action': 'statistics'}
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))
    
    # Test recent cases
    print("\n=== Testing Recent Cases ===")
    test_event = {'action': 'recent_cases', 'limit': 5}
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))

