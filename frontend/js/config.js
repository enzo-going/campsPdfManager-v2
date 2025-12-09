/**
 * CAMPS PDF Manager v2.0 - Configuration
 * Centralized configuration constants
 */

export const API_BASE = 'http://localhost:5000/api';

export const FILE_UPLOAD = {
    MAX_SIZE: 50 * 1024 * 1024,  // 50MB
    MAX_SIZE_MB: 50,
    ALLOWED_TYPES: ['.pdf'],
    MIME_TYPES: ['application/pdf']
};

export const PAGINATION = {
    DEFAULT_SIZE: 20,
    MAX_SIZE: 100
};

export const FASE1 = {
    MIN_DPI: 150,
    DEFAULT_DPI: 300,
    MAX_DPI: 1200,
    COMPANY_NAME: 'CAMPS Santos'
};

export const ROUTES = {
    AUTH: {
        LOGIN: '/auth/login',
        REFRESH: '/auth/refresh',
        ME: '/auth/me',
        LOGOUT: '/auth/logout',
        USERS: '/auth/users'
    },
    DOCUMENTS: {
        UPLOAD: '/documents/upload',
        LIST: '/documents/',
        DETAIL: '/documents',
        METADATA: '/documents/:id/metadata',
        DOWNLOAD: '/documents/:id/download',
        DELETE: '/documents/:id',
        DELETE_MANY: '/documents/delete-many',
        BATCH_METADATA: '/documents/batch/metadata',
        BATCH_STATUS: '/documents/batch/status',
        STATS: '/documents/stats',
        SIGN: '/documents/:id/sign',
        SIGNATURE_STATUS: '/documents/signature/status'
    },
    ANALYTICS: {
        SUMMARY: '/analytics/dashboard/summary',
        TIMELINE: '/analytics/charts/documents-timeline',
        BY_TYPE: '/analytics/charts/documents-by-type',
        SIGNATURE_STATUS: '/analytics/charts/signature-status',
        EXPORT: '/analytics/reports/export'
    }
};
