"""
Hybrid Multi-Agent Orchestrator for Hackathon MVP

This orchestrator supports TWO modes:
1. Bedrock AgentCore (AWS-native) - uses Bedrock Agent when available
2. Simple Orchestration (fallback) - direct Lambda invocation

The system automatically detects which mode to use based on environment variables.
"""

import json
import os
import boto3
from typing import Dict, Any
from datetime import datetime
from decimal import Decimal

# Initialize AWS clients
lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb')
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

# Environment variables
DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE', 'pa-agent-cases')
USE_BEDROCK_AGENT = os.getenv('USE_BEDROCK_AGENT', 'false').lower() == 'true'
BEDROCK_AGENT_ID = os.getenv('BEDROCK_AGENT_ID')
BEDROCK_AGENT_ALIAS_ID = os.getenv('BEDROCK_AGENT_ALIAS_ID', 'TSTALIASID')


def convert_floats_to_decimal(obj):
    """Convert float types to Decimal for DynamoDB"""
    if isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_floats_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj


def add_timeline_event(case_id: str, event_text: str, status: str = 'info'):
    """Add an event to the case timeline"""
    table = dynamodb.Table(DYNAMODB_TABLE)
    
    try:
        # Get current case to retrieve timeline
        response = table.get_item(Key={'case_id': case_id})
        current_timeline = response.get('Item', {}).get('timeline', [])
        
        # Add new event
        new_event = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'event': event_text,
            'status': status
        }
        current_timeline.append(new_event)
        
        # Update the case with new timeline
        table.update_item(
            Key={'case_id': case_id},
            UpdateExpression='SET timeline = :timeline',
            ExpressionAttributeValues={':timeline': current_timeline}
        )
        print(f"✅ Timeline event added: {event_text}")
    except Exception as e:
        print(f"⚠️ Failed to add timeline event: {str(e)}")


def update_case_status(case_id: str, updates: Dict[str, Any]):
    """Update case in DynamoDB"""
    table = dynamodb.Table(DYNAMODB_TABLE)
    
    # Convert floats to Decimal
    updates = convert_floats_to_decimal(updates)
    
    # Build update expression
    update_expr_parts = []
    expr_attr_values = {}
    expr_attr_names = {}
    
    # List of DynamoDB reserved keywords
    reserved_keywords = ['status', 'timestamp', 'error', 'name', 'data', 'value']
    
    for key, value in updates.items():
        # Handle reserved keywords
        if key.lower() in reserved_keywords:
            attr_name = f'#{key}'
            expr_attr_names[attr_name] = key
            update_expr_parts.append(f'{attr_name} = :{key}')
        else:
            update_expr_parts.append(f'{key} = :{key}')
        expr_attr_values[f':{key}'] = value
    
    update_expression = 'SET ' + ', '.join(update_expr_parts)
    
    kwargs = {
        'Key': {'case_id': case_id},
        'UpdateExpression': update_expression,
        'ExpressionAttributeValues': expr_attr_values
    }
    
    if expr_attr_names:
        kwargs['ExpressionAttributeNames'] = expr_attr_names
    
    table.update_item(**kwargs)


def invoke_lambda(function_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke a Lambda function and return its response"""
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if 'body' in result:
            return json.loads(result['body'])
        return result
        
    except Exception as e:
        print(f"Error invoking {function_name}: {str(e)}")
        return {'success': False, 'error': str(e)}


def orchestrate_with_bedrock_agent(case_id: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orchestrate using Amazon Bedrock AgentCore.
    The agent autonomously decides the workflow.
    """
    print(f"🤖 Using Bedrock Agent: {BEDROCK_AGENT_ID}")
    
    try:
        # Prepare input for agent
        agent_input = f"""
Process prior authorization for case {case_id}.

Patient: {case_data.get('patient_name')}
Diagnosis Codes (ICD-10): {', '.join(case_data.get('ICD10', []))}
Procedure Codes (CPT): {', '.join(case_data.get('CPT', []))}
Diagnosis: {case_data.get('diagnosis')}

Follow the complete workflow:
1. Validate the medical codes
2. Check for required evidence documents
3. Submit to the payer
4. Return the final authorization status

Use all available action groups to complete this task.
"""
        
        # Invoke Bedrock Agent
        response = bedrock_agent_runtime.invoke_agent(
            agentId=BEDROCK_AGENT_ID,
            agentAliasId=BEDROCK_AGENT_ALIAS_ID,
            sessionId=f"session-{case_id}",
            inputText=agent_input
        )
        
        # Parse agent response
        agent_response = ""
        for event in response.get('completion', []):
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    agent_response += chunk['bytes'].decode('utf-8')
        
        print(f"Agent response: {agent_response}")
        
        return {
            'success': True,
            'orchestration_method': 'Amazon Bedrock AgentCore',
            'agent_response': agent_response,
            'agent_id': BEDROCK_AGENT_ID
        }
        
    except Exception as e:
        print(f"❌ Bedrock Agent error: {str(e)}")
        print("Falling back to simple orchestration...")
        return {'success': False, 'error': str(e)}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Hybrid Orchestrator Lambda handler.
    Uses Bedrock Agent if available, falls back to simple orchestration.
    """
    print(f"Orchestrator invoked with event: {json.dumps(event)}")
    print(f"Mode: {'Bedrock Agent' if USE_BEDROCK_AGENT and BEDROCK_AGENT_ID else 'Simple Orchestration'}")
    
    # Extract case_id
    case_id = event.get('case_id')
    if not case_id:
        body = event.get('body')
        if body:
            try:
                body_data = json.loads(body) if isinstance(body, str) else body
                case_id = body_data.get('case_id')
            except json.JSONDecodeError:
                pass
    
    if not case_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Missing case_id in event'})
        }
    
    print(f"Processing case: {case_id}")
    
    try:
        # Fetch case data from DynamoDB
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.get_item(Key={'case_id': case_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'body': json.dumps({'message': f'Case {case_id} not found'})
            }
        
        case_data = response['Item']
        print(f"Case data retrieved for case: {case_id}")
        
        # Update status to processing
        update_case_status(case_id, {
            'status': 'processing',
            'processing_started_at': datetime.utcnow().isoformat()
        })
        
        # TRY BEDROCK AGENT FIRST if enabled
        if USE_BEDROCK_AGENT and BEDROCK_AGENT_ID:
            bedrock_result = orchestrate_with_bedrock_agent(case_id, case_data)
            if bedrock_result.get('success'):
                # Bedrock Agent succeeded - update case and return
                update_case_status(case_id, {
                    'status': 'completed',
                    'orchestration_method': 'Amazon Bedrock AgentCore',
                    'agent_response': bedrock_result.get('agent_response'),
                    'processed_at': datetime.utcnow().isoformat()
                })
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'message': 'Orchestration complete (Bedrock Agent)',
                        'case_id': case_id,
                        'orchestration_method': 'Amazon Bedrock AgentCore',
                        'agent_response': bedrock_result.get('agent_response')
                    })
                }
            else:
                print("⚠️ Bedrock Agent failed, falling back to simple orchestration")
        
        # FALLBACK: Simple orchestration (direct Lambda invocation)
        print("Using simple orchestration mode...")
        add_timeline_event(case_id, "Started prior authorization processing", "processing")
        
        # STEP 1: Code Validation
        print("Step 1: Validating codes...")
        add_timeline_event(case_id, "Validating ICD-10 and CPT codes", "validating")
        validation_payload = {
            'case_id': case_id,
            'extracted_data': {
                'ICD10': case_data.get('ICD10', []),
                'CPT': case_data.get('CPT', []),
                'diagnosis': case_data.get('diagnosis', ''),
                'summary': case_data.get('summary', '')
            }
        }
        
        validation_result = invoke_lambda('pa-code-validator', validation_payload)
        print(f"Validation result: {json.dumps(validation_result)}")
        
        # Check for errors in validation
        if validation_result.get('error') or not validation_result.get('all_valid', True):
            error_msg = validation_result.get('error') or ', '.join(validation_result.get('errors', ['Validation failed']))
            add_timeline_event(case_id, f"❌ Code validation failed: {error_msg}", "error")
            update_case_status(case_id, {
                'status': 'validation_failed',
                'validation_result': validation_result,
                'processed_at': datetime.utcnow().isoformat()
            })
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Code validation failed',
                    'case_id': case_id,
                    'status': 'denied',
                    'reason': error_msg
                })
            }
        
        add_timeline_event(case_id, "✅ Codes validated successfully", "success")
        
        # STEP 2: Evidence Check
        print("Step 2: Checking evidence...")
        add_timeline_event(case_id, "Checking clinical evidence and documentation", "checking")
        evidence_payload = {
            'case_id': case_id,
            'cpt_codes': case_data.get('CPT', []),
            'procedure': case_data.get('CPT', [])
        }
        
        evidence_result = invoke_lambda('pa-evidence-checker', evidence_payload)
        print(f"Evidence result: {json.dumps(evidence_result)}")
        
        if evidence_result.get('has_sufficient_evidence'):
            add_timeline_event(case_id, "✅ Sufficient clinical evidence found", "success")
        else:
            missing = ', '.join(evidence_result.get('missing_documents', []))
            add_timeline_event(case_id, f"⚠️ Missing evidence: {missing}", "warning")
        
        # STEP 3: Submit to Payer with AI review
        print("Step 3: Submitting to payer with AI medical necessity review...")
        add_timeline_event(case_id, "Submitting to payer for AI-powered medical necessity review", "submitting")
        # Get evidence from case_data (extracted from clinical note) or fallback to evidence checker
        extracted_evidence = case_data.get('evidence', {})
        
        payer_payload = {
            'patient': {
                'name': case_data.get('patient_name'),
                'member_id': case_id[:8]  # Use first 8 chars of case_id as member ID
            },
            'diagnosis': case_data.get('ICD10', []),  # List of ICD-10 codes
            'procedures': case_data.get('CPT', []),   # List of CPT codes
            'clinical_summary': case_data.get('summary', '') + ' | Diagnosis: ' + case_data.get('diagnosis', ''),  # Provide context for AI
            'evidence': {
                'pt_notes': extracted_evidence.get('pt_notes', False),
                'clinical_notes': extracted_evidence.get('clinical_notes', True),  # Assume we have clinical note
                'xray': extracted_evidence.get('xray', False),
                'referral': extracted_evidence.get('referral', False)
            },
            'provider': {
                'npi': '1234567890',
                'name': 'Demo Provider'
            }
        }
        
        payer_result = invoke_lambda('pa-mock-payer-api', payer_payload)
        print(f"Payer result: {json.dumps(payer_result)}")
        
        # Determine final status (convert to lowercase for consistency)
        payer_status = payer_result.get('status', 'Pending')
        final_status = payer_status.lower()  # Convert "Approved"/"Denied" to "approved"/"denied"
        
        # Add timeline event based on decision
        if final_status == 'approved':
            auth_number = payer_result.get('authorization_number', 'N/A')
            add_timeline_event(case_id, f"🎉 APPROVED - Authorization #{auth_number}", "approved")
        elif final_status == 'denied':
            reason = payer_result.get('reason', 'Reason not specified')
            add_timeline_event(case_id, f"❌ DENIED - {reason}", "denied")
        else:
            add_timeline_event(case_id, f"⚠️ Payer response: {final_status}", "info")
        
        # Update case with final results
        update_case_status(case_id, {
            'status': final_status,
            'validation_result': validation_result,
            'evidence_result': evidence_result,
            'payer_result': payer_result,
            'authorization_number': payer_result.get('authorization_number'),
            'denial_reason': payer_result.get('reason'),
            'processed_at': datetime.utcnow().isoformat()
        })
        
        print(f"Orchestration complete. Final status: {final_status}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Orchestration complete',
                'case_id': case_id,
                'status': final_status,
                'authorization_number': payer_result.get('authorization_number'),
                'reason': payer_result.get('reason'),
                'next_steps': payer_result.get('next_steps'),
                'required_documents': evidence_result.get('missing_documents', []),
                'validation': validation_result,
                'evidence': evidence_result,
                'payer': payer_result
            })
        }
        
    except Exception as e:
        error_msg = f"Orchestration error: {str(e)}"
        print(f"ERROR: {error_msg}")
        
        # Update case with error status
        try:
            update_case_status(case_id, {
                'status': 'error',
                'error': error_msg,
                'processed_at': datetime.utcnow().isoformat()
            })
        except Exception as update_error:
            print(f"Failed to update error status: {update_error}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Orchestration failed',
                'error': error_msg,
                'case_id': case_id
            })
        }


if __name__ == "__main__":
    # For local testing
    print("=== Testing Simple Orchestrator Locally ===")
    
    event = {
        'case_id': 'test-case-123'
    }
    
    class MockContext:
        request_id = 'local-test-request'
    
    response = lambda_handler(event, MockContext())
    print(f"\nResponse: {json.dumps(response, indent=2)}")
