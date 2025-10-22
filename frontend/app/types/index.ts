export interface Case {
  case_id: string;
  patient_name: string;
  diagnosis: string;
  ICD10: string[];
  CPT: string[];
  summary: string;
  status: 'extracted' | 'processing' | 'approved' | 'denied' | 'pending';
  created_at: string;
  updated_at?: string;
  authorization_number?: string;
  payer_response?: PayerResponse;
  payer_result?: PayerResponse; // Alternative field name used in DynamoDB
  timeline?: TimelineEvent[];
  evidence?: Evidence;
  validation_result?: ValidationResult;
  evidence_result?: EvidenceResult;
}

export interface PayerResponse {
  status: string;
  reason?: string;
  authorization_number?: string;
  ai_reasoning?: string;
  medical_necessity?: string;
  medical_necessity_assessment?: string; // Alternative field name
  code_appropriateness?: string;
  confidence?: string;
  denial_code?: string;
  next_steps?: string;
  missing_elements?: string[];
  required_documents?: string[]; // Alternative field name
}

export interface TimelineEvent {
  timestamp: string;
  event: string;
  status: string;
}

export interface Evidence {
  pt_notes?: boolean;
  clinical_notes?: boolean;
  xray?: boolean;
  referral?: boolean;
}

export interface ValidationResult {
  valid: boolean;
  icd10_valid?: boolean;
  cpt_valid?: boolean;
  message?: string;
}

export interface EvidenceResult {
  all_present: boolean;
  completeness_percentage: number;
  missing_documents?: string[];
}

export interface AIMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface UploadResponse {
  case_id: string;
  extracted_data: {
    patient_name: string;
    diagnosis: string;
    ICD10: string[];
    CPT: string[];
    summary: string;
    evidence?: Evidence;
  };
  message: string;
}

export interface StatisticsData {
  total_cases: number;
  approved: number;
  denied: number;
  pending: number;
  approval_rate: number;
  completion_rate: number;
  top_denial_reasons: Array<{
    reason: string;
    count: number;
  }>;
}

