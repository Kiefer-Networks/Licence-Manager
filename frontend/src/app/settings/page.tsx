'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { AppLayout } from '@/components/layout/app-layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
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
import { api, PaymentMethod, PaymentMethodCreate, PaymentMethodDetails, NotificationRule, NOTIFICATION_EVENT_TYPES, ThresholdSettings } from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';
import { Plus, Pencil, Trash2, CheckCircle2, XCircle, Loader2, Globe, X, CreditCard, Landmark, Wallet, AlertTriangle, MessageSquare, Bell, Send, Hash, Power, Settings2, Download, HardDrive, Info } from 'lucide-react';
import { BackupExportDialog } from '@/components/backup';
import { Textarea } from '@/components/ui/textarea';

export default function SettingsPage() {
  const t = useTranslations('settings');
  const tCommon = useTranslations('common');
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Company Domains state
  const [companyDomains, setCompanyDomains] = useState<string[]>([]);
  const [newDomain, setNewDomain] = useState('');
  const [savingDomains, setSavingDomains] = useState(false);

  // Payment Methods state
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [paymentMethodDialogOpen, setPaymentMethodDialogOpen] = useState(false);
  const [editingPaymentMethod, setEditingPaymentMethod] = useState<PaymentMethod | null>(null);
  const [savingPaymentMethod, setSavingPaymentMethod] = useState(false);

  // Slack/Notification state
  const [slackBotToken, setSlackBotToken] = useState('');
  const [slackConfigured, setSlackConfigured] = useState(false);
  const [savingSlack, setSavingSlack] = useState(false);
  const [testingSlack, setTestingSlack] = useState(false);
  const [testChannel, setTestChannel] = useState('');
  const [notificationRules, setNotificationRules] = useState<NotificationRule[]>([]);
  const [ruleDialogOpen, setRuleDialogOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<NotificationRule | null>(null);
  const [ruleForm, setRuleForm] = useState({
    event_type: '',
    slack_channel: '',
    template: '',
  });
  const [paymentMethodForm, setPaymentMethodForm] = useState({
    name: '',
    type: 'credit_card',
    card_holder: '',
    card_last_four: '',
    expiry_month: '',
    expiry_year: '',
    bank_name: '',
    account_holder: '',
    iban_last_four: '',
    provider_name: '',
    notes: '',
    is_default: false,
  });

  // Threshold Settings state
  const [thresholds, setThresholds] = useState<ThresholdSettings>({
    inactive_days: 30,
    expiring_days: 90,
    low_utilization_percent: 70,
    cost_increase_percent: 20,
    max_unassigned_licenses: 10,
  });
  const [savingThresholds, setSavingThresholds] = useState(false);

  // Backup state
  const [backupExportDialogOpen, setBackupExportDialogOpen] = useState(false);

  useEffect(() => {
    Promise.all([
      fetchCompanyDomains(),
      fetchPaymentMethods(),
      fetchSlackConfig(),
      fetchNotificationRules(),
      fetchThresholdSettings(),
    ]).finally(() => setLoading(false));
  }, []);

  async function fetchCompanyDomains() {
    try {
      const domains = await api.getCompanyDomains();
      setCompanyDomains(domains);
    } catch (error) {
      handleSilentError('fetchCompanyDomains', error);
    }
  }

  async function fetchPaymentMethods() {
    try {
      const data = await api.getPaymentMethods();
      setPaymentMethods(data.items);
    } catch (error) {
      handleSilentError('fetchPaymentMethods', error);
    }
  }

  async function fetchSlackConfig() {
    try {
      const config = await api.getSlackConfig();
      setSlackConfigured(config.configured);
    } catch (error) {
      handleSilentError('fetchSlackConfig', error);
    }
  }

  async function fetchNotificationRules() {
    try {
      const rules = await api.getNotificationRules();
      setNotificationRules(rules);
    } catch (error) {
      handleSilentError('fetchNotificationRules', error);
    }
  }

  async function fetchThresholdSettings() {
    try {
      const settings = await api.getThresholdSettings();
      if (settings) {
        setThresholds({
          inactive_days: settings.inactive_days ?? 30,
          expiring_days: settings.expiring_days ?? 90,
          low_utilization_percent: settings.low_utilization_percent ?? 70,
          cost_increase_percent: settings.cost_increase_percent ?? 20,
          max_unassigned_licenses: settings.max_unassigned_licenses ?? 10,
        });
      }
    } catch (error) {
      handleSilentError('fetchThresholdSettings', error);
    }
  }

  const handleSaveThresholds = async () => {
    setSavingThresholds(true);
    try {
      await api.updateThresholdSettings(thresholds);
      showToast('success', t('thresholdsUpdated'));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToSave');
      showToast('error', message);
    } finally {
      setSavingThresholds(false);
    }
  };

  const showToast = (type: 'success' | 'error', text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 3000);
  };

  // Company Domains handlers
  const handleAddDomain = () => {
    const domain = newDomain.trim().toLowerCase();
    if (!domain) return;
    if (companyDomains.includes(domain)) {
      showToast('error', t('domainAlreadyExists'));
      return;
    }
    setCompanyDomains([...companyDomains, domain]);
    setNewDomain('');
  };

  const handleRemoveDomain = (domain: string) => {
    setCompanyDomains(companyDomains.filter((d) => d !== domain));
  };

  const handleSaveDomains = async () => {
    setSavingDomains(true);
    try {
      await api.setCompanyDomains(companyDomains);
      showToast('success', t('companyDomainsSaved'));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToSaveDomains');
      showToast('error', message);
    } finally {
      setSavingDomains(false);
    }
  };

  // Payment Methods handlers
  const resetPaymentMethodForm = () => {
    setPaymentMethodForm({
      name: '',
      type: 'credit_card',
      card_holder: '',
      card_last_four: '',
      expiry_month: '',
      expiry_year: '',
      bank_name: '',
      account_holder: '',
      iban_last_four: '',
      provider_name: '',
      notes: '',
      is_default: false,
    });
  };

  const handleOpenPaymentMethodDialog = (method?: PaymentMethod) => {
    if (method) {
      setEditingPaymentMethod(method);
      setPaymentMethodForm({
        name: method.name,
        type: method.type,
        card_holder: method.details.card_holder || '',
        card_last_four: method.details.card_last_four || '',
        expiry_month: method.details.expiry_month || '',
        expiry_year: method.details.expiry_year || '',
        bank_name: method.details.bank_name || '',
        account_holder: method.details.account_holder || '',
        iban_last_four: method.details.iban_last_four || '',
        provider_name: method.details.provider_name || '',
        notes: method.notes || '',
        is_default: method.is_default,
      });
    } else {
      setEditingPaymentMethod(null);
      resetPaymentMethodForm();
    }
    setPaymentMethodDialogOpen(true);
  };

  const handleSavePaymentMethod = async () => {
    setSavingPaymentMethod(true);
    try {
      const details: PaymentMethodDetails = {};

      if (paymentMethodForm.type === 'credit_card') {
        details.cardholder_name = paymentMethodForm.card_holder;
        details.card_last_four = paymentMethodForm.card_last_four;
        details.card_expiry_month = paymentMethodForm.expiry_month ? parseInt(paymentMethodForm.expiry_month) : undefined;
        details.card_expiry_year = paymentMethodForm.expiry_year ? parseInt(paymentMethodForm.expiry_year) : undefined;
      } else if (paymentMethodForm.type === 'bank_account') {
        details.bank_name = paymentMethodForm.bank_name;
        details.account_holder_name = paymentMethodForm.account_holder;
        details.account_last_four = paymentMethodForm.iban_last_four;
      } else {
        details.provider_name = paymentMethodForm.provider_name;
      }

      const data: PaymentMethodCreate = {
        name: paymentMethodForm.name,
        type: paymentMethodForm.type,
        details,
        is_default: paymentMethodForm.is_default,
        notes: paymentMethodForm.notes || undefined,
      };

      if (editingPaymentMethod) {
        await api.updatePaymentMethod(editingPaymentMethod.id, data);
        showToast('success', t('paymentMethodUpdated'));
      } else {
        await api.createPaymentMethod(data);
        showToast('success', t('paymentMethodAdded'));
      }

      await fetchPaymentMethods();
      setPaymentMethodDialogOpen(false);
      resetPaymentMethodForm();
      setEditingPaymentMethod(null);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToSavePaymentMethod');
      showToast('error', message);
    } finally {
      setSavingPaymentMethod(false);
    }
  };

  const handleDeletePaymentMethod = async (id: string) => {
    try {
      await api.deletePaymentMethod(id);
      await fetchPaymentMethods();
      showToast('success', t('paymentMethodDeleted'));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToDeletePaymentMethod');
      showToast('error', message);
    }
  };

  // Slack handlers
  const handleSaveSlackConfig = async () => {
    if (!slackBotToken.trim()) {
      showToast('error', t('enterSlackToken'));
      return;
    }
    setSavingSlack(true);
    try {
      await api.setSlackConfig({ bot_token: slackBotToken });
      setSlackConfigured(true);
      setSlackBotToken('');
      showToast('success', t('slackConfigSaved'));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToSaveSlackConfig');
      showToast('error', message);
    } finally {
      setSavingSlack(false);
    }
  };

  const handleTestSlack = async () => {
    if (!testChannel.trim()) {
      showToast('error', t('enterChannelName'));
      return;
    }
    setTestingSlack(true);
    try {
      const result = await api.testSlackNotification(testChannel.startsWith('#') ? testChannel : `#${testChannel}`);
      if (result.success) {
        showToast('success', result.message);
      } else {
        showToast('error', result.message);
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToSendTest');
      showToast('error', message);
    } finally {
      setTestingSlack(false);
    }
  };

  // Notification rule handlers
  const handleOpenRuleDialog = (rule?: NotificationRule) => {
    if (rule) {
      setEditingRule(rule);
      setRuleForm({
        event_type: rule.event_type,
        slack_channel: rule.slack_channel,
        template: rule.template || '',
      });
    } else {
      setEditingRule(null);
      setRuleForm({ event_type: '', slack_channel: '', template: '' });
    }
    setRuleDialogOpen(true);
  };

  const handleSaveRule = async () => {
    if (!ruleForm.event_type || !ruleForm.slack_channel) {
      showToast('error', t('fillRequiredFields'));
      return;
    }
    try {
      const channel = ruleForm.slack_channel.startsWith('#') ? ruleForm.slack_channel : `#${ruleForm.slack_channel}`;
      if (editingRule) {
        await api.updateNotificationRule(editingRule.id, {
          slack_channel: channel,
          template: ruleForm.template || undefined,
        });
        showToast('success', t('ruleUpdated'));
      } else {
        await api.createNotificationRule({
          event_type: ruleForm.event_type,
          slack_channel: channel,
          template: ruleForm.template || undefined,
        });
        showToast('success', t('ruleCreatedSuccess'));
      }
      await fetchNotificationRules();
      setRuleDialogOpen(false);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToSaveRule');
      showToast('error', message);
    }
  };

  const handleToggleRule = async (rule: NotificationRule) => {
    try {
      await api.updateNotificationRule(rule.id, { enabled: !rule.enabled });
      await fetchNotificationRules();
      showToast('success', rule.enabled ? t('ruleDisabled') : t('ruleEnabled'));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToUpdateRule');
      showToast('error', message);
    }
  };

  const handleDeleteRule = async (id: string) => {
    try {
      await api.deleteNotificationRule(id);
      await fetchNotificationRules();
      showToast('success', t('ruleDeleted'));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToDeleteRule');
      showToast('error', message);
    }
  };

  const getPaymentMethodIcon = (type: string) => {
    switch (type) {
      case 'credit_card':
        return <CreditCard className="h-4 w-4" />;
      case 'bank_account':
        return <Landmark className="h-4 w-4" />;
      default:
        return <Wallet className="h-4 w-4" />;
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-96">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Toast */}
        {toast && (
          <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
            toast.type === 'success' ? 'bg-zinc-900 text-white' : 'bg-red-600 text-white'
          }`}>
            {toast.type === 'success' ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
            {toast.text}
          </div>
        )}

        {/* Header */}
        <div className="pt-2">
          <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
          <p className="text-muted-foreground text-sm mt-0.5">{t('general')}</p>
        </div>

        {/* Company Domains Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-medium">{t('companyDomains')}</h2>
            </div>
          </div>

          <div className="border rounded-lg bg-white p-4 space-y-4">
            <p className="text-xs text-muted-foreground">
              {t('companyDomainsDescription')}
            </p>

            <div className="flex gap-2">
              <Input
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                placeholder={t('domainPlaceholder')}
                className="flex-1"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddDomain();
                  }
                }}
              />
              <Button variant="outline" size="sm" onClick={handleAddDomain}>
                <Plus className="h-3.5 w-3.5 mr-1.5" />
                {tCommon('add')}
              </Button>
            </div>

            {companyDomains.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {companyDomains.map((domain) => (
                  <Badge
                    key={domain}
                    variant="secondary"
                    className="bg-zinc-100 text-zinc-700 pr-1.5 flex items-center gap-1"
                  >
                    {domain}
                    <button
                      onClick={() => handleRemoveDomain(domain)}
                      className="ml-1 hover:bg-zinc-200 rounded p-0.5"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground italic">{t('noDomainsConfigured')}</p>
            )}

            <div className="pt-2 border-t">
              <Button size="sm" onClick={handleSaveDomains} disabled={savingDomains}>
                {savingDomains ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                {tCommon('save')}
              </Button>
            </div>
          </div>
        </section>

        {/* Payment Methods Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-medium">{t('paymentMethods')}</h2>
            </div>
            <Button size="sm" variant="outline" onClick={() => handleOpenPaymentMethodDialog()}>
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              {t('addPaymentMethod')}
            </Button>
          </div>

          {paymentMethods.length > 0 ? (
            <div className="border rounded-lg bg-white divide-y">
              {paymentMethods.map((method) => (
                <div key={method.id} className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3">
                    <div className={`h-9 w-9 rounded-lg flex items-center justify-center ${
                      method.is_expiring ? 'bg-amber-50 text-amber-600' : 'bg-zinc-100 text-zinc-600'
                    }`}>
                      {getPaymentMethodIcon(method.type)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-sm">{method.name}</p>
                        {method.is_default && (
                          <Badge variant="secondary" className="text-xs">{t('default')}</Badge>
                        )}
                        {method.is_expiring && (
                          <Badge variant="outline" className="text-xs text-amber-600 border-amber-200 bg-amber-50">
                            <AlertTriangle className="h-3 w-3 mr-1" />
                            {method.days_until_expiry !== null && method.days_until_expiry !== undefined && method.days_until_expiry > 0
                              ? t('expiresInDays', { days: method.days_until_expiry })
                              : t('expiresSoon')}
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {method.type === 'credit_card' && method.details.card_last_four && (
                          <>•••• {method.details.card_last_four} · Expires {method.details.expiry_month}/{method.details.expiry_year}</>
                        )}
                        {method.type === 'bank_account' && method.details.bank_name && (
                          <>{method.details.bank_name} {method.details.iban_last_four && `· •••• ${method.details.iban_last_four}`}</>
                        )}
                        {method.type !== 'credit_card' && method.type !== 'bank_account' && method.details.provider_name && (
                          <>{method.details.provider_name}</>
                        )}
                        {method.type !== 'credit_card' && method.type !== 'bank_account' && !method.details.provider_name && (
                          <span className="capitalize">{method.type.replace('_', ' ')}</span>
                        )}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleOpenPaymentMethodDialog(method)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600" onClick={() => handleDeletePaymentMethod(method.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="border rounded-lg bg-white p-6 text-center">
              <CreditCard className="h-8 w-8 mx-auto text-zinc-300 mb-2" />
              <p className="text-sm text-muted-foreground">{t('noPaymentMethods')}</p>
              <p className="text-xs text-muted-foreground mt-1">{t('addPaymentMethodsNote')}</p>
            </div>
          )}
        </section>

        {/* Slack Integration Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-medium">{t('slackNotifications')}</h2>
            </div>
          </div>

          <div className="border rounded-lg bg-white p-4 space-y-4">
            <p className="text-xs text-muted-foreground">
              {t('slackDescription')}
            </p>

            {/* Slack Configuration */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <div className={`h-2 w-2 rounded-full ${slackConfigured ? 'bg-emerald-500' : 'bg-zinc-300'}`} />
                <span className="text-sm font-medium">{slackConfigured ? t('slackConnected') : t('slackNotConnected')}</span>
              </div>

              <div className="flex gap-2">
                <Input
                  type="password"
                  value={slackBotToken}
                  onChange={(e) => setSlackBotToken(e.target.value)}
                  placeholder={slackConfigured ? t('newTokenPlaceholder') : t('slackTokenPlaceholder')}
                  className="flex-1"
                />
                <Button variant="outline" size="sm" onClick={handleSaveSlackConfig} disabled={savingSlack || !slackBotToken.trim()}>
                  {savingSlack ? <Loader2 className="h-4 w-4 animate-spin" /> : t('saveToken')}
                </Button>
              </div>

              {slackConfigured && (
                <div className="flex gap-2 pt-2 border-t">
                  <div className="flex items-center gap-1 flex-1">
                    <Hash className="h-4 w-4 text-muted-foreground" />
                    <Input
                      value={testChannel}
                      onChange={(e) => setTestChannel(e.target.value)}
                      placeholder={t('channelPlaceholder')}
                      className="flex-1"
                    />
                  </div>
                  <Button variant="outline" size="sm" onClick={handleTestSlack} disabled={testingSlack || !testChannel.trim()}>
                    {testingSlack ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Send className="h-4 w-4 mr-1" /> {t('test')}</>}
                  </Button>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Notification Rules Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Bell className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-medium">{t('notificationRules')}</h2>
            </div>
            <Button size="sm" variant="outline" onClick={() => handleOpenRuleDialog()} disabled={!slackConfigured}>
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              {t('addRule')}
            </Button>
          </div>

          {!slackConfigured ? (
            <div className="border rounded-lg bg-zinc-50 p-4 text-center">
              <MessageSquare className="h-8 w-8 mx-auto text-zinc-300 mb-2" />
              <p className="text-sm text-muted-foreground">{t('configureSlackFirst')}</p>
            </div>
          ) : notificationRules.length > 0 ? (
            <div className="border rounded-lg bg-white divide-y">
              {notificationRules.map((rule) => {
                const eventType = NOTIFICATION_EVENT_TYPES.find(t => t.value === rule.event_type);
                return (
                  <div key={rule.id} className="flex items-center justify-between p-4">
                    <div className="flex items-center gap-3">
                      <div className={`h-9 w-9 rounded-lg flex items-center justify-center ${rule.enabled ? 'bg-emerald-50 text-emerald-600' : 'bg-zinc-100 text-zinc-400'}`}>
                        <Bell className="h-4 w-4" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-sm">{eventType?.label || rule.event_type}</p>
                          {!rule.enabled && (
                            <Badge variant="secondary" className="text-xs">{tCommon('disabled')}</Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {rule.slack_channel}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className={`h-8 w-8 ${rule.enabled ? 'text-emerald-600' : 'text-zinc-400'}`}
                        onClick={() => handleToggleRule(rule)}
                        title={rule.enabled ? t('disableRule') : t('enableRule')}
                      >
                        <Power className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleOpenRuleDialog(rule)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600" onClick={() => handleDeleteRule(rule.id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="border rounded-lg bg-white p-6 text-center">
              <Bell className="h-8 w-8 mx-auto text-zinc-300 mb-2" />
              <p className="text-sm text-muted-foreground">{t('noRulesConfigured')}</p>
            </div>
          )}
        </section>

        {/* Threshold Settings Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-medium">{t('warningThresholds')}</h2>
            </div>
          </div>

          <div className="border rounded-lg bg-white p-4 space-y-6">
            <p className="text-xs text-muted-foreground">
              {t('thresholdsDescription')}
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label className="text-xs font-medium">{t('inactiveLicenseThreshold')}</Label>
                <Input
                  type="number"
                  value={thresholds.inactive_days}
                  onChange={(e) => setThresholds({ ...thresholds, inactive_days: parseInt(e.target.value) || 0 })}
                  min={1}
                  max={365}
                />
                <p className="text-xs text-muted-foreground">
                  {t('inactiveLicenseThresholdHelp')}
                </p>
              </div>

              <div className="space-y-2">
                <Label className="text-xs font-medium">{t('contractExpiringSoon')}</Label>
                <Input
                  type="number"
                  value={thresholds.expiring_days}
                  onChange={(e) => setThresholds({ ...thresholds, expiring_days: parseInt(e.target.value) || 0 })}
                  min={1}
                  max={365}
                />
                <p className="text-xs text-muted-foreground">
                  {t('contractExpiringSoonHelp')}
                </p>
              </div>

              <div className="space-y-2">
                <Label className="text-xs font-medium">{t('lowUtilizationThreshold')}</Label>
                <Input
                  type="number"
                  value={thresholds.low_utilization_percent}
                  onChange={(e) => setThresholds({ ...thresholds, low_utilization_percent: parseInt(e.target.value) || 0 })}
                  min={1}
                  max={100}
                />
                <p className="text-xs text-muted-foreground">
                  {t('lowUtilizationThresholdHelp')}
                </p>
              </div>

              <div className="space-y-2">
                <Label className="text-xs font-medium">{t('costIncreaseAlert')}</Label>
                <Input
                  type="number"
                  value={thresholds.cost_increase_percent}
                  onChange={(e) => setThresholds({ ...thresholds, cost_increase_percent: parseInt(e.target.value) || 0 })}
                  min={1}
                  max={100}
                />
                <p className="text-xs text-muted-foreground">
                  {t('costIncreaseAlertHelp')}
                </p>
              </div>

              <div className="space-y-2">
                <Label className="text-xs font-medium">{t('maxUnassignedLicenses')}</Label>
                <Input
                  type="number"
                  value={thresholds.max_unassigned_licenses}
                  onChange={(e) => setThresholds({ ...thresholds, max_unassigned_licenses: parseInt(e.target.value) || 0 })}
                  min={0}
                  max={1000}
                />
                <p className="text-xs text-muted-foreground">
                  {t('maxUnassignedLicensesHelp')}
                </p>
              </div>
            </div>

            <div className="pt-4 border-t">
              <Button size="sm" onClick={handleSaveThresholds} disabled={savingThresholds}>
                {savingThresholds ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                {t('saveThresholds')}
              </Button>
            </div>
          </div>
        </section>

        {/* System Backup Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <HardDrive className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-medium">{t('systemBackup')}</h2>
            </div>
          </div>

          <div className="border rounded-lg bg-white p-4 space-y-4">
            <div className="flex items-start gap-3 p-3 rounded-lg bg-blue-50 text-blue-700">
              <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <div className="text-sm">
                <p>
                  {t('backupInfoDescription')}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3 p-3 rounded-lg bg-amber-50 text-amber-700">
              <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <div className="text-sm">
                <p className="font-medium">{t('importWarningTitle')}</p>
                <p className="text-xs mt-1">
                  {t('importWarningDescription')}
                </p>
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <Button
                variant="outline"
                onClick={() => setBackupExportDialogOpen(true)}
              >
                <Download className="h-4 w-4 mr-2" />
                {t('createBackupButton')}
              </Button>
            </div>
          </div>
        </section>
      </div>

      {/* Backup Dialog */}
      <BackupExportDialog
        open={backupExportDialogOpen}
        onOpenChange={setBackupExportDialogOpen}
        onSuccess={() => showToast('success', t('backupCreatedSuccess'))}
        onError={(error) => showToast('error', error)}
      />

      {/* Notification Rule Dialog */}
      <Dialog open={ruleDialogOpen} onOpenChange={setRuleDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingRule ? t('editNotificationRule') : t('addNotificationRule')}</DialogTitle>
            <DialogDescription>
              {editingRule ? t('editRuleDescription') : t('createRuleDescription')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-xs font-medium">{t('eventType')}</Label>
              <Select
                value={ruleForm.event_type}
                onValueChange={(v) => setRuleForm({ ...ruleForm, event_type: v })}
                disabled={!!editingRule}
              >
                <SelectTrigger>
                  <SelectValue placeholder={t('selectEventType')} />
                </SelectTrigger>
                <SelectContent>
                  {NOTIFICATION_EVENT_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      <div>
                        <span>{type.label}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {ruleForm.event_type && (
                <p className="text-xs text-muted-foreground">
                  {NOTIFICATION_EVENT_TYPES.find(t => t.value === ruleForm.event_type)?.description}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-medium">{t('slackChannel')}</Label>
              <div className="flex items-center gap-1">
                <Hash className="h-4 w-4 text-muted-foreground" />
                <Input
                  value={ruleForm.slack_channel.replace(/^#/, '')}
                  onChange={(e) => setRuleForm({ ...ruleForm, slack_channel: e.target.value })}
                  placeholder={t('channelPlaceholder')}
                  className="flex-1"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-medium">{t('customTemplate')}</Label>
              <Textarea
                value={ruleForm.template}
                onChange={(e) => setRuleForm({ ...ruleForm, template: e.target.value })}
                placeholder={t('leaveEmptyForDefault')}
                rows={3}
              />
              <p className="text-xs text-muted-foreground">
                {t('availableVariables')}: {'{{employee_name}}'}, {'{{employee_email}}'}, {'{{provider_name}}'}, {'{{license_count}}'}
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setRuleDialogOpen(false)}>{tCommon('cancel')}</Button>
            <Button onClick={handleSaveRule} disabled={!ruleForm.event_type || !ruleForm.slack_channel}>
              {editingRule ? tCommon('save') : tCommon('create')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Payment Method Dialog */}
      <Dialog open={paymentMethodDialogOpen} onOpenChange={setPaymentMethodDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingPaymentMethod ? t('editPaymentMethod') : t('addPaymentMethod')}</DialogTitle>
            <DialogDescription>
              {editingPaymentMethod ? t('editPaymentMethodDescription') : t('createPaymentMethodDescription')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-xs font-medium">{tCommon('name')}</Label>
              <Input
                value={paymentMethodForm.name}
                onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, name: e.target.value })}
                placeholder={t('paymentNamePlaceholder')}
              />
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-medium">{tCommon('type')}</Label>
              <Select
                value={paymentMethodForm.type}
                onValueChange={(v) => setPaymentMethodForm({ ...paymentMethodForm, type: v })}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="bank_account">{t('bankAccount')}</SelectItem>
                  <SelectItem value="credit_card">{t('creditCard')}</SelectItem>
                  <SelectItem value="invoice">{tCommon('invoice')}</SelectItem>
                  <SelectItem value="other">{t('otherPayment')}</SelectItem>
                  <SelectItem value="paypal">{t('paypal')}</SelectItem>
                  <SelectItem value="stripe">{t('stripe')}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {paymentMethodForm.type === 'credit_card' && (
              <>
                <div className="space-y-2">
                  <Label className="text-xs font-medium">{t('cardHolder')}</Label>
                  <Input
                    value={paymentMethodForm.card_holder}
                    onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, card_holder: e.target.value })}
                    placeholder={t('nameOnCard')}
                  />
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div className="space-y-2">
                    <Label className="text-xs font-medium">{t('lastFourDigits')}</Label>
                    <Input
                      value={paymentMethodForm.card_last_four}
                      onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, card_last_four: e.target.value.slice(0, 4) })}
                      placeholder="1234"
                      maxLength={4}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs font-medium">{t('expiryMonth')}</Label>
                    <Select
                      value={paymentMethodForm.expiry_month}
                      onValueChange={(v) => setPaymentMethodForm({ ...paymentMethodForm, expiry_month: v })}
                    >
                      <SelectTrigger><SelectValue placeholder="MM" /></SelectTrigger>
                      <SelectContent>
                        {Array.from({ length: 12 }, (_, i) => {
                          const m = String(i + 1).padStart(2, '0');
                          return <SelectItem key={m} value={m}>{m}</SelectItem>;
                        })}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs font-medium">{t('expiryYear')}</Label>
                    <Select
                      value={paymentMethodForm.expiry_year}
                      onValueChange={(v) => setPaymentMethodForm({ ...paymentMethodForm, expiry_year: v })}
                    >
                      <SelectTrigger><SelectValue placeholder="YY" /></SelectTrigger>
                      <SelectContent>
                        {Array.from({ length: 10 }, (_, i) => {
                          const y = String(new Date().getFullYear() + i).slice(-2);
                          return <SelectItem key={y} value={y}>{y}</SelectItem>;
                        })}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </>
            )}

            {paymentMethodForm.type === 'bank_account' && (
              <>
                <div className="space-y-2">
                  <Label className="text-xs font-medium">{t('bankName')}</Label>
                  <Input
                    value={paymentMethodForm.bank_name}
                    onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, bank_name: e.target.value })}
                    placeholder={t('bankNamePlaceholder')}
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label className="text-xs font-medium">{t('accountHolder')}</Label>
                    <Input
                      value={paymentMethodForm.account_holder}
                      onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, account_holder: e.target.value })}
                      placeholder={t('accountHolderName')}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-xs font-medium">{t('ibanLastFour')}</Label>
                    <Input
                      value={paymentMethodForm.iban_last_four}
                      onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, iban_last_four: e.target.value.slice(0, 4) })}
                      placeholder="1234"
                      maxLength={4}
                    />
                  </div>
                </div>
              </>
            )}

            {paymentMethodForm.type !== 'credit_card' && paymentMethodForm.type !== 'bank_account' && (
              <div className="space-y-2">
                <Label className="text-xs font-medium">{t('providerAccount')}</Label>
                <Input
                  value={paymentMethodForm.provider_name}
                  onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, provider_name: e.target.value })}
                  placeholder={t('accountEmailPlaceholder')}
                />
              </div>
            )}

            <div className="space-y-2">
              <Label className="text-xs font-medium">{t('notesOptional')}</Label>
              <Input
                value={paymentMethodForm.notes}
                onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, notes: e.target.value })}
                placeholder={t('anyAdditionalNotes')}
              />
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_default"
                checked={paymentMethodForm.is_default}
                onChange={(e) => setPaymentMethodForm({ ...paymentMethodForm, is_default: e.target.checked })}
                className="rounded border-zinc-300"
              />
              <Label htmlFor="is_default" className="text-xs font-medium cursor-pointer">{t('setAsDefaultPayment')}</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setPaymentMethodDialogOpen(false)}>{tCommon('cancel')}</Button>
            <Button onClick={handleSavePaymentMethod} disabled={!paymentMethodForm.name || savingPaymentMethod}>
              {savingPaymentMethod ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> {tCommon('loading')}</> : (editingPaymentMethod ? tCommon('save') : tCommon('add'))}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
