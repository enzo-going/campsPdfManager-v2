/**
 * CAMPS PDF Manager v2.0 - Batch Module
 * Handles batch operations (metadata update, delete)
 */

import { ROUTES } from '../config.js';
import { showToast } from '../utils/toast.js';

export class BatchModule {
    constructor(api) {
        this.api = api;
        this.selectedDocuments = new Set();
    }

    /**
     * Update selection from DocumentsModule
     */
    updateSelection(selectedSet) {
        this.selectedDocuments = selectedSet;
        this.updateActionBar();
    }

    /**
     * Update action bar visibility and count
     */
    updateActionBar() {
        const bar = document.getElementById('batchActionsBar');
        const countSpan = document.getElementById('selectedCount');
        const selectAllBtn = document.getElementById('selectAllBtn');

        if (!bar) return;

        if (this.selectedDocuments.size > 0) {
            bar.style.display = 'flex';
            if (countSpan) {
                countSpan.textContent = this.selectedDocuments.size;
            }
        } else {
            bar.style.display = 'none';
        }

        // Setup listeners if not already done
        if (selectAllBtn && !selectAllBtn.dataset.bound) {
            selectAllBtn.addEventListener('click', () => this.toggleSelectAll());
            selectAllBtn.dataset.bound = 'true';
        }

        const metadataBtn = document.getElementById('batchMetadataBtn');
        if (metadataBtn && !metadataBtn.dataset.bound) {
            metadataBtn.addEventListener('click', () => this.openMetadataModal());
            metadataBtn.dataset.bound = 'true';
        }

        const signBtn = document.getElementById('batchSignBtn');
        if (signBtn && !signBtn.dataset.bound) {
            signBtn.addEventListener('click', () => this.signSelected());
            signBtn.dataset.bound = 'true';
        }

        const deleteBtn = document.getElementById('batchDeleteBtn');
        if (deleteBtn && !deleteBtn.dataset.bound) {
            deleteBtn.addEventListener('click', () => this.deleteSelected());
            deleteBtn.dataset.bound = 'true';
        }
    }

    /**
     * Toggle select all documents
     */
    toggleSelectAll() {
        const checkboxes = document.querySelectorAll('.doc-checkbox');
        const allSelected = this.selectedDocuments.size === checkboxes.length;

        if (allSelected) {
            // Deselect all
            this.selectedDocuments.clear();
            checkboxes.forEach(cb => cb.checked = false);
        } else {
            // Select all visible
            this.selectedDocuments.clear();
            checkboxes.forEach(cb => {
                cb.checked = true;
                this.selectedDocuments.add(parseInt(cb.value));
            });
        }

        // Sync with DocumentsModule
        if (window.app.modules.documents) {
            window.app.modules.documents.selectedDocuments = new Set(this.selectedDocuments);
        }

        this.updateActionBar();
    }

    /**
     * Clear all selections
     */
    clearSelection() {
        this.selectedDocuments.clear();
        
        // Uncheck all checkboxes
        document.querySelectorAll('.doc-checkbox').forEach(cb => cb.checked = false);
        const selectAll = document.getElementById('selectAllCheckbox');
        if (selectAll) selectAll.checked = false;

        // Sync with DocumentsModule
        if (window.app.modules.documents) {
            window.app.modules.documents.selectedDocuments = new Set();
        }

        this.updateActionBar();
    }

    /**
     * Open batch metadata modal
     */
    openMetadataModal() {
        if (this.selectedDocuments.size === 0) return;

        const modal = document.getElementById('batchMetadataModal');
        const count = document.getElementById('batchDocCount');
        const form = document.getElementById('batchMetadataForm');
        const title = modal.querySelector('h2');

        if (modal && count) {
            count.textContent = this.selectedDocuments.size;
            if (form) form.reset();

            // Pre-fill if single document selected
            if (this.selectedDocuments.size === 1) {
                const docId = Array.from(this.selectedDocuments)[0];
                const doc = window.app.modules.documents.documents.find(d => d.id === docId);
                
                if (doc && form) {
                    if (title) title.textContent = '📝 Editar Metadados';
                    
                    // Basic Fields
                    if (doc.author) document.getElementById('batchAuthor').value = doc.author;
                    if (doc.subject) document.getElementById('batchSubject').value = doc.subject;
                    if (doc.document_type) document.getElementById('batchDocType').value = doc.document_type;
                    
                    // FASE 1 Fields
                    if (doc.digitizer_name) document.getElementById('batchDigitizerName').value = doc.digitizer_name;
                    if (doc.digitizer_cpf_cnpj) document.getElementById('batchDigitizerCpfCnpj').value = doc.digitizer_cpf_cnpj;
                    if (doc.resolution_dpi) document.getElementById('batchResolution').value = doc.resolution_dpi;
                    if (doc.company_name) document.getElementById('batchCompanyName').value = doc.company_name;
                    if (doc.document_category) document.getElementById('batchDocCategory').value = doc.document_category;
                }
            } else {
                if (title) title.textContent = '📝 Adicionar Metadados em Lote';
            }
            
            // Setup submit handler
            if (form && !form.dataset.bound) {
                form.addEventListener('submit', (e) => this.submitMetadata(e));
                form.dataset.bound = 'true';
            }

            modal.style.display = 'flex';
        }
    }

    /**
     * Submit batch metadata update
     */
    async submitMetadata(event) {
        event.preventDefault();

        const rawMetadata = {
            author: document.getElementById('batchAuthor')?.value,
            subject: document.getElementById('batchSubject')?.value,
            document_type: document.getElementById('batchDocType')?.value,
            digitizer_name: document.getElementById('batchDigitizerName')?.value,
            digitizer_cpf_cnpj: document.getElementById('batchDigitizerCpfCnpj')?.value,
            resolution_dpi: document.getElementById('batchResolution')?.value,
            company_name: document.getElementById('batchCompanyName')?.value,
            document_category: document.getElementById('batchDocCategory')?.value
        };

        // Filter out empty strings to avoid validation errors
        const metadata = Object.fromEntries(
            Object.entries(rawMetadata).filter(([_, v]) => v !== '' && v !== null && v !== undefined)
        );

        // Validate at least one field
        if (!Object.values(metadata).some(val => val)) {
            showToast('Preencha pelo menos um campo', 'warning');
            return;
        }

        const progressDiv = document.getElementById('batchProgress');
        if (progressDiv) progressDiv.style.display = 'block';

        try {
            const response = await this.api.post(ROUTES.DOCUMENTS.BATCH_METADATA, {
                document_ids: Array.from(this.selectedDocuments),
                metadata: metadata
            });

            if (response.success) {
                this.pollStatus(response.task_id);
            } else {
                showToast(response.message || 'Erro ao iniciar processamento', 'error');
                if (progressDiv) progressDiv.style.display = 'none';
            }

        } catch (error) {
            console.error('Batch metadata error:', error);
            showToast('Erro ao processar lote', 'error');
            if (progressDiv) progressDiv.style.display = 'none';
        }
    }

    /**
     * Poll batch task status
     */
    async pollStatus(taskId) {
        const maxAttempts = 30;
        let attempts = 0;

        const interval = setInterval(async () => {
            attempts++;

            try {
                const response = await this.api.get(`${ROUTES.DOCUMENTS.BATCH_STATUS}/${taskId}`);

                if (response.success) {
                    this.updateProgress(response.status, response.result);

                    if (response.status === 'completed' || response.status === 'failed') {
                        clearInterval(interval);
                        this.finishBatch(response);
                    }
                }

                if (attempts >= maxAttempts) {
                    clearInterval(interval);
                    showToast('Timeout no processamento', 'error');
                }

            } catch (error) {
                console.error('Poll error:', error);
                clearInterval(interval);
            }
        }, 1000);
    }

    /**
     * Update progress UI
     */
    updateProgress(status, result) {
        const text = document.getElementById('batchProgressText');
        const bar = document.getElementById('batchProgressBar');

        if (text && result && result.total) {
            const processed = result.success || 0;
            text.textContent = `Processando: ${processed}/${result.total}`;
            
            if (bar) {
                const percent = (processed / result.total) * 100;
                bar.style.width = `${percent}%`;
            }
        }
    }

    /**
     * Finish batch operation
     */
    finishBatch(response) {
        const modal = document.getElementById('batchMetadataModal');
        if (modal) modal.style.display = 'none';

        showToast('Processamento em lote concluído', 'success');
        
        // Reload documents
        if (window.app.modules.documents) {
            window.app.modules.documents.load(window.app.modules.documents.currentPage);
        }
    }

    /**
     * Delete selected documents
     */
    async deleteSelected() {
        if (!confirm(`Tem certeza que deseja excluir ${this.selectedDocuments.size} documentos?`)) return;

        try {
            const response = await this.api.post(ROUTES.DOCUMENTS.DELETE_MANY, {
                document_ids: Array.from(this.selectedDocuments)
            });

            if (response.success) {
                showToast('Documentos excluídos com sucesso', 'success');
                this.selectedDocuments.clear();
                this.updateActionBar();
                
                if (window.app.modules.documents) {
                    window.app.modules.documents.load(window.app.modules.documents.currentPage);
                }
            } else {
                showToast(response.message || 'Erro ao excluir documentos', 'error');
            }

        } catch (error) {
            console.error('Batch delete error:', error);
            showToast('Erro ao excluir documentos', 'error');
        }
    }

    /**
     * Sign selected documents in batch
     */
    async signSelected() {
        if (this.selectedDocuments.size === 0) return;

        const count = this.selectedDocuments.size;
        if (!confirm(`Deseja assinar digitalmente ${count} documento(s) com certificado ICP-Brasil A1?\n\nEsta ação é irreversível.`)) {
            return;
        }

        showToast(`Iniciando assinatura de ${count} documento(s)...`, 'info');

        try {
            const response = await this.api.post(ROUTES.DOCUMENTS.BATCH_SIGN, {
                document_ids: Array.from(this.selectedDocuments)
            });

            if (response.success) {
                // Mostrar info sobre docs já assinados
                if (response.already_signed > 0) {
                    showToast(`${response.already_signed} documento(s) já estavam assinados e foram ignorados`, 'warning');
                }
                
                // Iniciar polling do status
                this.pollStatus(response.task_id);
            } else {
                showToast(response.message || 'Erro ao iniciar assinatura', 'error');
            }

        } catch (error) {
            console.error('Batch sign error:', error);
            showToast('Erro ao assinar documentos', 'error');
        }
    }
}
