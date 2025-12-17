/**
 * CAMPS PDF Manager v2.0 - FASE 1 Metadata Form
 * Handles collection and validation of mandatory metadata
 */

import { validateFASE1Fields } from './validators.js';
import { showToast } from '../utils/toast.js';

export class FASE1MetadataForm {
    constructor(formId = 'metadataForm') {
        this.formElement = document.getElementById(formId);
        this.fields = {
            // Identificação
            author: 'author',
            subject: 'subject',
            production_date: 'production_date',
            // Digitalização
            digitizer_name: 'digitizer_name',
            digitizer_cpf_cnpj: 'digitizer_cpf_cnpj',
            digitization_location: 'digitization_location',
            resolution_dpi: 'resolution_dpi',
            // Organização
            company_name: 'company_name',
            company_cnpj: 'company_cnpj',
            // Classificação
            document_type: 'upload_document_type',
            document_category: 'document_category',
            destination: 'destination',
            retention_period: 'retention_period'
        };
        this.isLoaded = false;
    }

    /**
     * Show the form
     */
    show() {
        if (this.formElement) {
            this.formElement.style.display = 'block';
        }
    }

    /**
     * Hide the form
     */
    hide() {
        if (this.formElement) {
            this.formElement.style.display = 'none';
        }
    }

    /**
     * Load user data for auto-fill
     */
    async loadUserData(api) {
        if (this.isLoaded) return;

        try {
            const user = await api.get('/auth/me');
            
            this.setFieldValue('digitizer_name', user.name);
            if (user.cpf_cnpj) {
                this.setFieldValue('digitizer_cpf_cnpj', user.cpf_cnpj);
            }
            
            this.isLoaded = true;
        } catch (error) {
            console.error('Error loading user data for FASE 1:', error);
        }
    }

    /**
     * Get current form data
     */
    getData() {
        const data = {};
        for (const [key, id] of Object.entries(this.fields)) {
            const element = document.getElementById(id);
            if (element) {
                data[key] = element.value;
            }
        }
        return data;
    }

    /**
     * Validate form data
     */
    validate() {
        const data = this.getData();
        const result = validateFASE1Fields(data);
        
        if (!result.valid) {
            showToast(result.errors.join('\n'), 'error');
            return false;
        }
        
        return true;
    }

    /**
     * Helper to set field value safely
     */
    setFieldValue(fieldId, value) {
        const element = document.getElementById(fieldId);
        if (element && !element.value) { // Only set if empty
            element.value = value;
        }
    }
}
