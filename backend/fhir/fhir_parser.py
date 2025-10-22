"""
FHIR Parser for Prior Authorization Requests

Extracts prior authorization data from FHIR R4 Bundles containing:
- Patient resource
- Condition resource (diagnosis with ICD-10)
- ServiceRequest resource (requested procedure with CPT)
- DocumentReference (clinical notes)
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime


class FHIRParser:
    """Parse FHIR R4 bundles for prior authorization data"""
    
    def __init__(self):
        self.supported_resource_types = [
            'Patient', 'Condition', 'ServiceRequest', 
            'Procedure', 'DocumentReference', 'Claim'
        ]
    
    def parse_bundle(self, fhir_bundle: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a FHIR Bundle and extract prior authorization data
        
        Args:
            fhir_bundle: FHIR R4 Bundle (dict)
            
        Returns:
            Structured PA data compatible with our system
        """
        try:
            # Validate bundle
            if fhir_bundle.get('resourceType') != 'Bundle':
                raise ValueError("Not a FHIR Bundle")
            
            entries = fhir_bundle.get('entry', [])
            
            # Extract resources by type
            patient = None
            conditions = []
            service_requests = []
            procedures = []
            documents = []
            
            for entry in entries:
                resource = entry.get('resource', {})
                resource_type = resource.get('resourceType')
                
                if resource_type == 'Patient':
                    patient = resource
                elif resource_type == 'Condition':
                    conditions.append(resource)
                elif resource_type == 'ServiceRequest':
                    service_requests.append(resource)
                elif resource_type == 'Procedure':
                    procedures.append(resource)
                elif resource_type == 'DocumentReference':
                    documents.append(resource)
            
            # Extract patient info
            patient_data = self._parse_patient(patient) if patient else {}
            
            # Extract diagnosis (ICD-10 from Conditions)
            icd10_codes = []
            diagnosis_text = ""
            for condition in conditions:
                codes = self._extract_codes(condition, 'http://hl7.org/fhir/sid/icd-10')
                icd10_codes.extend(codes)
                
                # Get condition text
                if condition.get('code', {}).get('text'):
                    diagnosis_text = condition['code']['text']
                elif condition.get('code', {}).get('coding'):
                    diagnosis_text = condition['code']['coding'][0].get('display', '')
            
            # Extract procedures (CPT from ServiceRequest or Procedure)
            cpt_codes = []
            procedure_text = ""
            
            for sr in service_requests:
                codes = self._extract_codes(sr, 'http://www.ama-assn.org/go/cpt')
                cpt_codes.extend(codes)
                
                if sr.get('code', {}).get('text'):
                    procedure_text = sr['code']['text']
                elif sr.get('code', {}).get('coding'):
                    procedure_text = sr['code']['coding'][0].get('display', '')
            
            for proc in procedures:
                codes = self._extract_codes(proc, 'http://www.ama-assn.org/go/cpt')
                cpt_codes.extend(codes)
            
            # Extract clinical notes from DocumentReference
            clinical_summary = ""
            for doc in documents:
                if doc.get('content'):
                    content = doc['content'][0]
                    if content.get('attachment', {}).get('data'):
                        # Base64 encoded data
                        try:
                            import base64
                            import re
                            decoded = base64.b64decode(content['attachment']['data'])
                            # Try UTF-8 first, fall back to latin-1 if needed
                            try:
                                clinical_summary = decoded.decode('utf-8')
                            except UnicodeDecodeError:
                                clinical_summary = decoded.decode('latin-1', errors='ignore')
                            
                            # Clean up control characters and formatting issues
                            # Remove control characters except newlines and tabs
                            clinical_summary = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', clinical_summary)
                            # Remove multiple consecutive spaces
                            clinical_summary = re.sub(r' {2,}', ' ', clinical_summary)
                            # Clean up weird character combinations
                            clinical_summary = re.sub(r'[^\x20-\x7E\n\r\t]', '', clinical_summary)
                            # Normalize line endings
                            clinical_summary = clinical_summary.replace('\r\n', '\n').replace('\r', '\n')
                            # Remove excessive blank lines (more than 2 consecutive)
                            clinical_summary = re.sub(r'\n{3,}', '\n\n', clinical_summary)
                            clinical_summary = clinical_summary.strip()
                            
                        except Exception as e:
                            print(f"Warning: Could not decode base64 clinical note: {str(e)}")
                            clinical_summary = "Clinical note present but could not be decoded"
                    elif content.get('attachment', {}).get('url'):
                        clinical_summary = f"Document URL: {content['attachment']['url']}"
            
            # Build structured response
            pa_data = {
                'patient_name': patient_data.get('name', 'Unknown Patient'),
                'patient_id': patient_data.get('id', ''),
                'date_of_birth': patient_data.get('dob', ''),
                'gender': patient_data.get('gender', ''),
                'diagnosis': diagnosis_text or 'Unknown diagnosis',
                'ICD10': list(set(icd10_codes)),  # Remove duplicates
                'CPT': list(set(cpt_codes)),
                'summary': clinical_summary or self._generate_summary(
                    diagnosis_text, procedure_text, icd10_codes, cpt_codes
                ),
                'fhir_source': True,
                'original_bundle': fhir_bundle  # Store original for reference
            }
            
            return pa_data
            
        except Exception as e:
            raise Exception(f"FHIR parsing error: {str(e)}")
    
    def _parse_patient(self, patient: Dict[str, Any]) -> Dict[str, Any]:
        """Extract patient demographic data"""
        if not patient:
            return {}
        
        # Parse name
        name = "Unknown Patient"
        if patient.get('name') and len(patient['name']) > 0:
            name_obj = patient['name'][0]
            given = ' '.join(name_obj.get('given', []))
            family = name_obj.get('family', '')
            name = f"{given} {family}".strip()
        
        return {
            'id': patient.get('id', ''),
            'name': name,
            'dob': patient.get('birthDate', ''),
            'gender': patient.get('gender', '')
        }
    
    def _extract_codes(self, resource: Dict[str, Any], system: str) -> List[str]:
        """
        Extract codes from a FHIR resource
        
        Args:
            resource: FHIR resource with code/coding
            system: Code system URL (e.g., ICD-10, CPT)
            
        Returns:
            List of codes
        """
        codes = []
        
        # Check code.coding array
        if resource.get('code', {}).get('coding'):
            for coding in resource['code']['coding']:
                if coding.get('system') == system and coding.get('code'):
                    codes.append(coding['code'])
        
        # Check reasonCode (for ServiceRequest)
        if resource.get('reasonCode'):
            for reason in resource['reasonCode']:
                if reason.get('coding'):
                    for coding in reason['coding']:
                        if coding.get('system') == system and coding.get('code'):
                            codes.append(coding['code'])
        
        return codes
    
    def _generate_summary(self, diagnosis: str, procedure: str, 
                         icd10: List[str], cpt: List[str]) -> str:
        """Generate clinical summary from extracted data"""
        summary_parts = []
        
        if diagnosis:
            summary_parts.append(f"Diagnosis: {diagnosis}")
        if icd10:
            summary_parts.append(f"ICD-10: {', '.join(icd10)}")
        if procedure:
            summary_parts.append(f"Requested Procedure: {procedure}")
        if cpt:
            summary_parts.append(f"CPT: {', '.join(cpt)}")
        
        return ". ".join(summary_parts) if summary_parts else "Prior authorization request from FHIR bundle"
    
    def validate_bundle(self, fhir_bundle: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate a FHIR bundle for prior authorization requirements
        
        Returns:
            (is_valid, error_message)
        """
        if fhir_bundle.get('resourceType') != 'Bundle':
            return False, "Not a FHIR Bundle"
        
        entries = fhir_bundle.get('entry', [])
        if not entries:
            return False, "Bundle contains no entries"
        
        # Check for required resource types
        resource_types = {entry.get('resource', {}).get('resourceType') 
                         for entry in entries}
        
        # Must have at least Patient and either ServiceRequest or Procedure
        if 'Patient' not in resource_types:
            return False, "Missing Patient resource"
        
        if 'ServiceRequest' not in resource_types and 'Procedure' not in resource_types:
            return False, "Missing ServiceRequest or Procedure resource"
        
        return True, None


# Convenience function
def parse_fhir_bundle(fhir_bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a FHIR bundle and extract prior authorization data
    
    Usage:
        pa_data = parse_fhir_bundle(fhir_bundle)
    """
    parser = FHIRParser()
    return parser.parse_bundle(fhir_bundle)


# For testing
if __name__ == '__main__':
    # Example FHIR bundle (minimal)
    test_bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-123",
                    "name": [{"given": ["Sarah"], "family": "Johnson"}],
                    "birthDate": "1978-05-15",
                    "gender": "female"
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "code": {
                        "coding": [
                            {
                                "system": "http://hl7.org/fhir/sid/icd-10",
                                "code": "M54.16",
                                "display": "Radiculopathy, lumbar region"
                            }
                        ],
                        "text": "Lumbar radiculopathy"
                    }
                }
            },
            {
                "resource": {
                    "resourceType": "ServiceRequest",
                    "status": "active",
                    "intent": "order",
                    "code": {
                        "coding": [
                            {
                                "system": "http://www.ama-assn.org/go/cpt",
                                "code": "72148",
                                "display": "MRI lumbar spine without contrast"
                            }
                        ]
                    }
                }
            }
        ]
    }
    
    parser = FHIRParser()
    result = parser.parse_bundle(test_bundle)
    print(json.dumps(result, indent=2, default=str))

