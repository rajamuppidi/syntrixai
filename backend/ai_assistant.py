"""
AI Assistant powered by Amazon Bedrock Nova Pro
Provides conversational interface to query prior authorization cases
Uses function calling to dynamically query DynamoDB
"""

import boto3
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from decimal import Decimal

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION', 'us-east-1'))
dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'us-east-1'))
lambda_client = boto3.client('lambda', region_name=os.getenv('AWS_REGION', 'us-east-1'))

DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE', 'pa-agent-cases')
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'amazon.nova-pro-v1:0')


def convert_decimals(obj):
    """Convert Decimal types to float/int for JSON serialization"""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    else:
        return obj


# ============================================================================
# TOOL FUNCTIONS - These are the capabilities the AI can use
# ============================================================================

def query_cases(status: Optional[str] = None, 
                patient_name: Optional[str] = None,
                diagnosis: Optional[str] = None,
                limit: int = 10) -> Dict[str, Any]:
    """
    Query prior authorization cases from DynamoDB
    
    Args:
        status: Filter by status (approved, denied, pending, etc.)
        patient_name: Filter by patient name (partial match)
        diagnosis: Filter by diagnosis (partial match)
        limit: Maximum number of results
    
    Returns:
        Dictionary with cases list and metadata
    """
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.scan(Limit=50)  # Scan up to 50, then filter
        cases = response.get('Items', [])
        
        # Apply filters
        filtered_cases = cases
        
        if status:
            filtered_cases = [c for c in filtered_cases 
                            if c.get('status', '').lower() == status.lower()]
        
        if patient_name:
            filtered_cases = [c for c in filtered_cases 
                            if patient_name.lower() in c.get('patient_name', '').lower()]
        
        if diagnosis:
            filtered_cases = [c for c in filtered_cases 
                            if diagnosis.lower() in c.get('diagnosis', '').lower()]
        
        # Sort by created_at descending
        filtered_cases.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Limit results
        result_cases = filtered_cases[:limit]
        
        # Convert Decimals for JSON
        result_cases = convert_decimals(result_cases)
        
        return {
            'success': True,
            'count': len(result_cases),
            'total_matched': len(filtered_cases),
            'cases': result_cases
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'cases': []
        }


def get_case_details(case_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific case
    
    Args:
        case_id: The unique case identifier (UUID) or authorization number (AUTH-*)
    
    Returns:
        Complete case information including timeline and payer response
    """
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        # First, try direct lookup by case_id (UUID)
        try:
            response = table.get_item(Key={'case_id': case_id})
            if 'Item' in response:
                return {
                    'success': True,
                    'case_data': convert_decimals(response['Item'])
                }
        except:
            pass
        
        # If not found and looks like an authorization number, search by auth number
        if case_id.startswith('AUTH-'):
            response = table.scan(
                FilterExpression='authorization_number = :auth_num',
                ExpressionAttributeValues={':auth_num': case_id}
            )
            
            if response.get('Items'):
                return {
                    'success': True,
                    'case_data': convert_decimals(response['Items'][0])
                }
        
        # Not found
        return {
            'success': False,
            'message': f'Case not found with identifier: {case_id}. Please provide a valid case ID (UUID) or authorization number (AUTH-*).',
            'case_data': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'case_data': None
        }


def get_statistics() -> Dict[str, Any]:
    """
    Get overall statistics about prior authorization cases
    
    Returns:
        Statistics including total cases, approval rate, common denials, etc.
    """
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.scan()
        cases = response.get('Items', [])
        
        # Calculate stats
        total = len(cases)
        approved = len([c for c in cases if c.get('status') == 'approved'])
        denied = len([c for c in cases if c.get('status') == 'denied'])
        pending = len([c for c in cases if c.get('status') in ['pending', 'extracted', 'processing']])
        
        # Approval rate
        completed = approved + denied
        approval_rate = (approved / completed * 100) if completed > 0 else 0
        
        # Common denial reasons
        denial_reasons = {}
        for case in cases:
            if case.get('status') == 'denied':
                payer_response = case.get('payer_response', {})
                reason = payer_response.get('reason', 'Unknown')
                denial_reasons[reason] = denial_reasons.get(reason, 0) + 1
        
        # Sort denial reasons
        top_denials = sorted(denial_reasons.items(), key=lambda x: x[1], reverse=True)[:5]
        
        stats = {
            'total_cases': total,
            'approved': approved,
            'denied': denied,
            'pending': pending,
            'approval_rate': round(approval_rate, 1),
            'completion_rate': round((completed / total * 100) if total > 0 else 0, 1),
            'top_denial_reasons': [{'reason': r, 'count': c} for r, c in top_denials]
        }
        
        return {
            'success': True,
            'statistics': stats
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


# ============================================================================
# TOOL DEFINITIONS - Define what the AI can do
# ============================================================================

TOOL_DEFINITIONS = {
    "tools": [
        {
            "toolSpec": {
                "name": "query_cases",
                "description": "Query and search prior authorization cases from the database. Can filter by status, patient name, diagnosis, or get all cases. Use this when user asks about multiple cases, lists, or filtered results.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "description": "Filter by case status",
                                "enum": ["approved", "denied", "pending", "processing", "extracted"]
                            },
                            "patient_name": {
                                "type": "string",
                                "description": "Filter by patient name (partial match supported)"
                            },
                            "diagnosis": {
                                "type": "string",
                                "description": "Filter by diagnosis or condition (partial match supported)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 10
                            }
                        }
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "get_case_details",
                "description": "Get complete details about a specific prior authorization case including patient info, diagnosis, codes, timeline, and payer response. Use this when user asks about a specific case by ID or authorization number. Can search by case ID (UUID) or authorization number (AUTH-*).",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "case_id": {
                                "type": "string",
                                "description": "The unique case identifier (UUID format) or authorization number (AUTH-YYYYMMDD-XXXXXXXX)"
                            }
                        },
                        "required": ["case_id"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "get_statistics",
                "description": "Get overall statistics and metrics about all prior authorization cases including totals, approval rates, denial reasons, and trends. Use this when user asks about counts, rates, statistics, or overall performance.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        }
    ]
}


# Map tool names to functions
TOOL_FUNCTIONS = {
    "query_cases": query_cases,
    "get_case_details": get_case_details,
    "get_statistics": get_statistics
}


# ============================================================================
# AI CONVERSATION HANDLER
# ============================================================================

def chat_with_ai(user_message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
    """
    Have a conversation with the AI assistant
    
    Args:
        user_message: The user's message/question
        conversation_history: Previous messages in the conversation
    
    Returns:
        AI response with answer, tool calls, and updated conversation history
    """
    if conversation_history is None:
        conversation_history = []
    
    # Add user message to history
    conversation_history.append({
        "role": "user",
        "content": [{"text": user_message}]
    })
    
    try:
        # Call Bedrock with conversation history and tools
        response = bedrock_runtime.converse(
            modelId=BEDROCK_MODEL_ID,
            messages=conversation_history,
            toolConfig=TOOL_DEFINITIONS,
            inferenceConfig={
                "temperature": 0.7,
                "maxTokens": 2048
            },
            system=[{
                "text": """You are an AI assistant for a Prior Authorization system. Your role is to help healthcare staff 
understand and manage prior authorization cases.

You have access to tools to query cases, get details, and retrieve statistics. Use these tools to answer questions 
accurately with real data.

When presenting information:
- Be concise but informative
- Use bullet points for lists
- Include relevant case IDs
- Explain denial reasons clearly
- Suggest next actions when appropriate

For denied cases, explain why they were denied and what's missing or needed for approval."""
            }]
        )
        
        # Handle tool use
        stop_reason = response['stopReason']
        
        if stop_reason == 'tool_use':
            # AI wants to call a tool
            assistant_message = response['output']['message']
            conversation_history.append(assistant_message)
            
            # Execute requested tools
            tool_results = []
            
            for content in assistant_message['content']:
                if 'toolUse' in content:
                    tool_use = content['toolUse']
                    tool_name = tool_use['name']
                    tool_input = tool_use['input']
                    tool_use_id = tool_use['toolUseId']
                    
                    print(f"🔧 AI calling tool: {tool_name} with {tool_input}")
                    
                    # Execute the tool function
                    if tool_name in TOOL_FUNCTIONS:
                        tool_function = TOOL_FUNCTIONS[tool_name]
                        tool_result = tool_function(**tool_input)
                    else:
                        tool_result = {"error": f"Unknown tool: {tool_name}"}
                    
                    # Add tool result to history
                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tool_use_id,
                            "content": [{"json": tool_result}]
                        }
                    })
            
            # Add tool results to conversation
            conversation_history.append({
                "role": "user",
                "content": tool_results
            })
            
            # Get AI's final response after tool use
            final_response = bedrock_runtime.converse(
                modelId=BEDROCK_MODEL_ID,
                messages=conversation_history,
                toolConfig=TOOL_DEFINITIONS,
                inferenceConfig={"temperature": 0.7, "maxTokens": 2048}
            )
            
            final_message = final_response['output']['message']
            conversation_history.append(final_message)
            
            # Extract text response
            ai_response = ""
            for content in final_message['content']:
                if 'text' in content:
                    ai_response += content['text']
            
            return {
                'success': True,
                'response': ai_response,
                'conversation_history': conversation_history,
                'tools_used': [t['toolResult']['toolUseId'] for t in tool_results]
            }
        
        else:
            # Direct response without tool use
            assistant_message = response['output']['message']
            conversation_history.append(assistant_message)
            
            # Extract text response
            ai_response = ""
            for content in assistant_message['content']:
                if 'text' in content:
                    ai_response += content['text']
            
            return {
                'success': True,
                'response': ai_response,
                'conversation_history': conversation_history,
                'tools_used': []
            }
    
    except Exception as e:
        print(f"Error in AI chat: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'response': f"I encountered an error: {str(e)}",
            'conversation_history': conversation_history,
            'error': str(e)
        }


# For testing
if __name__ == '__main__':
    print("Testing AI Assistant...")
    
    # Test query
    result = chat_with_ai("How many cases are denied?")
    print(f"\nAI Response: {result['response']}")
    print(f"Tools used: {result.get('tools_used', [])}")

