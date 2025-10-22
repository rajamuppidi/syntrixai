'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { Search, Filter } from 'lucide-react';
import { Case } from '../types';
import { api } from '../lib/api';
import StatusBadge from '../components/StatusBadge';
import { formatDate } from '../lib/utils';

export default function CasesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [cases, setCases] = useState<Case[]>([]);
  const [filteredCases, setFilteredCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const loadCases = useCallback(async () => {
    try {
      const data = await api.getCases();
      setCases(data);
      
      // Auto-navigate to highlighted case
      const highlight = searchParams.get('highlight');
      if (highlight) {
        router.push(`/cases/${highlight}`);
      }
    } catch (error) {
      console.error('Failed to load cases:', error);
    } finally {
      setLoading(false);
    }
  }, [searchParams, router]);

  const filterCases = useCallback(() => {
    let filtered = cases;

    if (statusFilter !== 'all') {
      filtered = filtered.filter(c => c.status?.toLowerCase() === statusFilter.toLowerCase());
    }

    if (searchTerm) {
      filtered = filtered.filter(c =>
        (c.patient_name?.toLowerCase() || '').includes(searchTerm.toLowerCase()) ||
        (c.diagnosis?.toLowerCase() || '').includes(searchTerm.toLowerCase())
      );
    }

    setFilteredCases(filtered);
  }, [cases, searchTerm, statusFilter]);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  useEffect(() => {
    filterCases();
  }, [filterCases]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Prior Authorization Cases</h1>
        <p className="mt-2 text-sm text-gray-600">
          View and manage all prior authorization requests
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg shadow space-y-4 sm:space-y-0 sm:flex sm:items-center sm:gap-4">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by patient or diagnosis..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-5 w-5 text-gray-400" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">All Status</option>
            <option value="approved">Approved</option>
            <option value="denied">Denied</option>
            <option value="pending">Pending</option>
            <option value="extracted">Extracted</option>
          </select>
        </div>
      </div>

      {/* Cases Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredCases.map((caseItem, index) => (
          <motion.div
            key={caseItem.case_id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            onClick={() => router.push(`/cases/${caseItem.case_id}`)}
            className="bg-white p-6 rounded-lg shadow cursor-pointer hover:shadow-xl hover:-translate-y-1 transition-all duration-200"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900">{caseItem.patient_name || 'Unknown Patient'}</h3>
                <p className="text-xs text-gray-400 font-mono mt-1">{caseItem.case_id?.substring(0, 20) || ''}...</p>
              </div>
              <StatusBadge status={caseItem.status || 'pending'} />
            </div>
            
            <p className="text-sm text-gray-700 mb-4 line-clamp-2 leading-relaxed">
              {caseItem.diagnosis || 'No diagnosis'}
            </p>
            
            {/* Quick Info */}
            <div className="flex items-center justify-between pt-3 border-t border-gray-100">
              <span className="text-xs text-gray-500">{formatDate(caseItem.created_at)}</span>
              {caseItem.authorization_number && (
                <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-mono font-semibold rounded">
                  {caseItem.authorization_number.substring(0, 12)}
                </span>
              )}
            </div>

            {/* Code Badges */}
            {(caseItem.ICD10?.length || caseItem.CPT?.length) && (
              <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-100">
                {caseItem.ICD10 && caseItem.ICD10.length > 0 && (
                  <span className="text-xs text-purple-700 bg-purple-50 px-2 py-1 rounded">
                    {caseItem.ICD10.length} ICD-10
                  </span>
                )}
                {caseItem.CPT && caseItem.CPT.length > 0 && (
                  <span className="text-xs text-blue-700 bg-blue-50 px-2 py-1 rounded">
                    {caseItem.CPT.length} CPT
                  </span>
                )}
              </div>
            )}
          </motion.div>
        ))}
        
        {filteredCases.length === 0 && (
          <div className="col-span-full">
            <div className="text-center py-16 bg-white rounded-lg shadow">
              <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-gray-500 text-lg">No cases found</p>
              <p className="text-gray-400 text-sm mt-2">Try adjusting your search or filter criteria</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
