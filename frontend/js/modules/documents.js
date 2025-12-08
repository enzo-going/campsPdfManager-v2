/**
 * CAMPS PDF Manager v2.0 - Documents Module
 * Handles document listing, filtering, pagination, and actions
 */

import { ROUTES, PAGINATION } from '../config.js';
import { formatFileSize, formatDate } from '../utils/formatters.js';
import { showToast } from '../utils/toast.js';

export class DocumentsModule {
    constructor(api) {
        this.api = api;
        this.currentPage = 1;
        this.documents = [];
        this.selectedDocuments = new Set();
        this.sortBy = 'uploaded_at';
        this.sortOrder = 'desc';
    }

    /**
     * Load documents list
     */
    async load(page = 1) {
        console.log(`📄 Loading documents page ${page}...`);
        
        try {
            const search = document.getElementById('searchInput')?.value || '';
            const docType = document.getElementById('typeFilter')?.value || '';
            const category = document.getElementById('categoryFilter')?.value || '';

            const params = {
                page: page,
                per_page: PAGINATION.DEFAULT_SIZE,
                sort_by: this.sortBy,
                order: this.sortOrder
            };

            if (search) params.search = search;
            if (docType) params.doc_type = docType;
            if (category) params.document_category = category;

            const response = await this.api.get(ROUTES.DOCUMENTS.LIST, params);

            if (response.success) {
                this.documents = response.data.documents;
                this.currentPage = page;
                this.renderTable();
                this.renderPagination(response.data.pagination);
                this.setupFilters();
                this.updateSortIcons();
            } else {
                showToast('Erro ao carregar documentos', 'error');
            }

        } catch (error) {
            console.error('Load documents error:', error);
            showToast('Erro de conexão', 'error');
        }
    }

    /**
     * Sort documents
     */
    sort(field) {
        if (this.sortBy === field) {
            this.sortOrder = this.sortOrder === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortBy = field;
            this.sortOrder = 'asc';
        }
        this.load(1);
    }

    /**
     * Update sort icons
     */
    updateSortIcons() {
        const headers = document.querySelectorAll('.sortable');
        headers.forEach(th => {
            const icon = th.querySelector('.sort-icon');
            if (th.onclick.toString().includes(this.sortBy)) {
                icon.textContent = this.sortOrder === 'asc' ? '↑' : '↓';
                th.classList.add('active-sort');
            } else {
                icon.textContent = '↕';
                th.classList.remove('active-sort');
            }
        });
    }

    /**
     * Render documents table
     */
    renderTable() {
        const tbody = document.getElementById('documentsTableBody');
        if (!tbody) return;

        if (this.documents.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" class="empty-state">
                        Nenhum documento encontrado. Faça upload de PDFs para começar.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.documents.map(doc => `
            <tr data-doc-id="${doc.id}">
                <td>
                    <input type="checkbox" 
                           class="doc-checkbox" 
                           value="${doc.id}" 
                           ${this.selectedDocuments.has(doc.id) ? 'checked' : ''}
                           onchange="window.app.modules.documents.toggleSelection(${doc.id})">
                </td>
                <td>${doc.id}</td>
                <td>
                    <strong>${doc.title || doc.original_filename}</strong>
                    <br><small>${doc.original_filename}</small>
                </td>
                <td>${doc.author || '-'}</td>
                <td style="text-transform: capitalize;">${doc.document_type || '-'}</td>
                <td>${doc.document_category || '-'}</td>
                <td>${formatFileSize(doc.file_size)}</td>
                <td>
                    <span class="badge ${doc.is_signed ? 'badge-success' : 'badge-secondary'}">
                        ${doc.is_signed ? '✓ Assinado' : '⋯ Pendente'}
                    </span>
                </td>
                <td>${formatDate(doc.uploaded_at)}</td>
                <td>
                    <div class="actions">
                        <button class="btn-icon" onclick="window.app.modules.documents.viewDocument(${doc.id})" title="Visualizar">
                            👁️
                        </button>
                        <button class="btn-icon" onclick="window.app.modules.documents.downloadDocument(${doc.id})" title="Download">
                            📥
                        </button>
                        ${window.app.auth.hasPermission('delete') ? `
                            <button class="btn-icon btn-danger" onclick="window.app.modules.documents.deleteDocument(${doc.id})" title="Deletar">
                                🗑️
                            </button>
                        ` : ''}
                    </div>
                </td>
            </tr>
        `).join('');
    }

    /**
     * Render pagination controls
     */
    renderPagination(pagination) {
        const container = document.getElementById('pagination');
        if (!container) return;

        const { current_page, pages, total } = pagination;

        if (pages <= 1) {
            container.innerHTML = '';
            return;
        }

        let html = '<div class="pagination-controls">';

        // Previous
        html += `
            <button class="btn-pagination" 
                    onclick="window.app.modules.documents.load(${current_page - 1})" 
                    ${current_page === 1 ? 'disabled' : ''}>
                ← Anterior
            </button>
        `;

        // Pages
        for (let i = 1; i <= Math.min(pages, 5); i++) {
            html += `
                <button class="btn-pagination ${i === current_page ? 'active' : ''}" 
                        onclick="window.app.modules.documents.load(${i})">
                    ${i}
                </button>
            `;
        }

        // Next
        html += `
            <button class="btn-pagination" 
                    onclick="window.app.modules.documents.load(${current_page + 1})" 
                    ${current_page === pages ? 'disabled' : ''}>
                Próxima →
            </button>
        `;

        html += `<span class="pagination-info">Total: ${total} documentos</span></div>`;
        container.innerHTML = html;
    }

    /**
     * Setup filter listeners
     */
    setupFilters() {
        const searchInput = document.getElementById('searchInput');
        const typeFilter = document.getElementById('typeFilter');
        const searchBtn = document.getElementById('searchBtn');

        if (searchBtn && !searchBtn.dataset.bound) {
            searchBtn.addEventListener('click', () => this.load(1));
            searchBtn.dataset.bound = 'true';
        }

        if (searchInput && !searchInput.dataset.bound) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.load(1);
            });
            searchInput.dataset.bound = 'true';
        }

        if (typeFilter && !typeFilter.dataset.bound) {
            typeFilter.addEventListener('change', () => this.load(1));
            typeFilter.dataset.bound = 'true';
        }
    }

    /**
     * Toggle document selection
     */
    toggleSelection(docId) {
        if (this.selectedDocuments.has(docId)) {
            this.selectedDocuments.delete(docId);
        } else {
            this.selectedDocuments.add(docId);
        }
        
        // Notify batch module if available
        if (window.app.modules.batch) {
            window.app.modules.batch.updateSelection(this.selectedDocuments);
        }
    }

    /**
     * View document details
     */
    async viewDocument(docId) {
        try {
            // Fetch fresh document data from API to ensure we have the latest
            const response = await this.api.get(`${ROUTES.DOCUMENTS.DETAIL}/${docId}`);
            // Backend returns { success: true, data: { ...document fields } }
            const doc = response.data;
            if (!doc) {
                showToast('Documento não encontrado', 'error');
                return;
            }
            console.log('📄 Document data for details:', doc);

            // Populate modal
            document.getElementById('viewDocTitle').textContent = doc.title || doc.original_filename;
            
            // Basic info
            // Basic info
            const detailsHtml = `
                <div class="detail-group">
                    <label>Arquivo</label>
                    <span>${doc.original_filename}</span>
                </div>
                <div class="detail-group">
                    <label>Tamanho</label>
                    <span>${formatFileSize(doc.file_size)}</span>
                </div>
                <div class="detail-group">
                    <label>Enviado em</label>
                    <span>${formatDate(doc.uploaded_at)}</span>
                </div>
                <div class="detail-group">
                    <label>Autor</label>
                    <span>${doc.author || '-'}</span>
                </div>
                <div class="detail-group">
                    <label>Assunto</label>
                    <span>${doc.subject || '-'}</span>
                </div>
                <div class="detail-group">
                    <label>Status</label>
                    <span class="badge ${doc.is_signed ? 'badge-success' : 'badge-secondary'}">
                        ${doc.is_signed ? '✓ Assinado' : '⋯ Pendente'}
                    </span>
                </div>
            `;
            document.getElementById('docDetailsContent').innerHTML = detailsHtml;

            // FASE 1 Metadata
            const fase1Html = `
                <div class="modal-section-title">
                    <span>📋</span> Metadados FASE 1
                </div>
                <div class="doc-fase1-grid">
                    <div class="detail-group">
                        <label>Digitalizador</label>
                        <span>${doc.digitizer_name || '-'}</span>
                    </div>
                    <div class="detail-group">
                        <label>CPF/CNPJ</label>
                        <span>${doc.digitizer_cpf_cnpj || '-'}</span>
                    </div>
                    <div class="detail-group">
                        <label>Resolução</label>
                        <span>${doc.resolution_dpi ? doc.resolution_dpi + ' DPI' : '-'}</span>
                    </div>
                    <div class="detail-group">
                        <label>Empresa</label>
                        <span>${doc.company_name || '-'}</span>
                    </div>
                    <div class="detail-group">
                        <label>Tipo Documental</label>
                        <span>${doc.document_type || '-'}</span>
                    </div>
                </div>
            `;
            // Note: docFase1Content container already exists in HTML, so we just set innerHTML.
            // But wait, I put doc-fase1-grid inside the HTML string above, but the container in index.html is id="docFase1Content" class="doc-fase1-grid".
            // So I should NOT wrap it in another doc-fase1-grid div if the container already has that class.
            // Let's check index.html again.
            // <div id="docFase1Content" class="doc-fase1-grid"></div>
            // So I should just inject the items.
            // BUT, I want a title before the grid.
            // So I should probably change the container in index.html or inject the title outside the grid?
            // Actually, I can just inject the title and then the items? No, grid will mess up the title.
            // I will remove the class from the container in index.html or handle it here.
            // Easier to handle here: I'll inject the title into the parent or change how I inject.
            // Actually, `docFase1Content` is the container. If it has `display: grid`, the title will be a grid item.
            // I should probably remove the class `doc-fase1-grid` from `docFase1Content` in index.html and put the grid inside.
            // OR, I can just make the title span all columns.
            // Let's try to be safe and just update index.html to remove the class from the ID container, and put the class on an inner div.
            
            // Wait, I can't update index.html in this tool call easily without another step.
            // Let's just update the JS to handle it.
            // I will target `docFase1Content` which is currently `<div id="docFase1Content" class="doc-fase1-grid"></div>`.
            // If I put a title in there, it becomes a grid item.
            // I will use `document.getElementById('docFase1Content').className = '';` to remove the grid class from the container,
            // and then inject the title and a new div with the grid class.
            
            document.getElementById('docFase1Content').className = ''; // Remove grid class from container
            document.getElementById('docFase1Content').innerHTML = `
                <div class="modal-section-title">
                    <span>📋</span> Metadados FASE 1
                </div>
                <div class="doc-fase1-grid">
                    <div class="detail-group">
                        <label>Digitalizador</label>
                        <span>${doc.digitizer_name || '-'}</span>
                    </div>
                    <div class="detail-group">
                        <label>CPF/CNPJ</label>
                        <span>${doc.digitizer_cpf_cnpj || '-'}</span>
                    </div>
                    <div class="detail-group">
                        <label>Resolução</label>
                        <span>${doc.resolution_dpi ? doc.resolution_dpi + ' DPI' : '-'}</span>
                    </div>
                    <div class="detail-group">
                        <label>Empresa</label>
                        <span>${doc.company_name || '-'}</span>
                    </div>
                    <div class="detail-group">
                        <label>Tipo Documental</label>
                        <span>${doc.document_type || '-'}</span>
                    </div>
                </div>
            `;

            // Show modal
            document.getElementById('documentModal').style.display = 'flex';

        } catch (error) {
            console.error('View document error:', error);
            showToast('Erro ao visualizar documento', 'error');
        }
    }

    /**
     * Download document
     */
    async downloadDocument(docId) {
        try {
            const url = ROUTES.DOCUMENTS.DOWNLOAD.replace(':id', docId);
            const response = await this.api.auth.fetchWithAuth(`${this.api.baseURL}${url}`);
            
            if (response.ok) {
                const blob = await response.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = downloadUrl;
                
                // Get filename from header or fallback
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = 'documento.pdf';
                if (contentDisposition) {
                    const match = contentDisposition.match(/filename="?([^"]+)"?/);
                    if (match) filename = match[1];
                }
                
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(downloadUrl);
                a.remove();
            } else {
                showToast('Erro ao baixar documento', 'error');
            }
        } catch (error) {
            console.error('Download error:', error);
            showToast('Erro ao baixar documento', 'error');
        }
    }

    /**
     * Delete document
     */
    async deleteDocument(docId) {
        if (!confirm('Tem certeza que deseja excluir este documento?')) return;

        try {
            const url = ROUTES.DOCUMENTS.DELETE.replace(':id', docId);
            const response = await this.api.delete(url);

            if (response.success) {
                showToast('Documento excluído com sucesso', 'success');
                this.load(this.currentPage);
            } else {
                showToast(response.message || 'Erro ao excluir documento', 'error');
            }
        } catch (error) {
            console.error('Delete error:', error);
            showToast('Erro ao excluir documento', 'error');
        }
    }
}
