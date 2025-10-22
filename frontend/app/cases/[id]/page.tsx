'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ArrowLeft, Calendar, FileText, Activity } from 'lucide-react';
import { Case } from '../../types';
import { api } from '../../lib/api';
import StatusBadge from '../../components/StatusBadge';
import { formatDate } from '../../lib/utils';

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadCase = async () => {
      try {
        const id = params.id as string;
        const data = await api.getCase(id);
        setCaseData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load case');
      } finally {
        setLoading(false);
      }
    };

    loadCase();
  }, [params.id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <p className="text-red-700">Failed to load case details</p>
          <button
            onClick={() => router.push('/cases')}
            className="mt-4 text-blue-600 hover:text-blue-800 font-medium"
          >
            ← Back to Cases
          </button>
        </div>
      </div>
    );
  }

  const payerData = caseData.payer_response || caseData.payer_result;

  return (
    <div className="max-w-7xl mx-auto">
      {/* Back Button */}
      <motion.button
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        onClick={() => router.push('/cases')}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6 transition-colors"
      >
        <ArrowLeft className="h-5 w-5" />
        <span className="font-medium">Back to Cases</span>
      </motion.button>

      {/* Header Card */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl shadow-xl overflow-hidden mb-8"
      >
        <div className="px-8 py-8 text-white">
          <div className="flex items-start justify-between mb-6">
            <div className="flex-1">
              <h1 className="text-4xl font-bold mb-3">{caseData.patient_name || 'Unknown Patient'}</h1>
              <div className="flex items-center gap-6 text-blue-100">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  <span className="font-mono text-sm">{caseData.case_id}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  <span className="text-sm">Submitted {formatDate(caseData.created_at)}</span>
                </div>
              </div>
            </div>
            <StatusBadge status={caseData.status || 'pending'} size="lg" />
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-lg p-4 shadow-md border-2 border-blue-300">
              <div className="flex items-center gap-3">
                <div className="bg-blue-100 rounded-full p-2">
                  <Activity className="h-6 w-6 text-blue-700" />
                </div>
                <div>
                  <p className="text-gray-600 text-xs font-semibold uppercase tracking-wider">Status</p>
                  <p className="text-gray-900 text-xl font-bold capitalize">{caseData.status || 'pending'}</p>
                </div>
              </div>
            </div>
            {caseData.ICD10 && caseData.ICD10.length > 0 && (
              <div className="bg-gradient-to-br from-purple-500 to-purple-700 rounded-lg p-4 shadow-md">
                <div className="flex items-center gap-3">
                  <div className="bg-white rounded-full p-2">
                    <span className="text-purple-700 font-bold text-sm">ICD</span>
                  </div>
                  <div>
                    <p className="text-purple-100 text-xs font-semibold uppercase tracking-wider">ICD-10 Codes</p>
                    <p className="text-white text-xl font-bold">{caseData.ICD10.length} {caseData.ICD10.length === 1 ? 'code' : 'codes'}</p>
                  </div>
                </div>
              </div>
            )}
            {caseData.CPT && caseData.CPT.length > 0 && (
              <div className="bg-gradient-to-br from-indigo-500 to-indigo-700 rounded-lg p-4 shadow-md">
                <div className="flex items-center gap-3">
                  <div className="bg-white rounded-full p-2">
                    <span className="text-indigo-700 font-bold text-sm">CPT</span>
                  </div>
                  <div>
                    <p className="text-indigo-100 text-xs font-semibold uppercase tracking-wider">CPT Codes</p>
                    <p className="text-white text-xl font-bold">{caseData.CPT.length} {caseData.CPT.length === 1 ? 'code' : 'codes'}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </motion.div>

      {/* Authorization Result Banner */}
      {caseData.status === 'approved' && caseData.authorization_number && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mb-8 bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-300 rounded-xl p-8 shadow-lg"
        >
          <div className="flex items-start gap-6">
            <div className="flex-shrink-0">
              <div className="bg-green-500 rounded-full p-4">
                <svg className="h-12 w-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
            <div className="flex-1">
              <h2 className="text-3xl font-bold text-green-900 mb-4">✓ Authorization Approved</h2>
              <div className="bg-white rounded-lg p-6 border-2 border-green-200">
                <p className="text-sm text-green-700 font-semibold mb-2">Authorization Number</p>
                <p className="text-4xl font-mono font-bold text-green-900 mb-4">{caseData.authorization_number}</p>
                {payerData?.reason && (
                  <div className="pt-4 border-t border-green-200">
                    <p className="text-green-800 leading-relaxed">{payerData.reason}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {caseData.status === 'denied' && payerData && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mb-8 bg-gradient-to-r from-red-50 to-rose-50 border-2 border-red-300 rounded-xl p-8 shadow-lg"
        >
          <div className="flex items-start gap-6">
            <div className="flex-shrink-0">
              <div className="bg-red-500 rounded-full p-4">
                <svg className="h-12 w-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
            <div className="flex-1">
              <h2 className="text-3xl font-bold text-red-900 mb-4">✗ Authorization Denied</h2>
              <div className="space-y-4">
                {payerData.reason && (
                  <div className="bg-white rounded-lg p-5 border-2 border-red-200">
                    <p className="text-sm font-semibold text-red-800 mb-2">Reason for Denial</p>
                    <p className="text-red-900 leading-relaxed">{payerData.reason}</p>
                  </div>
                )}
                
                {payerData.code_appropriateness && (
                  <div className="bg-white rounded-lg p-5 border-2 border-orange-200">
                    <p className="text-sm font-semibold text-orange-800 mb-2 flex items-center gap-2">
                      <span>⚠️</span>
                      Code Validation Issue
                    </p>
                    <p className="text-orange-900 whitespace-pre-wrap leading-relaxed">{payerData.code_appropriateness}</p>
                  </div>
                )}
                
                {(payerData.medical_necessity || payerData.medical_necessity_assessment) && (
                  <div className="bg-white rounded-lg p-5 border-2 border-red-200">
                    <p className="text-sm font-semibold text-red-800 mb-2">Medical Necessity Assessment</p>
                    <p className="text-red-900 leading-relaxed">{payerData.medical_necessity || payerData.medical_necessity_assessment}</p>
                  </div>
                )}
                
                {(payerData.missing_elements || payerData.required_documents) && 
                 (payerData.missing_elements || payerData.required_documents)!.length > 0 && (
                  <div className="bg-white rounded-lg p-5 border-2 border-red-200">
                    <p className="text-sm font-semibold text-red-800 mb-3">Missing Requirements</p>
                    <ul className="space-y-2">
                      {(payerData.missing_elements || payerData.required_documents)!.map((item: string, idx: number) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-red-600 mt-0.5">•</span>
                          <span className="text-red-900">{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {payerData.next_steps && (
                  <div className="bg-yellow-50 rounded-lg p-5 border-2 border-yellow-300">
                    <p className="text-sm font-semibold text-yellow-900 mb-2 flex items-center gap-2">
                      <span>📋</span>
                      Recommended Next Steps
                    </p>
                    <p className="text-yellow-900 font-medium leading-relaxed">{payerData.next_steps}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Clinical Information Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Diagnosis Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="lg:col-span-2 bg-white rounded-xl shadow-lg overflow-hidden"
        >
          <div className="bg-gradient-to-r from-gray-700 to-gray-900 px-6 py-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Primary Diagnosis
            </h3>
          </div>
          <div className="p-6">
            <p className="text-gray-900 text-lg leading-relaxed">
              {caseData.diagnosis || 'No diagnosis provided'}
            </p>
          </div>
        </motion.div>

        {/* Medical Codes Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-xl shadow-lg overflow-hidden"
        >
          <div className="bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-4">
            <h3 className="text-lg font-bold text-white">Medical Codes</h3>
          </div>
          <div className="p-6 space-y-4">
            {caseData.ICD10 && caseData.ICD10.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">ICD-10 Codes</p>
                <div className="flex flex-wrap gap-2">
                  {caseData.ICD10.map(code => (
                    <span key={code} className="px-3 py-1.5 bg-purple-100 border border-purple-300 rounded-lg text-sm font-mono font-bold text-purple-900">
                      {code}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {caseData.CPT && caseData.CPT.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-2">CPT Codes</p>
                <div className="flex flex-wrap gap-2">
                  {caseData.CPT.map(code => (
                    <span key={code} className="px-3 py-1.5 bg-indigo-100 border border-indigo-300 rounded-lg text-sm font-mono font-bold text-indigo-900">
                      {code}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {(!caseData.ICD10 || caseData.ICD10.length === 0) && (!caseData.CPT || caseData.CPT.length === 0) && (
              <p className="text-gray-500 text-sm">No codes available</p>
            )}
          </div>
        </motion.div>
      </div>

      {/* Clinical Summary */}
      {caseData.summary && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-xl shadow-lg overflow-hidden"
        >
          <div className="bg-gradient-to-r from-blue-600 to-cyan-600 px-6 py-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Clinical Summary
            </h3>
          </div>
          <div className="p-6">
            <div className="prose max-w-none">
              <p className="text-gray-800 text-base leading-relaxed whitespace-pre-wrap">
                {caseData.summary}
              </p>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}

