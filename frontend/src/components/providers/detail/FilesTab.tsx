'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Upload, Loader2, FileText, File, Eye, Download, Trash2 } from 'lucide-react';
import { api, ProviderFile } from '@/lib/api';

export interface FilesTabProps {
  providerId: string;
  files: ProviderFile[];
  uploadingFile: boolean;
  fileDescription: string;
  setFileDescription: (value: string) => void;
  fileCategory: string;
  setFileCategory: (value: string) => void;
  onFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDeleteFile: (fileId: string) => void;
  formatDate: (date: string | Date | null | undefined) => string;
  t: (key: string) => string;
  tCommon: (key: string) => string;
}

/**
 * Format file size in human-readable format.
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

/**
 * Files tab component for provider detail page.
 * Handles file uploads and displays uploaded documents.
 */
export function FilesTab({
  providerId,
  files,
  uploadingFile,
  fileDescription,
  setFileDescription,
  fileCategory,
  setFileCategory,
  onFileUpload,
  onDeleteFile,
  formatDate,
  t,
  tCommon,
}: FilesTabProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-medium">{t('documentsAndFiles')}</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Upload contracts, invoices, and other documents related to this provider.
          </p>
        </div>
      </div>

      {/* Upload Section */}
      <Card>
        <CardContent className="pt-4 pb-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">{t('category')}</Label>
              <Select value={fileCategory} onValueChange={setFileCategory}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="agreement">{t('agreement')}</SelectItem>
                  <SelectItem value="contract">{t('contract')}</SelectItem>
                  <SelectItem value="invoice">{t('invoice')}</SelectItem>
                  <SelectItem value="other">{t('other')}</SelectItem>
                  <SelectItem value="quote">{t('quote')}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5 md:col-span-2">
              <Label className="text-xs text-muted-foreground">{t('descriptionOptional')}</Label>
              <Input
                placeholder={t('optionalNotes')}
                value={fileDescription}
                onChange={(e) => setFileDescription(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label
                htmlFor="file-upload"
                className={`inline-flex items-center justify-center h-9 px-4 rounded-md text-sm font-medium cursor-pointer transition-colors ${
                  uploadingFile
                    ? 'bg-zinc-100 text-zinc-400 cursor-not-allowed'
                    : 'bg-zinc-900 text-white hover:bg-zinc-800'
                }`}
              >
                {uploadingFile ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    {tCommon('loading')}
                  </>
                ) : (
                  <>
                    <Upload className="h-4 w-4 mr-2" />
                    {t('uploadFile')}
                  </>
                )}
              </Label>
              <input
                id="file-upload"
                type="file"
                className="hidden"
                accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.bmp,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.odt,.ods,.odp"
                onChange={onFileUpload}
                disabled={uploadingFile}
              />
              <p className="text-xs text-muted-foreground">
                Allowed: PDF, Images (PNG, JPG, GIF), Office documents (Word, Excel, PowerPoint)
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Files List */}
      {files.length === 0 ? (
        <div className="border rounded-lg bg-white p-8 text-center text-muted-foreground">
          <FileText className="h-8 w-8 mx-auto mb-2 opacity-30" />
          <p className="text-sm">{t('noFilesUploaded')}</p>
          <p className="text-xs mt-1">{t('uploadDocumentsNote')}</p>
        </div>
      ) : (
        <div className="border rounded-lg bg-white overflow-hidden">
          <table className="w-full">
            <thead className="bg-zinc-50 border-b">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">{t('file')}</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">{t('category')}</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">{t('size')}</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-muted-foreground">{t('uploaded')}</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-muted-foreground">{t('actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {files.map((file) => (
                <tr key={file.id} className="hover:bg-zinc-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <File className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <p className="text-sm font-medium">{file.original_name}</p>
                        {file.description && (
                          <p className="text-xs text-muted-foreground">{file.description}</p>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant="outline" className="text-xs capitalize">
                      {file.category || 'other'}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {formatFileSize(file.file_size)}
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {formatDate(file.created_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {file.viewable && (
                        <a
                          href={api.getProviderFileViewUrl(providerId, file.id)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center justify-center h-7 w-7 rounded-md hover:bg-zinc-100 transition-colors"
                          title={t('viewInBrowser')}
                        >
                          <Eye className="h-3.5 w-3.5" />
                        </a>
                      )}
                      <a
                        href={api.getProviderFileDownloadUrl(providerId, file.id)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center justify-center h-7 w-7 rounded-md hover:bg-zinc-100 transition-colors"
                        title={tCommon('download')}
                      >
                        <Download className="h-3.5 w-3.5" />
                      </a>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-red-600"
                        onClick={() => onDeleteFile(file.id)}
                        title={tCommon('delete')}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
