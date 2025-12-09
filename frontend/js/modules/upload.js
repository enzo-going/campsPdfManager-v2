/**
 * CAMPS PDF Manager v2.0 - Upload Module
 * Handles file selection, validation, and upload with FASE 1 integration
 */

import { FILE_UPLOAD, ROUTES } from '../config.js';
import { formatFileSize } from '../utils/formatters.js';
import { showToast } from '../utils/toast.js';
import { FASE1MetadataForm } from '../fase1/metadata-form.js';

export class UploadModule {
    constructor(api) {
        this.api = api;
        this.selectedFiles = [];
        this.metadataForm = new FASE1MetadataForm();
    }

    /**
     * Initialize upload module
     */
    init() {
        this.setupDropZone();
        this.setupFileInput();
        this.setupButtons();
    }

    /**
     * Setup drag and drop zone
     */
    setupDropZone() {
        const dropZone = document.getElementById('dropZone');
        if (!dropZone) return;

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.add('drag-active');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.remove('drag-active');
            });
        });

        dropZone.addEventListener('drop', (e) => {
            const files = Array.from(e.dataTransfer.files);
            this.addFiles(files);
        });
    }

    /**
     * Setup file input
     */
    setupFileInput() {
        const fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                const files = Array.from(e.target.files);
                this.addFiles(files);
                fileInput.value = ''; // Reset input
            });
        }
    }

    /**
     * Setup action buttons
     */
    setupButtons() {
        const uploadBtn = document.getElementById('uploadBtn');
        const clearBtn = document.getElementById('clearBtn');

        if (uploadBtn) {
            uploadBtn.addEventListener('click', () => this.uploadFiles());
        }

        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearFiles());
        }
    }

    /**
     * Add files to selection
     */
    addFiles(files) {
        const validFiles = files.filter(file => {
            // Check type
            if (file.type !== 'application/pdf') {
                showToast(`Arquivo "${file.name}" ignorado: apenas PDFs são permitidos`, 'warning');
                return false;
            }
            // Check duplicates
            if (this.selectedFiles.some(f => f.name === file.name)) {
                showToast(`Arquivo "${file.name}" já foi adicionado`, 'warning');
                return false;
            }
            return true;
        });

        this.selectedFiles.push(...validFiles);
        this.updateFileList();
    }

    /**
     * Remove file from selection
     */
    removeFile(index) {
        this.selectedFiles.splice(index, 1);
        this.updateFileList();
    }

    /**
     * Clear all files
     */
    clearFiles() {
        this.selectedFiles = [];
        this.updateFileList();
    }

    /**
     * Update file list UI
     */
    updateFileList() {
        const fileList = document.getElementById('fileList');
        const uploadBtn = document.getElementById('uploadBtn');
        const metadataForm = document.getElementById('metadataForm');

        if (!fileList) return;

        if (this.selectedFiles.length === 0) {
            fileList.innerHTML = '<p class="empty-state">Nenhum arquivo selecionado</p>';
            if (uploadBtn) uploadBtn.disabled = true;
            if (metadataForm) metadataForm.style.display = 'none';
            return;
        }

        // Check file sizes
        const hasLargeFiles = this.selectedFiles.some(f => f.size > FILE_UPLOAD.MAX_SIZE);
        let html = hasLargeFiles 
            ? `<p class="warning">⚠️ Alguns arquivos excedem ${FILE_UPLOAD.MAX_SIZE_MB}MB e não serão enviados</p>` 
            : '';

        // Generate list
        html += this.selectedFiles.map((file, index) => `
            <div class="file-item ${file.size > FILE_UPLOAD.MAX_SIZE ? 'error' : ''}">
                <span class="file-icon">📄</span>
                <div class="file-info">
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">${formatFileSize(file.size)}</span>
                </div>
                <button class="btn-icon" onclick="window.app.modules.upload.removeFile(${index})">❌</button>
            </div>
        `).join('');

        fileList.innerHTML = html;
        
        if (uploadBtn) {
            uploadBtn.disabled = this.selectedFiles.filter(f => f.size <= FILE_UPLOAD.MAX_SIZE).length === 0;
        }

        // Show FASE 1 form
        if (metadataForm) {
            metadataForm.style.display = 'block';
            this.metadataForm.loadUserData(this.api);
        }
    }

    /**
     * Upload selected files
     */
    async uploadFiles() {
        // Validate FASE 1 metadata
        if (!this.metadataForm.validate()) {
            return;
        }

        // Filter valid files
        const validFiles = this.selectedFiles.filter(f => f.size <= FILE_UPLOAD.MAX_SIZE);
        if (validFiles.length === 0) {
            showToast('Nenhum arquivo válido para envio', 'error');
            return;
        }

        const uploadBtn = document.getElementById('uploadBtn');
        if (uploadBtn) {
            uploadBtn.disabled = true;
            uploadBtn.innerHTML = '<span class="spinner"></span> Enviando...';
        }

        try {
            const formData = new FormData();
            
            // Add files
            validFiles.forEach(file => {
                formData.append('files[]', file);
            });

            // Add FASE 1 metadata
            const metadata = this.metadataForm.getData();
            for (const [key, value] of Object.entries(metadata)) {
                formData.append(key, value);
            }

            // Upload
            const result = await this.api.upload(ROUTES.DOCUMENTS.UPLOAD, formData);

            if (result.success) {
                this.showResults(result.data);
                showToast(result.message, 'success');
                this.clearFiles();
                
                // Reload dashboard if active
                if (window.app.currentSection === 'dashboard') {
                    window.app.reloadCurrentSection();
                }
            } else {
                showToast(result.message || 'Erro no upload', 'error');
            }

        } catch (error) {
            console.error('Upload error:', error);
            showToast('Erro ao enviar arquivos', 'error');
        } finally {
            if (uploadBtn) {
                uploadBtn.disabled = false;
                uploadBtn.innerHTML = '📤 Enviar PDFs';
            }
        }
    }

    /**
     * Show upload results
     */
    showResults(results) {
        const resultsDiv = document.getElementById('uploadResults');
        if (!resultsDiv) return;

        const successCount = results.filter(r => r.success).length;
        const totalCount = results.length;
        const isSuccess = successCount === totalCount;

        let html = `
            <div class="results-summary ${isSuccess ? 'success' : 'partial'}">
                <strong>✅ ${successCount} de ${totalCount} arquivos enviados com sucesso!</strong>
            </div>
            <div class="results-list">
        `;

        results.forEach(result => {
            html += `
                <div class="result-item ${result.success ? 'success' : 'error'}">
                    <span class="result-icon">${result.success ? '✓' : '✗'}</span>
                    <div class="result-info">
                        <strong>${result.filename}</strong>
                        ${result.success 
                            ? `<small>ID: ${result.document_id} | ${formatFileSize(result.size)} | ${result.pages} páginas</small>`
                            : `<small class="error-text">${result.error}</small>`
                        }
                    </div>
                </div>
            `;
        });

        html += '</div>';
        resultsDiv.innerHTML = html;
        resultsDiv.style.display = 'block';

        // Auto hide
        setTimeout(() => {
            resultsDiv.style.display = 'none';
        }, 5000);
    }
}
