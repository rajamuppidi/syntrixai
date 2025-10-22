"""
Lambda function to retrieve case data from DynamoDB for Bedrock Agent
"""
import json
import boto3
import os
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE', 'pa-agent-cases')
table = dynamodb.Table(table_name)

def decimal_default(obj):
    """Helper to convert Decimal to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    """
    Retrieve case data from DynamoDB
    
    Expected input:
    {
        "case_id": "uuid-string"
    }
    
    Returns:
    {
        "success": true/false,
        "case_data": {...} or null,
        "message": "..."
    }
    """
    print(f"📥 GetCaseData invoked with event: {json.dumps(event)}")
    
    try:
        # Parse input based on invocation source
        case_id = None
        
        # Check if this is a Bedrock Agent invocation
        if 'parameters' in event and isinstance(event['parameters'], list):
            # Bedrock Agent format: parameters is a list of {name, type, value}
            print("🤖 Bedrock Agent invocation detected")
            for param in event['parameters']:
                if param.get('name') == 'case_id':
                    case_id = param.get('value')
                    break
        else:
            # Direct Lambda invocation or other formats
            case_id = event.get('case_id') or event.get('caseId')
        
        if not case_id:
            error_response = {
                'success': False,
                'case_data': None,
                'message': 'Missing required parameter: case_id'
            }
            
            # Return in Bedrock format if invoked by agent
            if 'agent' in event:
                return {
                    'messageVersion': '1.0',
                    'response': {
                        'actionGroup': event.get('actionGroup'),
                        'function': event.get('function'),
                        'functionResponse': {
                            'responseBody': {
                                'TEXT': {
                                    'body': json.dumps(error_response)
                                }
                            }
                        }
                    }
                }
            return error_response
        
        print(f"🔍 Retrieving case: {case_id}")
        
        # Get case from DynamoDB
        response = table.get_item(Key={'case_id': case_id})
        
        if 'Item' not in response:
            error_response = {
                'success': False,
                'case_data': None,
                'message': f'Case not found: {case_id}'
            }
            
            # Return in Bedrock format if invoked by agent
            if 'agent' in event:
                return {
                    'messageVersion': '1.0',
                    'response': {
                        'actionGroup': event.get('actionGroup'),
                        'function': event.get('function'),
                        'functionResponse': {
                            'responseBody': {
                                'TEXT': {
                                    'body': json.dumps(error_response)
                                }
                            }
                        }
                    }
                }
            return error_response
        
        item = response['Item']
        
        # Format case data for the agent
        case_data = {
            'case_id': item.get('case_id'),
            'patient_name': item.get('patient_name'),
            'diagnosis': item.get('diagnosis'),
            'icd10_codes': item.get('icd10_codes', []),
            'cpt_codes': item.get('cpt_codes', []),
            'status': item.get('status'),
            'created_at': item.get('created_at'),
            'summary': item.get('summary'),
            'clinical_note_s3': item.get('clinical_note_s3'),
            'evidence': item.get('evidence', {}),
            'authorization_number': item.get('authorization_number'),
            'payer_response': item.get('payer_response', {})
        }
        
        # Remove None values
        case_data = {k: v for k, v in case_data.items() if v is not None}
        
        print(f"✅ Case data retrieved successfully")
        print(f"📊 Case data: {json.dumps(case_data, default=decimal_default)}")
        
        success_response = {
            'success': True,
            'case_data': case_data,
            'message': f'Case data retrieved for {case_data.get("patient_name", "patient")}'
        }
        
        # Return in Bedrock format if invoked by agent
        if 'agent' in event:
            return {
                'messageVersion': '1.0',
                'response': {
                    'actionGroup': event.get('actionGroup'),
                    'function': event.get('function'),
                    'functionResponse': {
                        'responseBody': {
                            'TEXT': {
                                'body': json.dumps(success_response, default=decimal_default)
                            }
                        }
                    }
                }
            }
        
        return success_response
        
    except Exception as e:
        print(f"❌ Error retrieving case data: {str(e)}")
        import traceback
        traceback.print_exc()
        
        error_response = {
            'success': False,
            'case_data': None,
            'message': f'Error retrieving case data: {str(e)}'
        }
        
        # Return in Bedrock format if invoked by agent
        if 'agent' in event:
            return {
                'messageVersion': '1.0',
                'response': {
                    'actionGroup': event.get('actionGroup'),
                    'function': event.get('function'),
                    'functionResponse': {
                        'responseBody': {
                            'TEXT': {
                                'body': json.dumps(error_response)
                            }
                        }
                    }
                }
            }
        
        return error_response

