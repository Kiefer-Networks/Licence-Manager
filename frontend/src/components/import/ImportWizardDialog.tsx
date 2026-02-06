'use client';

import { useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import {
  Upload,
  Loader2,
  AlertTriangle,
  CheckCircle,
  X,
  Download,
  ArrowRight,
  ArrowLeft,
  FileSpreadsheet,
  AlertCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { api, ImportUploadResponse, ImportValidateResponse, ImportColumnMapping, ImportOptions, ImportJobStatus } from '@/lib/api';

interface ImportWizardDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  providerId: string;
  onSuccess?: () => void;
  onError?: (error: string) => void;
}

type Step = 'upload' | 'mapping' | 'options' | 'validate' | 'execute' | 'result';

const SYSTEM_FIELDS = [
  { value: 'license_key', label: 'licenseKeyField' },
  { value: 'external_user_id', label: 'externalUserIdField' },
  { value: 'license_type', label: 'licenseTypeField' },
  { value: 'employee_email', label: 'employeeEmailField' },
  { value: 'monthly_cost', label: 'monthlyCostField' },
  { value: 'currency', label: 'currencyField' },
  { value: 'valid_until', label: 'validUntilField' },
  { value: 'status', label: 'statusField' },
  { value: 'notes', label: 'notesField' },
  { value: 'is_service_account', label: 'isServiceAccountField' },
  { value: 'service_account_name', label: 'serviceAccountNameField' },
  { value: 'is_admin_account', label: 'isAdminAccountField' },
  { value: 'admin_account_name', label: 'adminAccountNameField' },
];

export function ImportWizardDialog({
  open,
  onOpenChange,
  providerId,
  onSuccess,
  onError,
}: ImportWizardDialogProps) {
  const t = useTranslations('providers.import');
  const tCommon = useTranslations('common');

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
      const message = err instanceof Error ? err.message : t('uploadFailed');
      setUploadError(message);
      onError?.(message);
    } finally {
      setIsUploading(false);
    }
  }, [providerId, t, onError]);

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
      const message = err instanceof Error ? err.message : 'Download failed';
      onError?.(message);
    }
  }, [providerId, onError]);

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
      const message = err instanceof Error ? err.message : 'Validation failed';
      setValidationError(message);
      onError?.(message);
    } finally {
      setIsValidating(false);
    }
  }, [providerId, uploadResult, columnMapping, options, onError]);

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
      const message = err instanceof Error ? err.message : 'Import failed';
      setExecuteError(message);
      onError?.(message);
    } finally {
      setIsExecuting(false);
    }
  }, [providerId, uploadResult, columnMapping, options, onSuccess, onError]);

  // Render step indicator
  const renderStepIndicator = () => {
    const steps: { key: Step; label: string }[] = [
      { key: 'upload', label: t('step1') },
      { key: 'mapping', label: t('step2') },
      { key: 'options', label: t('step3') },
      { key: 'validate', label: t('step4') },
      { key: 'execute', label: t('step5') },
      { key: 'result', label: t('step6') },
    ];

    const currentIndex = steps.findIndex(s => s.key === currentStep);

    return (
      <div className="flex items-center justify-center gap-2 mb-6">
        {steps.map((step, index) => (
          <div key={step.key} className="flex items-center">
            <div
              className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
                index < currentIndex
                  ? 'bg-green-100 text-green-600 dark:bg-green-900 dark:text-green-400'
                  : index === currentIndex
                  ? 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400'
                  : 'bg-muted text-muted-foreground'
              }`}
            >
              {index < currentIndex ? (
                <CheckCircle className="w-5 h-5" />
              ) : (
                index + 1
              )}
            </div>
            {index < steps.length - 1 && (
              <div
                className={`w-12 h-0.5 mx-1 ${
                  index < currentIndex ? 'bg-green-400' : 'bg-muted'
                }`}
              />
            )}
          </div>
        ))}
      </div>
    );
  };

  // Render upload step
  const renderUploadStep = () => (
    <div className="space-y-4">
      <div
        className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:border-primary transition-colors"
        onDrop={handleDrop}
        onDragOver={e => e.preventDefault()}
        onClick={() => document.getElementById('file-input')?.click()}
      >
        {isUploading ? (
          <div className="flex flex-col items-center">
            <Loader2 className="h-12 w-12 animate-spin text-muted-foreground" />
            <p className="mt-2 text-sm text-muted-foreground">Uploading...</p>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <Upload className="h-12 w-12 text-muted-foreground" />
            <p className="mt-2 text-sm text-muted-foreground">{t('dragDrop')}</p>
            <Button variant="outline" className="mt-4">
              {t('selectFile')}
            </Button>
          </div>
        )}
        <input
          id="file-input"
          type="file"
          accept=".csv"
          className="hidden"
          onChange={handleFileSelect}
        />
      </div>

      {uploadError && (
        <div className="flex items-center gap-2 p-3 bg-destructive/10 text-destructive rounded-md">
          <AlertTriangle className="h-4 w-4" />
          <span className="text-sm">{uploadError}</span>
        </div>
      )}

      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <div className="space-y-1">
          <p>{t('supportedFormats')}</p>
          <p>{t('maxFileSize')}</p>
          <p>{t('maxRows')}</p>
        </div>
        <Button variant="outline" size="sm" onClick={handleDownloadTemplate}>
          <Download className="h-4 w-4 mr-2" />
          {t('downloadTemplate')}
        </Button>
      </div>
    </div>
  );

  // Render mapping step
  const renderMappingStep = () => {
    if (!uploadResult) return null;

    return (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">{t('mappingDescription')}</p>

        <div className="border rounded-lg overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('fileColumn')}</TableHead>
                <TableHead>{t('systemField')}</TableHead>
                <TableHead>{t('preview')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {columnMapping.map((mapping, index) => (
                <TableRow key={mapping.file_column}>
                  <TableCell className="font-medium">{mapping.file_column}</TableCell>
                  <TableCell>
                    <Select
                      value={mapping.system_field || '_ignore'}
                      onValueChange={value => handleMappingChange(mapping.file_column, value)}
                    >
                      <SelectTrigger className="w-48">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="_ignore">{t('ignore')}</SelectItem>
                        {SYSTEM_FIELDS.map(field => (
                          <SelectItem
                            key={field.value}
                            value={field.value}
                            disabled={columnMapping.some(
                              m => m.system_field === field.value && m.file_column !== mapping.file_column
                            )}
                          >
                            {t(field.label)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {uploadResult.preview[0]?.[mapping.file_column] || '-'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {!hasRequiredFields() && (
          <div className="flex items-center gap-2 p-3 bg-yellow-50 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400 rounded-md">
            <AlertCircle className="h-4 w-4" />
            <span className="text-sm">{t('requiredFieldsNote')}</span>
          </div>
        )}
      </div>
    );
  };

  // Render options step
  const renderOptionsStep = () => (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label>{t('errorHandling')}</Label>
        <Select
          value={options.error_handling}
          onValueChange={value => setOptions({ ...options, error_handling: value as 'strict' | 'skip' })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="skip">{t('errorHandlingSkip')}</SelectItem>
            <SelectItem value="strict">{t('errorHandlingStrict')}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>{t('defaultStatus')}</Label>
        <Select
          value={options.default_status}
          onValueChange={value => setOptions({ ...options, default_status: value })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="active">{tCommon('active')}</SelectItem>
            <SelectItem value="inactive">{tCommon('inactive')}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>{t('defaultCurrency')}</Label>
        <Select
          value={options.default_currency}
          onValueChange={value => setOptions({ ...options, default_currency: value })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="EUR">EUR</SelectItem>
            <SelectItem value="USD">USD</SelectItem>
            <SelectItem value="GBP">GBP</SelectItem>
            <SelectItem value="CHF">CHF</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );

  // Render validate step
  const renderValidateStep = () => {
    if (!validationResult) return null;

    return (
      <div className="space-y-4">
        {/* Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 bg-muted rounded-lg text-center">
            <p className="text-2xl font-bold">{validationResult.total_rows}</p>
            <p className="text-sm text-muted-foreground">{t('totalRows')}</p>
          </div>
          <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg text-center">
            <p className="text-2xl font-bold text-green-600 dark:text-green-400">
              {validationResult.summary.will_create}
            </p>
            <p className="text-sm text-muted-foreground">{t('willCreate')}</p>
          </div>
          <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg text-center">
            <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
              {validationResult.summary.will_skip_duplicates}
            </p>
            <p className="text-sm text-muted-foreground">{t('willSkipDuplicates')}</p>
          </div>
          <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg text-center">
            <p className="text-2xl font-bold text-red-600 dark:text-red-400">
              {validationResult.error_count}
            </p>
            <p className="text-sm text-muted-foreground">{t('errors')}</p>
          </div>
        </div>

        {/* Errors */}
        {validationResult.errors.length > 0 && (
          <div className="space-y-2">
            <h4 className="font-medium text-destructive">{t('validationErrors')}</h4>
            <div className="max-h-48 overflow-auto border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">{t('rowNumber')}</TableHead>
                    <TableHead>{t('errorColumn')}</TableHead>
                    <TableHead>{t('errorValue')}</TableHead>
                    <TableHead>{t('errorMessage')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {validationResult.errors.slice(0, 20).map((error, index) => (
                    <TableRow key={index}>
                      <TableCell>{error.row}</TableCell>
                      <TableCell>{error.column}</TableCell>
                      <TableCell className="max-w-32 truncate">{error.value}</TableCell>
                      <TableCell>{error.message}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            {validationResult.errors.length > 20 && (
              <p className="text-sm text-muted-foreground">
                ...and {validationResult.errors.length - 20} more errors
              </p>
            )}
          </div>
        )}

        {/* Warnings */}
        {validationResult.warnings.length > 0 && (
          <div className="space-y-2">
            <h4 className="font-medium text-yellow-600 dark:text-yellow-400">{t('validationWarnings')}</h4>
            <div className="max-h-32 overflow-auto border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">{t('rowNumber')}</TableHead>
                    <TableHead>{t('errorMessage')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {validationResult.warnings.slice(0, 10).map((warning, index) => (
                    <TableRow key={index}>
                      <TableCell>{warning.row}</TableCell>
                      <TableCell>{warning.message}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}

        {!validationResult.can_proceed && (
          <div className="flex items-center gap-2 p-3 bg-destructive/10 text-destructive rounded-md">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-sm">Cannot proceed due to errors</span>
          </div>
        )}
      </div>
    );
  };

  // Render execute step
  const renderExecuteStep = () => (
    <div className="flex flex-col items-center justify-center py-8 space-y-4">
      {isExecuting ? (
        <>
          <Loader2 className="h-12 w-12 animate-spin text-primary" />
          <p className="text-lg font-medium">{t('executing')}</p>
          {jobStatus && (
            <div className="w-full space-y-2">
              <Progress value={jobStatus.progress} />
              <p className="text-sm text-center text-muted-foreground">
                {jobStatus.processed_rows} / {jobStatus.total_rows} rows
              </p>
            </div>
          )}
        </>
      ) : (
        <>
          <FileSpreadsheet className="h-12 w-12 text-muted-foreground" />
          <p className="text-lg font-medium">{t('executeDescription')}</p>
          {validationResult && (
            <p className="text-sm text-muted-foreground">
              {validationResult.summary.will_create} licenses will be created
            </p>
          )}
        </>
      )}

      {executeError && (
        <div className="flex items-center gap-2 p-3 bg-destructive/10 text-destructive rounded-md w-full">
          <AlertTriangle className="h-4 w-4" />
          <span className="text-sm">{executeError}</span>
        </div>
      )}
    </div>
  );

  // Render result step
  const renderResultStep = () => {
    if (!jobStatus) return null;

    const isSuccess = jobStatus.status === 'completed';

    return (
      <div className="flex flex-col items-center justify-center py-8 space-y-4">
        {isSuccess ? (
          <CheckCircle className="h-16 w-16 text-green-500" />
        ) : (
          <AlertTriangle className="h-16 w-16 text-destructive" />
        )}

        <h3 className="text-xl font-semibold">
          {isSuccess ? t('resultTitle') : 'Import Failed'}
        </h3>

        <div className="grid grid-cols-3 gap-4 w-full max-w-sm">
          <div className="text-center">
            <p className="text-2xl font-bold text-green-600">{jobStatus.created}</p>
            <p className="text-sm text-muted-foreground">{t('created')}</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-yellow-600">{jobStatus.skipped}</p>
            <p className="text-sm text-muted-foreground">{t('skipped')}</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-red-600">{jobStatus.errors}</p>
            <p className="text-sm text-muted-foreground">{t('errors')}</p>
          </div>
        </div>
      </div>
    );
  };

  // Get current step content
  const renderCurrentStep = () => {
    switch (currentStep) {
      case 'upload':
        return renderUploadStep();
      case 'mapping':
        return renderMappingStep();
      case 'options':
        return renderOptionsStep();
      case 'validate':
        return renderValidateStep();
      case 'execute':
        return renderExecuteStep();
      case 'result':
        return renderResultStep();
    }
  };

  // Get step title
  const getStepTitle = () => {
    switch (currentStep) {
      case 'upload':
        return t('uploadTitle');
      case 'mapping':
        return t('mappingTitle');
      case 'options':
        return t('optionsTitle');
      case 'validate':
        return t('validateTitle');
      case 'execute':
        return t('executeTitle');
      case 'result':
        return t('resultTitle');
    }
  };

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

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t('title')}</DialogTitle>
          <DialogDescription>{getStepTitle()}</DialogDescription>
        </DialogHeader>

        {renderStepIndicator()}
        {renderCurrentStep()}

        <DialogFooter className="flex justify-between">
          <div>
            {currentStep !== 'upload' && currentStep !== 'result' && (
              <Button variant="outline" onClick={handleBack} disabled={isValidating || isExecuting}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                {t('back')}
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            {currentStep === 'result' ? (
              <>
                <Button variant="outline" onClick={() => handleOpenChange(false)}>
                  {tCommon('close')}
                </Button>
                <Button onClick={resetState}>
                  {t('startNew')}
                </Button>
              </>
            ) : (
              <>
                <Button variant="outline" onClick={() => handleOpenChange(false)}>
                  {t('cancel')}
                </Button>
                {currentStep !== 'upload' && (
                  <Button
                    onClick={handleNext}
                    disabled={!canGoNext() || isValidating || isExecuting}
                  >
                    {isValidating || isExecuting ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <ArrowRight className="h-4 w-4 mr-2" />
                    )}
                    {currentStep === 'execute' ? t('execute') : t('next')}
                  </Button>
                )}
              </>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
