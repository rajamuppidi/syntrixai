'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Upload, FileText, Loader2, CheckCircle } from 'lucide-react';
import { api } from '../lib/api';

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [orchestrating, setOrchestrating] = useState(false);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [completed, setCompleted] = useState(false);
  const [result, setResult] = useState<{
    status: string;
    authorization_number?: string;
    reason?: string;
    next_steps?: string;
    code_appropriateness?: string;
    medical_necessity?: string;
    missing_elements?: string[];
  } | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    try {
      setError(null);
      setCompleted(false);
      setUploading(true);
      setExtracting(true);

      // Upload and extract
      const uploadResult = await api.uploadNote(file);
      
      if (!uploadResult.case_id) {
        throw new Error('Upload failed - no case ID returned');
      }

      setCaseId(uploadResult.case_id);
      setUploading(false);
      setExtracting(false);
      setOrchestrating(true);

      // Orchestrate
      await api.orchestrateCase(uploadResult.case_id);
      
      setOrchestrating(false);

      // Fetch final case status
      const finalCase = await api.getCase(uploadResult.case_id);
      const payerData = finalCase.payer_response || finalCase.payer_result;
      setResult({
        status: finalCase.status || 'completed',
        authorization_number: finalCase.authorization_number,
        reason: payerData?.reason,
        next_steps: payerData?.next_steps,
        code_appropriateness: payerData?.code_appropriateness,
        medical_necessity: payerData?.medical_necessity || payerData?.medical_necessity_assessment,
        missing_elements: payerData?.missing_elements || payerData?.required_documents,
      });
      
      setCompleted(true);

      // Redirect after showing result (5 seconds for approved, 8 seconds for denied to read details)
      const redirectDelay = finalCase.status === 'denied' ? 8000 : 5000;
      setTimeout(() => {
        router.push(`/cases/${uploadResult.case_id}`);
      }, redirectDelay);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setUploading(false);
      setExtracting(false);
      setOrchestrating(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setError(null);
    setCompleted(false);
    setResult(null);
    setCaseId(null);
  };

  const isProcessing = uploading || extracting || orchestrating;
  const showResults = completed && result;

  return (
    <div className="fixed inset-y-0 right-0 left-0 lg:left-72 flex flex-col bg-white">
      {/* Header Bar */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-blue-600 p-2 rounded-lg">
              <Upload className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Submit Prior Authorization</h1>
              <p className="text-xs text-gray-500">Upload clinical note or FHIR bundle</p>
            </div>
          </div>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="space-y-6">
            {!isProcessing && !showResults ? (
              <div className="bg-white border border-gray-200 rounded-lg p-8">
                {/* Drag & Drop Zone */}
                <div className="flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-lg hover:border-blue-400 transition-colors">
                  <div className="space-y-2 text-center">
                    <FileText className="mx-auto h-12 w-12 text-gray-400" />
                    <div className="flex text-sm text-gray-600">
                      <label
                        htmlFor="file-upload"
                        className="relative cursor-pointer rounded-md bg-white font-medium text-blue-600 hover:text-blue-500"
                      >
                        <span>Upload a file</span>
                        <input
                          id="file-upload"
                          name="file-upload"
                          type="file"
                          className="sr-only"
                          accept=".txt,.json"
                          onChange={handleFileChange}
                        />
                      </label>
                      <p className="pl-1">or drag and drop</p>
                    </div>
                    <p className="text-xs text-gray-500">
                      Plain text (.txt) or FHIR R4 JSON (.json) files
                    </p>
                  </div>
                </div>

                {/* Selected File */}
                {file && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-6 flex items-center justify-between p-4 bg-blue-50 border border-blue-200 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="h-5 w-5 text-blue-600" />
                      <div>
                        <p className="text-sm font-medium text-gray-900">{file.name}</p>
                        <p className="text-xs text-gray-500">
                          {(file.size / 1024).toFixed(2)} KB • {file.name.endsWith('.json') ? 'FHIR Bundle' : 'Plain text'}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => setFile(null)}
                      className="text-sm text-gray-600 hover:text-gray-900"
                    >
                      Remove
                    </button>
                  </motion.div>
                )}

                {/* Error */}
                {error && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg"
                  >
                    <p className="text-sm text-red-700">{error}</p>
                  </motion.div>
                )}

                {/* Submit Button */}
                <button
                  onClick={handleUpload}
                  disabled={!file}
                  className="mt-6 w-full flex justify-center items-center gap-2 px-4 py-3 text-sm font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                  <Upload className="h-5 w-5" />
                  Process Authorization Request
                </button>
              </div>
            ) : isProcessing ? (
              <div className="bg-white border border-gray-200 rounded-lg p-8">
                <div className="space-y-6">
                  <ProcessStep
                    label="Uploading to S3"
                    active={uploading}
                    complete={!uploading && caseId !== null}
                  />
                  <ProcessStep
                    label="Extracting with AI"
                    active={extracting}
                    complete={!extracting && caseId !== null}
                  />
                  <ProcessStep
                    label="Validating codes & evidence"
                    active={orchestrating}
                    complete={!orchestrating && result !== null}
                  />
                </div>
              </div>
            ) : showResults ? (
              <div className="space-y-6">
                {/* All steps complete */}
                <div className="bg-white border border-gray-200 rounded-lg p-8">
                  <div className="space-y-6">
                    <ProcessStep
                      label="Uploading to S3"
                      active={false}
                      complete={true}
                    />
                    <ProcessStep
                      label="Extracting with AI"
                      active={false}
                      complete={true}
                    />
                    <ProcessStep
                      label="Validating codes & evidence"
                      active={false}
                      complete={true}
                    />
                  </div>
                </div>

                {/* Result Card */}
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-white border border-gray-200 rounded-lg p-6"
                >
                  {result.status === 'approved' ? (
                    <div className="text-center">
                      <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
                        <CheckCircle className="h-10 w-10 text-green-600" />
                      </div>
                      <h3 className="text-2xl font-bold text-gray-900 mb-2">
                        Authorization Approved
                      </h3>
                      {result.authorization_number && (
                        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                          <p className="text-sm text-gray-600 mb-1">Authorization Number</p>
                          <p className="text-xl font-mono font-bold text-gray-900">
                            {result.authorization_number}
                          </p>
                        </div>
                      )}
                      {result.reason && (
                        <p className="mt-4 text-sm text-gray-600">
                          {result.reason}
                        </p>
                      )}
                      <div className="mt-6 flex gap-3 justify-center">
                        <button
                          onClick={handleReset}
                          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                        >
                          Upload Another
                        </button>
                        <button
                          onClick={() => router.push(`/cases/${caseId}`)}
                          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                        >
                          View Case Details
                        </button>
                      </div>
                      <p className="mt-4 text-xs text-gray-500">
                        Auto-redirecting in 5 seconds...
                      </p>
                    </div>
                  ) : result.status === 'denied' ? (
                    <div className="max-h-96 overflow-y-auto">
                      <div className="text-center mb-6">
                        <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
                          <svg className="h-10 w-10 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </div>
                        <h3 className="text-2xl font-bold text-gray-900">
                          Authorization Denied
                        </h3>
                      </div>
                      <div className="space-y-3 text-left">
                        {result.reason && (
                          <div>
                            <p className="text-sm font-semibold text-gray-700 mb-1">Reason</p>
                            <p className="text-sm text-gray-900 bg-gray-50 p-3 rounded-lg border border-gray-200">
                              {result.reason}
                            </p>
                          </div>
                        )}
                        {result.code_appropriateness && (
                          <div>
                            <p className="text-sm font-semibold text-gray-700 mb-1">Code Validation Issue</p>
                            <p className="text-sm text-gray-900 bg-gray-50 p-3 rounded-lg border border-gray-200 whitespace-pre-wrap">
                              {result.code_appropriateness}
                            </p>
                          </div>
                        )}
                        {result.medical_necessity && (
                          <div>
                            <p className="text-sm font-semibold text-gray-700 mb-1">Medical Necessity</p>
                            <p className="text-sm text-gray-900 bg-gray-50 p-3 rounded-lg border border-gray-200">
                              {result.medical_necessity}
                            </p>
                          </div>
                        )}
                        {result.missing_elements && result.missing_elements.length > 0 && (
                          <div>
                            <p className="text-sm font-semibold text-gray-700 mb-1">Missing Requirements</p>
                            <ul className="text-sm text-gray-900 bg-gray-50 p-3 rounded-lg border border-gray-200 list-disc list-inside space-y-1">
                              {result.missing_elements.map((item, idx) => (
                                <li key={idx}>{item}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {result.next_steps && (
                          <div>
                            <p className="text-sm font-semibold text-gray-700 mb-1">Next Steps</p>
                            <p className="text-sm text-gray-900 bg-blue-50 p-3 rounded-lg border border-blue-200">
                              {result.next_steps}
                            </p>
                          </div>
                        )}
                      </div>
                      <div className="mt-6 flex gap-3 justify-center">
                        <button
                          onClick={handleReset}
                          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                        >
                          Upload Another
                        </button>
                        <button
                          onClick={() => router.push(`/cases/${caseId}`)}
                          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                        >
                          View Case Details
                        </button>
                      </div>
                      <p className="mt-4 text-xs text-gray-500 text-center">
                        Auto-redirecting in 8 seconds...
                      </p>
                    </div>
                  ) : (
                    <div className="text-center">
                      <CheckCircle className="mx-auto h-12 w-12 text-green-600 mb-3" />
                      <h3 className="text-lg font-medium text-gray-900">
                        Processing Complete
                      </h3>
                      <p className="mt-2 text-sm text-gray-600">
                        Redirecting to case details...
                      </p>
                    </div>
                  )}
                </motion.div>
              </div>
            ) : null}

            {/* Info Box */}
            {!isProcessing && !showResults && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-900 mb-2">
                  How it works
                </h3>
                <ol className="text-sm text-gray-700 space-y-1 list-decimal list-inside">
                  <li>Clinical note is uploaded to secure S3 storage</li>
                  <li>AI extracts ICD-10 codes, CPT codes, and clinical summary</li>
                  <li>Codes are validated for correctness and appropriateness</li>
                  <li>Evidence documentation is checked</li>
                  <li>Request is submitted to payer for AI-powered review</li>
                </ol>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ProcessStep({
  label,
  active,
  complete,
}: {
  label: string;
  active: boolean;
  complete: boolean;
}) {
  return (
    <div className="flex items-center gap-4">
      <div className="relative">
        {active && (
          <Loader2 className="h-6 w-6 text-blue-600 animate-spin" />
        )}
        {complete && !active && (
          <CheckCircle className="h-6 w-6 text-green-600" />
        )}
        {!active && !complete && (
          <div className="h-6 w-6 rounded-full border-2 border-gray-300" />
        )}
      </div>
      <span
        className={`text-sm font-medium ${
          active || complete ? 'text-gray-900' : 'text-gray-400'
        }`}
      >
        {label}
      </span>
    </div>
  );
}

