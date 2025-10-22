"""
AI-Powered Payer API
Uses Amazon Bedrock to perform intelligent medical necessity review
Analyzes clinical context to make authorization decisions with reasoning
"""

import json
import uuid
import os
import boto3
from datetime import datetime
from typing import Dict, Any

# Initialize Bedrock client
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION', 'us-east-1'))
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'amazon.nova-pro-v1:0')


def ai_medical_necessity_review(pas_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use Amazon Bedrock AI to perform intelligent medical necessity review
    Analyzes clinical context, appropriateness, and provides reasoning
    """
    
    diagnosis_codes = pas_request.get('diagnosis', [])
    procedure_codes = pas_request.get('procedures', [])
    evidence = pas_request.get('evidence', {})
    patient_info = pas_request.get('patient', {})
    clinical_summary = pas_request.get('clinical_summary', '')
    
    # Build comprehensive prompt for AI review
    prompt = f"""You are a medical necessity reviewer for a health insurance company. 
Analyze this prior authorization request and determine if it should be APPROVED or DENIED.

AUTHORIZATION REQUEST:
- Patient: {patient_info.get('name', 'Unknown')}
- Diagnosis Codes (ICD-10): {', '.join(diagnosis_codes)}
- Procedure Codes (CPT): {', '.join(procedure_codes)}
- Clinical Summary: {clinical_summary if clinical_summary else 'Not provided'}

SUPPORTING DOCUMENTATION:
- Physical Therapy Notes: {'Yes' if evidence.get('pt_notes') else 'No'}
- Clinical Notes: {'Yes' if evidence.get('clinical_notes') else 'No'}
- X-ray/Imaging: {'Yes' if evidence.get('xray') else 'No'}
- Referral: {'Yes' if evidence.get('referral') else 'No'}

⚠️ CRITICAL REVIEW CRITERIA (Check in this order):

1. CODE ACCURACY & APPROPRIATENESS:
   - Do the ICD-10 diagnosis codes accurately match the clinical summary?
   - Do the CPT procedure codes match the diagnosed condition?
   - Are there any obvious mismatches? (e.g., knee procedure codes for shoulder problems, cardiac codes for musculoskeletal issues, wrong body part codes)
   - Are the codes clinically appropriate for the described condition?
   - ⚠️ If you detect ANY code mismatch or inappropriate code usage, this is a STRONG reason for DENIAL.

2. CLINICAL CONTEXT VALIDATION:
   - Does the clinical summary support the diagnosis codes provided?
   - Does the requested procedure make sense for the diagnosis?
   - Is this the standard of care for this condition?

3. MEDICAL NECESSITY:
   - Is this procedure medically necessary for the given diagnosis?
   - Has conservative treatment been attempted (if applicable)?
   - Are there red flag symptoms requiring immediate intervention?

4. DOCUMENTATION:
   - Is there sufficient documentation to support medical necessity?
   - Are there any missing critical documents?

5. EVIDENCE-BASED GUIDELINES:
   - Does this align with clinical practice guidelines?
   - Is this cost-effective and appropriate?

EXAMPLES OF CODE MISMATCHES TO WATCH FOR:
- Shoulder pain (M25.511) + Knee MRI (73721) = DENY (wrong body part)
- Lower back pain (M54.5) + Cardiac stress test = DENY (wrong system)
- Diabetes diagnosis (E11.x) + Orthopedic procedure = DENY (unless clinically justified)
- Minor sprain + Major surgery code = DENY (overtreatment)

Analyze the request and respond with a JSON object ONLY (no other text):
{{
  "decision": "APPROVED" or "DENIED",
  "confidence": "high" or "medium" or "low",
  "reasoning": "Clear explanation of why this decision was made, HIGHLIGHTING ANY CODE MISMATCHES (3-4 sentences)",
  "medical_necessity": "Explanation of medical necessity (or lack thereof)",
  "code_appropriateness": "Analysis of whether the codes match the clinical context",
  "missing_elements": ["list", "of", "missing", "items", "or", "incorrect", "codes"] or [],
  "required_actions": "What the provider should do to get approval (if denied - e.g., 'Resubmit with correct CPT code for shoulder, not knee')",
  "clinical_guideline_reference": "Relevant clinical practice guideline or standard of care"
}}

Be vigilant and thorough. Code accuracy is paramount. If codes don't match the clinical context, DENY and explain why."""

    try:
        # Call Bedrock for AI review
        if 'nova' in BEDROCK_MODEL_ID.lower():
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1500,
                "temperature": 0.2,
                "messages": [{
                    "role": "user",
                    "content": prompt
                }]
            }
        else:
            # Nova format
            request_body = {
                "messages": [{
                    "role": "user",
                    "content": [{"text": prompt}]
                }],
                "inferenceConfig": {
                    "temperature": 0.2,
                    "maxTokens": 1500
                }
            }
        
        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        
        # Extract AI response
        if 'nova' in BEDROCK_MODEL_ID.lower():
            ai_text = response_body['content'][0]['text']
        else:
            ai_text = response_body['output']['message']['content'][0]['text']
        
        # Clean and parse JSON
        ai_text = ai_text.strip()
        if ai_text.startswith('```json'):
            ai_text = ai_text[7:]
        if ai_text.startswith('```'):
            ai_text = ai_text[3:]
        if ai_text.endswith('```'):
            ai_text = ai_text[:-3]
        ai_text = ai_text.strip()
        
        ai_decision = json.loads(ai_text)
        
        # Format response based on AI decision
        if ai_decision.get('decision') == 'APPROVED':
            auth_number = f"AUTH-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            return {
                'status': 'Approved',
                'authorization_number': auth_number,
                'valid_from': datetime.now().isoformat(),
                'valid_until': f"{datetime.now().year}-12-31T23:59:59",
                'approved_procedures': procedure_codes,
                'message': 'Prior authorization approved',
                'ai_reasoning': ai_decision.get('reasoning'),
                'medical_necessity': ai_decision.get('medical_necessity'),
                'code_appropriateness': ai_decision.get('code_appropriateness'),
                'confidence': ai_decision.get('confidence', 'medium')
            }
        else:
            return {
                'status': 'Denied',
                'reason': ai_decision.get('reasoning'),
                'medical_necessity_assessment': ai_decision.get('medical_necessity'),
                'code_appropriateness': ai_decision.get('code_appropriateness'),
                'required_documents': ai_decision.get('missing_elements', []),
                'next_steps': ai_decision.get('required_actions'),
                'clinical_guideline': ai_decision.get('clinical_guideline_reference'),
                'denial_code': 'AI_MEDICAL_NECESSITY_REVIEW',
                'confidence': ai_decision.get('confidence', 'medium')
            }
            
    except Exception as e:
        print(f"AI review error: {str(e)}")
        # Fallback to rule-based if AI fails
        return check_authorization_rules_fallback(pas_request)


def check_authorization_rules_fallback(pas_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback rule-based logic if AI review fails
    """
    """
    Apply rule-based logic to approve/deny PA requests with medical necessity review
    In real implementation, this would be the payer's actual policy engine
    """
    
    diagnosis_codes = pas_request.get('diagnosis', [])
    procedure_codes = pas_request.get('procedures', [])
    evidence = pas_request.get('evidence', {})
    patient_info = pas_request.get('patient', {})
    
    # Convert to strings for easy checking
    diagnosis_str = ' '.join(str(code) for code in diagnosis_codes)
    procedure_str = ' '.join(str(code) for code in procedure_codes)
    
    # MEDICAL NECESSITY RULES
    
    # Rule 0: Non-specific diagnosis codes - insufficient medical necessity
    non_specific_codes = ['R51.9', 'M54.5', 'M25.511']  # Headache, low back pain, shoulder pain
    if any(code in diagnosis_str for code in non_specific_codes):
        return {
            'status': 'Denied',
            'reason': 'Insufficient medical necessity: Non-specific diagnosis without documentation of conservative treatment failure or red flag symptoms',
            'required_documents': [
                'Documentation of 6-8 weeks conservative treatment failure',
                'Physical therapy notes',
                'Medication trial records',
                'Evidence of progressive symptoms or functional limitations'
            ],
            'denial_code': 'MEDICAL_NECESSITY_005',
            'next_steps': 'Complete conservative treatment protocol and resubmit with documented treatment failure'
        }
    
    # Rule 0.5: Inappropriate procedure for condition (ankle sprain + surgery)
    if 'S93.401A' in diagnosis_str and '29891' in procedure_str:
        return {
            'status': 'Denied',
            'reason': 'Procedure not medically necessary: Arthroscopic surgery not indicated for Grade 1 ankle sprain',
            'required_documents': [
                'Evidence of Grade 3 ligament tear',
                'Chronic instability documented with stress testing',
                'Failed 3-6 months conservative treatment including physical therapy'
            ],
            'denial_code': 'INAPPROPRIATE_PROCEDURE_006',
            'next_steps': 'Grade 1 ankle sprains require RICE protocol and physical therapy, not surgery'
        }
    
    # Rule 1: MRI procedures require PT notes and conservative treatment
    mri_cpt_codes = ['73721', '73722', '73723', '70551', '70552', '70553', '72148', '73221']
    requires_mri = any(code in procedure_str for code in mri_cpt_codes)
    
    if requires_mri:
        if not evidence.get('pt_notes'):
            return {
                'status': 'Denied',
                'reason': 'Missing required documentation: Physical Therapy notes showing 6 weeks of conservative treatment',
                'required_documents': ['Physical therapy notes with treatment dates and progress', 'Documentation of failed conservative management'],
                'denial_code': 'INSUFFICIENT_EVIDENCE_001',
                'next_steps': 'Complete 6 weeks of physical therapy and resubmit with PT notes documenting treatment failure'
            }
    
    # Rule 2: Specialty procedures require referral
    specialty_cpt_codes = ['99241', '99242', '99243']
    requires_referral = any(code in str(procedure_codes) for code in specialty_cpt_codes)
    
    if requires_referral:
        if not evidence.get('referral'):
            return {
                'status': 'Denied',
                'reason': 'Missing required documentation: Primary care physician referral',
                'required_documents': ['referral'],
                'denial_code': 'MISSING_REFERRAL_002'
            }
    
    # Rule 3: High-cost procedures require medical necessity documentation
    high_cost_procedures = ['27447', '27486']  # Joint replacement codes
    if any(code in str(procedure_codes) for code in high_cost_procedures):
        if not evidence.get('xray') or not evidence.get('clinical_notes'):
            return {
                'status': 'Denied',
                'reason': 'Missing required documentation: X-ray reports and detailed clinical notes',
                'required_documents': ['xray', 'clinical_notes'],
                'denial_code': 'INSUFFICIENT_MEDICAL_NECESSITY_003'
            }
    
    # Rule 4: All procedures need diagnosis
    if not diagnosis_codes:
        return {
            'status': 'Denied',
            'reason': 'Missing diagnosis codes',
            'required_documents': ['diagnosis'],
            'denial_code': 'MISSING_DIAGNOSIS_004'
        }
    
    # If all rules pass, approve
    auth_number = f"AUTH-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    return {
        'status': 'Approved',
        'authorization_number': auth_number,
        'valid_from': datetime.now().isoformat(),
        'valid_until': f"{datetime.now().year}-12-31T23:59:59",
        'approved_procedures': procedure_codes,
        'message': 'Prior authorization approved'
    }


def lambda_handler(event, context):
    """
    Mock Payer API Lambda handler
    
    Expected request body:
    {
        "patient": {
            "name": "John Smith",
            "member_id": "12345"
        },
        "diagnosis": ["M25.561"],
        "procedures": ["73721"],
        "evidence": {
            "pt_notes": true,
            "xray": false,
            "clinical_notes": true
        },
        "provider": {
            "npi": "1234567890",
            "name": "Dr. Jane Doe"
        }
    }
    """
    
    print(f"Received PA request: {json.dumps(event)}")
    
    try:
        # Parse request body
        if isinstance(event, dict) and 'body' in event:
            # API Gateway format
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            # Direct invocation format
            body = event
        
        # Validate required fields
        diagnosis = body.get('diagnosis', [])
        procedures = body.get('procedures', [])
        
        # Check if fields are missing or empty
        missing_info = []
        if not diagnosis or (isinstance(diagnosis, list) and len(diagnosis) == 0):
            missing_info.append("ICD-10 diagnosis codes")
        if not procedures or (isinstance(procedures, list) and len(procedures) == 0):
            missing_info.append("CPT procedure codes")
        
        # If critical information is missing, deny immediately
        if missing_info:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'status': 'Denied',
                    'authorization_number': None,
                    'reason': f"Prior authorization denied due to missing required information: {', '.join(missing_info)}",
                    'denial_code': 'MISSING_REQUIRED_CODES',
                    'confidence': 'high',
                    'medical_necessity_assessment': 'Cannot assess medical necessity without proper diagnostic and procedure codes.',
                    'clinical_guideline': 'CMS Prior Authorization Requirements',
                    'required_documents': [],
                    'next_steps': f"Please resubmit the request with valid {', '.join(missing_info)}. All prior authorization requests must include proper ICD-10 diagnosis codes and CPT procedure codes.",
                    'request_id': str(uuid.uuid4()),
                    'timestamp': datetime.now().isoformat(),
                    'payer': 'Mock Insurance Co.'
                })
            }
        
        # Validate code formats (basic check)
        invalid_codes = []
        for icd in diagnosis:
            if not isinstance(icd, str) or len(icd) < 3:
                invalid_codes.append(f"Invalid ICD-10: {icd}")
        for cpt in procedures:
            if not isinstance(cpt, str) or (len(cpt) != 5 and len(cpt) != 4):
                invalid_codes.append(f"Invalid CPT: {cpt}")
        
        if invalid_codes:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'status': 'Denied',
                    'authorization_number': None,
                    'reason': f"Prior authorization denied due to invalid codes: {', '.join(invalid_codes)}. ICD-10 codes must be at least 3 characters, CPT codes must be 4-5 digits.",
                    'denial_code': 'INVALID_CODES',
                    'confidence': 'high',
                    'medical_necessity_assessment': 'Cannot assess medical necessity with improperly formatted codes.',
                    'clinical_guideline': 'CMS Coding Standards',
                    'required_documents': [],
                    'next_steps': 'Please verify and resubmit with properly formatted ICD-10 and CPT codes.',
                    'request_id': str(uuid.uuid4()),
                    'timestamp': datetime.now().isoformat(),
                    'payer': 'Mock Insurance Co.'
                })
            }
        
        # Use AI-powered medical necessity review
        decision = ai_medical_necessity_review(body)
        
        # Add processing metadata
        response_data = {
            'request_id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'payer': 'Mock Insurance Co.',
            **decision
        }
        
        # Return response
        http_status = 200 if decision['status'] == 'Approved' else 202
        
        response = {
            'statusCode': http_status,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_data)
        }
        
        print(f"PA Decision: {decision['status']}")
        return response
        
    except Exception as e:
        print(f"Error processing PA request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to process prior authorization request'
            })
        }


# For local testing
if __name__ == '__main__':
    # Test case 1: Approved (has all evidence)
    test_approved = {
        'patient': {'name': 'John Smith', 'member_id': '12345'},
        'diagnosis': ['M25.561'],
        'procedures': ['73721'],
        'evidence': {
            'pt_notes': True,
            'clinical_notes': True
        },
        'provider': {'npi': '1234567890', 'name': 'Dr. Jane Doe'}
    }
    
    # Test case 2: Denied (missing PT notes)
    test_denied = {
        'patient': {'name': 'Jane Doe', 'member_id': '67890'},
        'diagnosis': ['M25.561'],
        'procedures': ['73721'],
        'evidence': {
            'pt_notes': False,
            'clinical_notes': True
        },
        'provider': {'npi': '1234567890', 'name': 'Dr. Jane Doe'}
    }
    
    print("=== Test 1: Should be APPROVED ===")
    result1 = lambda_handler(test_approved, None)
    print(json.dumps(json.loads(result1['body']), indent=2))
    
    print("\n=== Test 2: Should be DENIED ===")
    result2 = lambda_handler(test_denied, None)
    print(json.dumps(json.loads(result2['body']), indent=2))

