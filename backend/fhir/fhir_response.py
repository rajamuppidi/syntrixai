"""
FHIR Response Generator for Prior Authorization Results

Creates FHIR R4 Task resources representing PA decisions
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
import uuid


class FHIRResponseGenerator:
    """Generate FHIR R4 responses for prior authorization results"""
    
    def __init__(self):
        self.base_url = "https://pa-agent.example.com/fhir"
    
    def generate_task_response(
        self,
        case_id: str,
        status: str,
        patient_name: str,
        diagnosis: str,
        procedures: list,
        authorization_number: Optional[str] = None,
        reason: Optional[str] = None,
        required_documents: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Generate a FHIR Task resource for PA response
        
        Args:
            case_id: Internal case ID
            status: 'approved', 'denied', 'pending'
            patient_name: Patient name
            diagnosis: Diagnosis text
            procedures: List of CPT codes
            authorization_number: Auth number if approved
            reason: Denial/approval reason
            required_documents: List of required docs if denied
            
        Returns:
            FHIR R4 Task resource
        """
        
        # Map internal status to FHIR Task status
        task_status_map = {
            'approved': 'completed',
            'denied': 'rejected',
            'pending': 'in-progress',
            'extracted': 'received',
            'validating': 'in-progress'
        }
        
        task_status = task_status_map.get(status, 'in-progress')
        
        # Build Task resource
        task = {
            "resourceType": "Task",
            "id": case_id,
            "status": task_status,
            "intent": "order",
            "code": {
                "coding": [
                    {
                        "system": "http://hl7.org/fhir/us/davinci-pas/CodeSystem/PASTempCodes",
                        "code": "prior-auth-request",
                        "display": "Prior Authorization Request"
                    }
                ],
                "text": "Prior Authorization Request"
            },
            "description": f"Prior authorization for {diagnosis}",
            "authoredOn": datetime.utcnow().isoformat() + "Z",
            "lastModified": datetime.utcnow().isoformat() + "Z",
            "for": {
                "reference": f"Patient/{case_id}",
                "display": patient_name
            },
            "owner": {
                "reference": "Organization/payer-org",
                "display": "Healthcare Payer"
            },
            "businessStatus": {
                "coding": [
                    {
                        "system": "http://hl7.org/fhir/us/davinci-pas/CodeSystem/PASTempCodes",
                        "code": status,
                        "display": status.capitalize()
                    }
                ],
                "text": status.capitalize()
            }
        }
        
        # Add output for approved cases
        if status == 'approved' and authorization_number:
            task["output"] = [
                {
                    "type": {
                        "coding": [
                            {
                                "system": "http://hl7.org/fhir/us/davinci-pas/CodeSystem/PASTempCodes",
                                "code": "auth-number",
                                "display": "Authorization Number"
                            }
                        ]
                    },
                    "valueString": authorization_number
                },
                {
                    "type": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/task-output-type",
                                "code": "disposition",
                                "display": "Disposition"
                            }
                        ]
                    },
                    "valueString": reason or "Prior authorization approved"
                }
            ]
        
        # Add output for denied cases
        elif status == 'denied':
            outputs = [
                {
                    "type": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/task-output-type",
                                "code": "disposition",
                                "display": "Disposition"
                            }
                        ]
                    },
                    "valueString": reason or "Prior authorization denied"
                }
            ]
            
            if required_documents:
                outputs.append({
                    "type": {
                        "coding": [
                            {
                                "system": "http://hl7.org/fhir/us/davinci-pas/CodeSystem/PASTempCodes",
                                "code": "required-documents",
                                "display": "Required Documents"
                            }
                        ]
                    },
                    "valueString": ", ".join(required_documents)
                })
            
            task["output"] = outputs
        
        # Add note
        task["note"] = [
            {
                "text": reason or f"Prior authorization {status}",
                "time": datetime.utcnow().isoformat() + "Z"
            }
        ]
        
        return task
    
    def generate_bundle_response(
        self,
        task: Dict[str, Any],
        include_claim_response: bool = False
    ) -> Dict[str, Any]:
        """
        Wrap Task in a FHIR Bundle for response
        
        Args:
            task: FHIR Task resource
            include_claim_response: Whether to include ClaimResponse
            
        Returns:
            FHIR Bundle
        """
        bundle = {
            "resourceType": "Bundle",
            "type": "searchset",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total": 1,
            "entry": [
                {
                    "fullUrl": f"{self.base_url}/Task/{task['id']}",
                    "resource": task,
                    "search": {
                        "mode": "match"
                    }
                }
            ]
        }
        
        # Optionally add ClaimResponse (for compatibility with some payer systems)
        if include_claim_response:
            claim_response = self._generate_claim_response(task)
            bundle["entry"].append({
                "fullUrl": f"{self.base_url}/ClaimResponse/{task['id']}",
                "resource": claim_response,
                "search": {
                    "mode": "include"
                }
            })
            bundle["total"] = 2
        
        return bundle
    
    def _generate_claim_response(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a ClaimResponse resource based on Task"""
        status_map = {
            'completed': 'active',
            'rejected': 'active',
            'in-progress': 'active'
        }
        
        outcome_map = {
            'completed': 'complete',
            'rejected': 'error',
            'in-progress': 'partial'
        }
        
        return {
            "resourceType": "ClaimResponse",
            "id": task['id'],
            "status": status_map.get(task['status'], 'active'),
            "type": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/claim-type",
                        "code": "professional"
                    }
                ]
            },
            "use": "preauthorization",
            "patient": task.get('for', {}),
            "created": datetime.utcnow().isoformat() + "Z",
            "insurer": {
                "reference": "Organization/payer-org",
                "display": "Healthcare Payer"
            },
            "outcome": outcome_map.get(task['status'], 'partial'),
            "preAuthRef": task.get('output', [{}])[0].get('valueString', '')
        }
    
    def generate_operation_outcome(
        self,
        severity: str,
        code: str,
        details: str
    ) -> Dict[str, Any]:
        """
        Generate FHIR OperationOutcome for errors
        
        Args:
            severity: 'fatal', 'error', 'warning', 'information'
            code: FHIR issue type code
            details: Human-readable description
        """
        return {
            "resourceType": "OperationOutcome",
            "issue": [
                {
                    "severity": severity,
                    "code": code,
                    "details": {
                        "text": details
                    }
                }
            ]
        }


# Convenience function
def create_fhir_task(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a FHIR Task from case data
    
    Usage:
        task = create_fhir_task(case_data)
    """
    generator = FHIRResponseGenerator()
    return generator.generate_task_response(
        case_id=case_data.get('case_id', ''),
        status=case_data.get('status', 'pending'),
        patient_name=case_data.get('patient_name', 'Unknown'),
        diagnosis=case_data.get('diagnosis', ''),
        procedures=case_data.get('CPT', []),
        authorization_number=case_data.get('payer_result', {}).get('authorization_number'),
        reason=case_data.get('payer_result', {}).get('reason'),
        required_documents=case_data.get('evidence_result', {}).get('missing_docs')
    )


# For testing
if __name__ == '__main__':
    # Test approved case
    generator = FHIRResponseGenerator()
    
    approved_task = generator.generate_task_response(
        case_id="case-123",
        status="approved",
        patient_name="Sarah Johnson",
        diagnosis="Lumbar radiculopathy",
        procedures=["72148"],
        authorization_number="AUTH-2024-123456",
        reason="Prior authorization approved for MRI lumbar spine"
    )
    
    print("=== APPROVED TASK ===")
    print(json.dumps(approved_task, indent=2))
    
    # Test denied case
    denied_task = generator.generate_task_response(
        case_id="case-456",
        status="denied",
        patient_name="John Doe",
        diagnosis="Back pain",
        procedures=["72148"],
        reason="Insufficient clinical documentation",
        required_documents=["PT notes", "X-ray results"]
    )
    
    print("\n=== DENIED TASK ===")
    print(json.dumps(denied_task, indent=2))
    
    # Test bundle
    bundle = generator.generate_bundle_response(approved_task)
    print("\n=== BUNDLE RESPONSE ===")
    print(json.dumps(bundle, indent=2))

