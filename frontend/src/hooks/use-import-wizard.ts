'use client';

import { useState, useCallback } from 'react';
import { api, ImportUploadResponse, ImportValidateResponse, ImportColumnMapping, ImportOptions, ImportJobStatus } from '@/lib/api';

type Step = 'upload' | 'mapping' | 'options' | 'validate' | 'execute' | 'result';

interface UseImportWizardProps {
  providerId: string;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  onError?: (error: string) => void;
  /** Translation function for fallback error messages */
  uploadFailedMessage: string;
  /** Translated fallback message for download failure */
  downloadFailedMessage: string;
  /** Translated fallback message for validation failure */
  validationFailedMessage: string;
  /** Translated fallback message for import failure */
  importFailedMessage: string;
}

export interface UseImportWizardReturn {
  // Step state
  currentStep: Step;
  setCurrentStep: (step: Step) => void;

  // Upload state
  isUploading: boolean;
  uploadResult: ImportUploadResponse | null;
  uploadError: string | null;

  // Mapping state
  columnMapping: ImportColumnMapping[];

  // Options state
  options: ImportOptions;
  setOptions: (options: ImportOptions) => void;

  // Validation state
  isValidating: boolean;
  validationResult: ImportValidateResponse | null;
  validationError: string | null;

  // Execute state
  isExecuting: boolean;
  jobStatus: ImportJobStatus | null;
  executeError: string | null;

  // Handlers
  resetState: () => void;
  handleOpenChange: (open: boolean) => void;
  handleFileUpload: (file: File) => Promise<void>;
  handleDrop: (e: React.DragEvent) => void;
  handleFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleDownloadTemplate: () => Promise<void>;
  handleMappingChange: (fileColumn: string, systemField: string | null) => void;
  hasRequiredFields: () => boolean;
  handleValidate: () => Promise<void>;
  handleExecute: () => Promise<void>;
  handleNext: () => void;
  handleBack: () => void;
  canGoNext: () => boolean;
}

/**
 * Custom hook that encapsulates all business logic for the ImportWizardDialog component.
 * Manages the multi-step import wizard flow: upload, mapping, options, validate, execute, result.
 */
export function useImportWizard({
  providerId,
  onOpenChange,
  onSuccess,
  onError,
  uploadFailedMessage,
  downloadFailedMessage,
  validationFailedMessage,
  importFailedMessage,
}: UseImportWizardProps): UseImportWizardReturn {
  // Step state
  const [currentStep, setCurrentStep] = useState<Step>('upload');

  // Upload state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<ImportUploadResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Mapping state
  const [columnMapping, setColumnMapping] = useState<ImportColumnMapping[]>([]);

  // Options state
  const [options, setOptions] = useState<ImportOptions>({
    error_handling: 'skip',
    default_status: 'active',
    default_currency: 'EUR',
  });

  // Validation state
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<ImportValidateResponse | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Execute state
  const [isExecuting, setIsExecuting] = useState(false);
  const [jobStatus, setJobStatus] = useState<ImportJobStatus | null>(null);
  const [executeError, setExecuteError] = useState<string | null>(null);

  // Reset all state
  const resetState = useCallback(() => {
    setCurrentStep('upload');
    setIsUploading(false);
    setUploadResult(null);
    setUploadError(null);
    setColumnMapping([]);
    setOptions({
      error_handling: 'skip',
      default_status: 'active',
      default_currency: 'EUR',
    });
    setIsValidating(false);
    setValidationResult(null);
    setValidationError(null);
    setIsExecuting(false);
    setJobStatus(null);
    setExecuteError(null);
  }, []);

  // Handle dialog close
  const handleOpenChange = useCallback((open: boolean) => {
    if (!open) {
      resetState();
    }
    onOpenChange(open);
  }, [onOpenChange, resetState]);

  // Handle file upload
  const handleFileUpload = useCallback(async (file: File) => {
    setIsUploading(true);
    setUploadError(null);

    try {
      const result = await api.uploadImportFile(providerId, file);
      setUploadResult(result);

      // Initialize column mapping from suggestions
      const mapping: ImportColumnMapping[] = result.columns.map(col => ({
        file_column: col,
        system_field: result.suggested_mapping[col] || null,
      }));
      setColumnMapping(mapping);

      setCurrentStep('mapping');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : uploadFailedMessage;
      setUploadError(message);
      onError?.(message);
    } finally {
      setIsUploading(false);
    }
  }, [providerId, uploadFailedMessage, onError]);

  // Handle file drop
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, [handleFileUpload]);

  // Handle file select
  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, [handleFileUpload]);

  // Handle template download
  const handleDownloadTemplate = useCallback(async () => {
    try {
      const blob = await api.downloadImportTemplate(providerId, true);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'license_import_template.csv';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : downloadFailedMessage;
      onError?.(message);
    }
  }, [providerId, onError, downloadFailedMessage]);

  // Handle mapping change
  const handleMappingChange = useCallback((fileColumn: string, systemField: string | null) => {
    setColumnMapping(prev =>
      prev.map(m =>
        m.file_column === fileColumn
          ? { ...m, system_field: systemField === '_ignore' ? null : systemField }
          : m
      )
    );
  }, []);

  // Check if required fields are mapped
  const hasRequiredFields = useCallback(() => {
    const mappedFields = columnMapping.map(m => m.system_field).filter(Boolean);
    return mappedFields.includes('license_key') || mappedFields.includes('external_user_id');
  }, [columnMapping]);

  // Handle validation
  const handleValidate = useCallback(async () => {
    if (!uploadResult) return;

    setIsValidating(true);
    setValidationError(null);

    try {
      const result = await api.validateImport(providerId, {
        upload_id: uploadResult.upload_id,
        column_mapping: columnMapping,
        options,
      });
      setValidationResult(result);
      setCurrentStep('validate');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : validationFailedMessage;
      setValidationError(message);
      onError?.(message);
    } finally {
      setIsValidating(false);
    }
  }, [providerId, uploadResult, columnMapping, options, onError, validationFailedMessage]);

  // Handle execute
  const handleExecute = useCallback(async () => {
    if (!uploadResult) return;

    setIsExecuting(true);
    setExecuteError(null);

    try {
      const result = await api.executeImport(providerId, {
        upload_id: uploadResult.upload_id,
        column_mapping: columnMapping,
        options,
        confirmed: true,
      });

      // Poll for job status
      let status: ImportJobStatus;
      do {
        await new Promise(resolve => setTimeout(resolve, 1000));
        status = await api.getImportJobStatus(providerId, result.job_id);
        setJobStatus(status);
      } while (status.status === 'processing' || status.status === 'pending');

      setCurrentStep('result');
      if (status.status === 'completed') {
        onSuccess?.();
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : importFailedMessage;
      setExecuteError(message);
      onError?.(message);
    } finally {
      setIsExecuting(false);
    }
  }, [providerId, uploadResult, columnMapping, options, onSuccess, onError, importFailedMessage]);

  // Handle next step
  const handleNext = () => {
    switch (currentStep) {
      case 'mapping':
        setCurrentStep('options');
        break;
      case 'options':
        handleValidate();
        break;
      case 'validate':
        setCurrentStep('execute');
        break;
      case 'execute':
        handleExecute();
        break;
    }
  };

  // Handle back step
  const handleBack = () => {
    switch (currentStep) {
      case 'mapping':
        setCurrentStep('upload');
        break;
      case 'options':
        setCurrentStep('mapping');
        break;
      case 'validate':
        setCurrentStep('options');
        break;
      case 'execute':
        setCurrentStep('validate');
        break;
    }
  };

  // Can go next
  const canGoNext = () => {
    switch (currentStep) {
      case 'mapping':
        return hasRequiredFields();
      case 'options':
        return true;
      case 'validate':
        return validationResult?.can_proceed ?? false;
      case 'execute':
        return !isExecuting;
      default:
        return false;
    }
  };

  return {
    // Step state
    currentStep,
    setCurrentStep,

    // Upload state
    isUploading,
    uploadResult,
    uploadError,

    // Mapping state
    columnMapping,

    // Options state
    options,
    setOptions,

    // Validation state
    isValidating,
    validationResult,
    validationError,

    // Execute state
    isExecuting,
    jobStatus,
    executeError,

    // Handlers
    resetState,
    handleOpenChange,
    handleFileUpload,
    handleDrop,
    handleFileSelect,
    handleDownloadTemplate,
    handleMappingChange,
    hasRequiredFields,
    handleValidate,
    handleExecute,
    handleNext,
    handleBack,
    canGoNext,
  };
}
