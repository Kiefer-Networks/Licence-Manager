'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Key, Settings, Trash2, Loader2 } from 'lucide-react';
import {
  getProviderFields,
  getFieldLabel,
  TEXTAREA_FIELDS,
  isSecretField,
} from '@/lib/provider-fields';
import type { Provider, PaymentMethod } from '@/lib/api';

export interface SettingsTabProps {
  provider: Provider;
  isManual: boolean;
  settingsForm: {
    display_name: string;
    license_model: string;
    payment_method_id: string | null;
  };
  setSettingsForm: React.Dispatch<
    React.SetStateAction<{
      display_name: string;
      license_model: string;
      payment_method_id: string | null;
    }>
  >;
  savingSettings: boolean;
  onSaveSettings: () => Promise<void>;
  paymentMethods: PaymentMethod[];
  // Credentials
  publicCredentials: Record<string, string>;
  credentialsForm: Record<string, string>;
  setCredentialsForm: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  showCredentialsEdit: boolean;
  setShowCredentialsEdit: (value: boolean) => void;
  savingCredentials: boolean;
  onSaveCredentials: () => Promise<void>;
  onDeleteProvider: () => void;
  t: (key: string, params?: Record<string, string>) => string;
  tCommon: (key: string) => string;
}

/**
 * Settings tab component for provider detail page.
 * Handles general settings, credentials, and danger zone actions.
 */
export function SettingsTab({
  provider,
  isManual,
  settingsForm,
  setSettingsForm,
  savingSettings,
  onSaveSettings,
  paymentMethods,
  publicCredentials,
  credentialsForm,
  setCredentialsForm,
  showCredentialsEdit,
  setShowCredentialsEdit,
  savingCredentials,
  onSaveCredentials,
  onDeleteProvider,
  t,
  tCommon,
}: SettingsTabProps) {
  const licenseModelOptions = [
    { value: 'seat_based', label: t('seatBased') },
    { value: 'license_based', label: t('licenseBased') },
  ];

  return (
    <div className="max-w-xl space-y-6">
      {/* General Settings */}
      <GeneralSettingsCard
        settingsForm={settingsForm}
        setSettingsForm={setSettingsForm}
        savingSettings={savingSettings}
        onSaveSettings={onSaveSettings}
        paymentMethods={paymentMethods}
        licenseModelOptions={licenseModelOptions}
        t={t}
        tCommon={tCommon}
      />

      {/* Credentials */}
      {!isManual && (
        <CredentialsCard
          provider={provider}
          publicCredentials={publicCredentials}
          credentialsForm={credentialsForm}
          setCredentialsForm={setCredentialsForm}
          showCredentialsEdit={showCredentialsEdit}
          setShowCredentialsEdit={setShowCredentialsEdit}
          savingCredentials={savingCredentials}
          onSaveCredentials={onSaveCredentials}
          t={t}
          tCommon={tCommon}
        />
      )}

      {/* Danger Zone */}
      <DangerZoneCard
        provider={provider}
        onDeleteProvider={onDeleteProvider}
        t={t}
      />
    </div>
  );
}

/**
 * General settings card sub-component.
 */
function GeneralSettingsCard({
  settingsForm,
  setSettingsForm,
  savingSettings,
  onSaveSettings,
  paymentMethods,
  licenseModelOptions,
  t,
  tCommon,
}: {
  settingsForm: SettingsTabProps['settingsForm'];
  setSettingsForm: SettingsTabProps['setSettingsForm'];
  savingSettings: boolean;
  onSaveSettings: () => Promise<void>;
  paymentMethods: PaymentMethod[];
  licenseModelOptions: Array<{ value: string; label: string }>;
  t: (key: string) => string;
  tCommon: (key: string) => string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{t('generalSettings')}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label className="text-xs font-medium">{t('displayName')}</Label>
          <Input
            value={settingsForm.display_name}
            onChange={(e) =>
              setSettingsForm({ ...settingsForm, display_name: e.target.value })
            }
          />
        </div>
        <div className="space-y-2">
          <Label className="text-xs font-medium">{t('licenseModel')}</Label>
          <Select
            value={settingsForm.license_model}
            onValueChange={(v) =>
              setSettingsForm({ ...settingsForm, license_model: v })
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {licenseModelOptions.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">{t('seatBasedDescription')}</p>
        </div>
        <div className="space-y-2">
          <Label className="text-xs font-medium">{t('paymentMethod')}</Label>
          <Select
            value={settingsForm.payment_method_id || '_none'}
            onValueChange={(v) =>
              setSettingsForm({
                ...settingsForm,
                payment_method_id: v === '_none' ? null : v,
              })
            }
          >
            <SelectTrigger>
              <SelectValue placeholder={t('selectPaymentMethod')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="_none">{t('noPaymentMethod')}</SelectItem>
              {paymentMethods.map((pm) => (
                <SelectItem key={pm.id} value={pm.id}>
                  {pm.name} {pm.is_default && `(${t('default')})`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">{t('paymentMethodDescription')}</p>
        </div>
        <Button onClick={onSaveSettings} disabled={savingSettings}>
          {savingSettings ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
          {t('saveSettings')}
        </Button>
      </CardContent>
    </Card>
  );
}

/**
 * Credentials card sub-component.
 */
function CredentialsCard({
  provider,
  publicCredentials,
  credentialsForm,
  setCredentialsForm,
  showCredentialsEdit,
  setShowCredentialsEdit,
  savingCredentials,
  onSaveCredentials,
  t,
  tCommon,
}: {
  provider: Provider;
  publicCredentials: Record<string, string>;
  credentialsForm: Record<string, string>;
  setCredentialsForm: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  showCredentialsEdit: boolean;
  setShowCredentialsEdit: (value: boolean) => void;
  savingCredentials: boolean;
  onSaveCredentials: () => Promise<void>;
  t: (key: string) => string;
  tCommon: (key: string) => string;
}) {
  const fields = getProviderFields(provider.name);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          <Key className="h-4 w-4" />
          {t('credentials')}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {!showCredentialsEdit ? (
          <>
            <p className="text-sm text-muted-foreground">{t('credentialsDescription')}</p>
            <div className="space-y-2">
              {fields.map((field) => (
                <div
                  key={field}
                  className="flex items-center justify-between py-2 border-b border-zinc-100 last:border-0"
                >
                  <span className="text-sm font-medium">{getFieldLabel(field, t)}</span>
                  <span className="text-sm text-muted-foreground font-mono">
                    {isSecretField(field)
                      ? '••••••••'
                      : publicCredentials[field] || t('configured')}
                  </span>
                </div>
              ))}
            </div>
            <Button variant="outline" onClick={() => setShowCredentialsEdit(true)}>
              <Settings className="h-4 w-4 mr-1.5" />
              {t('editCredentials')}
            </Button>
          </>
        ) : (
          <>
            <p className="text-sm text-muted-foreground">{t('editCredentialsDescription')}</p>
            <div className="space-y-3">
              {fields.map((field) => (
                <div key={field} className="space-y-1">
                  <Label className="text-xs font-medium">{getFieldLabel(field, t)}</Label>
                  {TEXTAREA_FIELDS.includes(field) ? (
                    <Textarea
                      value={credentialsForm[field] || ''}
                      onChange={(e) =>
                        setCredentialsForm({ ...credentialsForm, [field]: e.target.value })
                      }
                      placeholder={t('leaveEmptyToKeep')}
                      rows={4}
                      className="font-mono text-xs"
                    />
                  ) : (
                    <Input
                      type={isSecretField(field) ? 'password' : 'text'}
                      value={credentialsForm[field] || ''}
                      onChange={(e) =>
                        setCredentialsForm({ ...credentialsForm, [field]: e.target.value })
                      }
                      placeholder={t('leaveEmptyToKeep')}
                    />
                  )}
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <Button onClick={onSaveCredentials} disabled={savingCredentials}>
                {savingCredentials ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : null}
                {t('saveCredentials')}
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setShowCredentialsEdit(false);
                  setCredentialsForm({});
                }}
              >
                {tCommon('cancel')}
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Danger zone card sub-component.
 */
function DangerZoneCard({
  provider,
  onDeleteProvider,
  t,
}: {
  provider: Provider;
  onDeleteProvider: () => void;
  t: (key: string, params?: Record<string, string>) => string;
}) {
  return (
    <Card className="border-red-200">
      <CardHeader>
        <CardTitle className="text-sm text-red-600">{t('dangerZone')}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-3">{t('deleteProviderWarning')}</p>
        <Button
          variant="outline"
          className="text-red-600 border-red-200 hover:bg-red-50"
          onClick={onDeleteProvider}
        >
          <Trash2 className="h-4 w-4 mr-1.5" />
          {t('deleteProvider')}
        </Button>
      </CardContent>
    </Card>
  );
}
