'use client';
import { useState, useEffect } from 'react';
import { Header } from '@/components/layout/header';
import { Plus, Phone, Calendar, Mail, Loader2 } from 'lucide-react';
import { apiGet, apiPatch } from '@/lib/supabase';
import { useAuth } from '@/contexts/auth-context';
import { Lead, LeadStatus } from '@/types';

export default function KanbanPage() {
  const { user } = useAuth();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [statuses, setStatuses] = useState<LeadStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [draggedLead, setDraggedLead] = useState<Lead | null>(null);

  useEffect(() => {
    if (user) {
      loadData();
    }
  }, [user]);

  async function loadData() {
    try {
      const [leadsRes, statusesRes] = await Promise.all([
        apiGet<Lead[]>(`/api/leads?company_id=${user?.company_id}`),
        apiGet<LeadStatus[]>(`/api/lead-statuses/${user?.company_id}`)
      ]);
      setLeads(leadsRes);
      setStatuses(statusesRes.sort((a, b) => a.ordem - b.ordem));
    } catch (error) {
      console.error('Error loading data:', error);
      // Use empty arrays on error
      setLeads([]);
      setStatuses([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleDragStart(lead: Lead) {
    setDraggedLead(lead);
  }

  async function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
  }

  async function handleDrop(statusId: number) {
    if (!draggedLead) return;

    const oldStatusId = draggedLead.status_id;

    // Optimistic update
    setLeads(leads.map(lead =>
      lead.id === draggedLead.id ? { ...lead, status_id: statusId } : lead
    ));

    try {
      await apiPatch(`/api/leads/${draggedLead.id}`, { status_id: statusId });
    } catch (error) {
      console.error('Error updating lead:', error);
      // Rollback
      setLeads(leads.map(lead =>
        lead.id === draggedLead.id ? { ...lead, status_id: oldStatusId } : lead
      ));
    } finally {
      setDraggedLead(null);
    }
  }

  function getLeadsByStatus(statusId: number) {
    return leads.filter(lead => lead.status_id === statusId);
  }

  if (loading) {
    return (
      <div>
        <Header title="Kanban" subtitle="Gerencie seus leads visualmente" />
        <div className="flex items-center justify-center h-96">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header title="Kanban" subtitle="Gerencie seus leads visualmente" />

      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <p className="text-sm text-gray-600">
              {leads.length} {leads.length === 1 ? 'lead' : 'leads'} no total
            </p>
          </div>
          <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
            <Plus className="w-4 h-4" />
            Novo Lead
          </button>
        </div>

        {/* Kanban Board */}
        <div className="flex gap-4 overflow-x-auto pb-4">
          {statuses.length === 0 ? (
            <div className="flex-1 text-center py-12 bg-white rounded-lg border-2 border-dashed border-gray-300">
              <p className="text-gray-500">
                Nenhum status configurado. Configure os status em Configurações.
              </p>
            </div>
          ) : (
            statuses.map((status) => (
              <div key={status.id} className="flex-shrink-0 w-80">
                {/* Column Header */}
                <div
                  className="flex items-center gap-2 mb-3 px-4 py-3 rounded-lg font-medium"
                  style={{ backgroundColor: status.cor + '20' }}
                >
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: status.cor }}
                  />
                  <h3 className="flex-1">{status.nome}</h3>
                  <span className="text-sm text-gray-600 bg-white px-2 py-0.5 rounded-full">
                    {getLeadsByStatus(status.id).length}
                  </span>
                </div>

                {/* Column Content */}
                <div
                  onDragOver={handleDragOver}
                  onDrop={() => handleDrop(status.id)}
                  className="min-h-[500px] p-3 rounded-lg bg-gray-50 border-2 border-dashed border-gray-200 space-y-3"
                >
                  {getLeadsByStatus(status.id).map((lead) => (
                    <div
                      key={lead.id}
                      draggable
                      onDragStart={() => handleDragStart(lead)}
                      className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 cursor-move hover:shadow-md transition-all duration-200"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-medium text-gray-900">
                          {lead.nome || 'Sem nome'}
                        </h4>
                        {lead.ai_enabled && (
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                            IA
                          </span>
                        )}
                      </div>

                      <div className="space-y-1">
                        <div className="flex items-center gap-2 text-sm text-gray-600">
                          <Phone className="w-3 h-3" />
                          <span className="text-xs">{lead.celular}</span>
                        </div>

                        {lead.email && (
                          <div className="flex items-center gap-2 text-sm text-gray-600">
                            <Mail className="w-3 h-3" />
                            <span className="text-xs">{lead.email}</span>
                          </div>
                        )}

                        <div className="flex items-center gap-2 text-xs text-gray-400 mt-2 pt-2 border-t border-gray-100">
                          <Calendar className="w-3 h-3" />
                          {new Date(lead.created_at).toLocaleDateString('pt-BR', {
                            day: '2-digit',
                            month: 'short',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </div>
                      </div>

                      {lead.origem && (
                        <div className="mt-2">
                          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                            {lead.origem}
                          </span>
                        </div>
                      )}
                    </div>
                  ))}

                  {getLeadsByStatus(status.id).length === 0 && (
                    <p className="text-sm text-gray-400 text-center py-8">
                      Nenhum lead neste status
                    </p>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
