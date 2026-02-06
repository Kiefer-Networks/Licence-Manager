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
import { api, NotificationRule, NOTIFICATION_EVENT_TYPES, ThresholdSettings, SmtpConfig, SmtpConfigRequest, PasswordPolicySettings, PasswordPolicyResponse, SystemNameSettings } from '@/lib/api';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { handleSilentError } from '@/lib/error-handler';
import { Plus, Pencil, Trash2, CheckCircle2, XCircle, Loader2, Globe, X, AlertTriangle, MessageSquare, Bell, Send, Hash, Power, Settings2, Download, HardDrive, Info, Mail, Server, Lock, ShieldCheck } from 'lucide-react';
import { BackupExportDialog } from '@/components/backup';
import { Textarea } from '@/components/ui/textarea';

export default function SettingsPage() {
  const t = useTranslations('settings');
  const tCommon = useTranslations('common');
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // System Name state
  const [systemName, setSystemName] = useState('License Management System');
  const [savingSystemName, setSavingSystemName] = useState(false);

  // Company Domains state
  const [companyDomains, setCompanyDomains] = useState<string[]>([]);
  const [newDomain, setNewDomain] = useState('');
  const [savingDomains, setSavingDomains] = useState(false);

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

  // Email/SMTP state
  const [emailConfig, setEmailConfig] = useState<SmtpConfig | null>(null);
  const [emailConfigured, setEmailConfigured] = useState(false);
  const [emailDialogOpen, setEmailDialogOpen] = useState(false);
  const [savingEmail, setSavingEmail] = useState(false);
  const [testingEmail, setTestingEmail] = useState(false);
  const [testEmailAddress, setTestEmailAddress] = useState('');
  const [emailForm, setEmailForm] = useState({
    host: '',
    port: 587,
    username: '',
    password: '',
    from_email: '',
    from_name: 'License Management System',
    use_tls: true,
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

  // Password Policy state
  const [passwordPolicy, setPasswordPolicy] = useState<PasswordPolicySettings>({
    min_length: 12,
    require_uppercase: true,
    require_lowercase: true,
    require_numbers: true,
    require_special_chars: true,
    expiry_days: 90,
    history_count: 5,
    max_failed_attempts: 5,
    lockout_duration_minutes: 15,
  });
  const [passwordPolicyWarning, setPasswordPolicyWarning] = useState(false);
  const [savingPasswordPolicy, setSavingPasswordPolicy] = useState(false);

  // Active tab state
  const [activeTab, setActiveTab] = useState('general');

  // Backup state
  const [backupExportDialogOpen, setBackupExportDialogOpen] = useState(false);

  useEffect(() => {
    Promise.all([
      fetchSystemName(),
      fetchCompanyDomains(),
      fetchSlackConfig(),
      fetchNotificationRules(),
      fetchThresholdSettings(),
      fetchEmailConfig(),
      fetchPasswordPolicy(),
    ]).finally(() => setLoading(false));
  }, []);

  async function fetchSystemName() {
    try {
      const settings = await api.getSystemName();
      setSystemName(settings.name);
    } catch (error) {
      handleSilentError('fetchSystemName', error);
    }
  }

  async function fetchCompanyDomains() {
    try {
      const domains = await api.getCompanyDomains();
      setCompanyDomains(domains);
    } catch (error) {
      handleSilentError('fetchCompanyDomains', error);
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

  async function fetchEmailConfig() {
    try {
      const config = await api.getEmailConfig();
      if (config && 'host' in config) {
        setEmailConfig(config as SmtpConfig);
        setEmailConfigured(true);
      } else if (config && 'is_configured' in config) {
        setEmailConfigured(config.is_configured);
      } else {
        setEmailConfigured(false);
      }
    } catch (error) {
      handleSilentError('fetchEmailConfig', error);
    }
  }

  const handleSaveSystemName = async () => {
    if (!systemName.trim()) {
      showToast('error', t('systemNameRequired'));
      return;
    }
    setSavingSystemName(true);
    try {
      await api.updateSystemName({ name: systemName.trim() });
      showToast('success', t('systemNameSaved'));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToSave');
      showToast('error', message);
    } finally {
      setSavingSystemName(false);
    }
  };

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

  async function fetchPasswordPolicy() {
    try {
      const policy = await api.getPasswordPolicy();
      setPasswordPolicy({
        min_length: policy.min_length,
        require_uppercase: policy.require_uppercase,
        require_lowercase: policy.require_lowercase,
        require_numbers: policy.require_numbers,
        require_special_chars: policy.require_special_chars,
        expiry_days: policy.expiry_days,
        history_count: policy.history_count,
        max_failed_attempts: policy.max_failed_attempts,
        lockout_duration_minutes: policy.lockout_duration_minutes,
      });
      setPasswordPolicyWarning(policy.length_warning);
    } catch (error) {
      handleSilentError('fetchPasswordPolicy', error);
    }
  }

  const handleSavePasswordPolicy = async () => {
    // Validate minimum length
    if (passwordPolicy.min_length < 8) {
      showToast('error', t('passwordPolicy.minLengthError'));
      return;
    }

    setSavingPasswordPolicy(true);
    try {
      const result = await api.updatePasswordPolicy(passwordPolicy);
      setPasswordPolicyWarning(result.length_warning);
      showToast('success', t('passwordPolicy.saved'));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToSave');
      showToast('error', message);
    } finally {
      setSavingPasswordPolicy(false);
    }
  };

  // Email configuration handlers
  const handleOpenEmailDialog = () => {
    if (emailConfig) {
      setEmailForm({
        host: emailConfig.host,
        port: emailConfig.port,
        username: emailConfig.username,
        password: '',
        from_email: emailConfig.from_email,
        from_name: emailConfig.from_name || 'License Management System',
        use_tls: emailConfig.use_tls,
      });
    } else {
      setEmailForm({
        host: '',
        port: 587,
        username: '',
        password: '',
        from_email: '',
        from_name: 'License Management System',
        use_tls: true,
      });
    }
    setEmailDialogOpen(true);
  };

  const handleSaveEmailConfig = async () => {
    if (!emailForm.host || !emailForm.username || !emailForm.from_email) {
      showToast('error', t('fillRequiredFields'));
      return;
    }
    // Password required for new config
    if (!emailConfigured && !emailForm.password) {
      showToast('error', t('emailPasswordRequired'));
      return;
    }
    setSavingEmail(true);
    try {
      const request: SmtpConfigRequest = {
        host: emailForm.host,
        port: emailForm.port,
        username: emailForm.username,
        password: emailForm.password || undefined,
        from_email: emailForm.from_email,
        from_name: emailForm.from_name,
        use_tls: emailForm.use_tls,
      };
      await api.setEmailConfig(request);
      await fetchEmailConfig();
      setEmailDialogOpen(false);
      showToast('success', t('emailConfigSaved'));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToSaveEmailConfig');
      showToast('error', message);
    } finally {
      setSavingEmail(false);
    }
  };

  const handleDeleteEmailConfig = async () => {
    try {
      await api.deleteEmailConfig();
      setEmailConfig(null);
      setEmailConfigured(false);
      showToast('success', t('emailConfigDeleted'));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToDeleteEmailConfig');
      showToast('error', message);
    }
  };

  const handleTestEmail = async () => {
    if (!testEmailAddress.trim()) {
      showToast('error', t('enterTestEmailAddress'));
      return;
    }
    setTestingEmail(true);
    try {
      const result = await api.testEmail(testEmailAddress);
      if (result.success) {
        showToast('success', result.message);
      } else {
        showToast('error', result.message);
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToSendTestEmail');
      showToast('error', message);
    } finally {
      setTestingEmail(false);
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
          <p className="text-muted-foreground text-sm mt-0.5">{t('description')}</p>
        </div>

        {/* Tabs Navigation */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="general" className="flex items-center gap-2">
              <Settings2 className="h-4 w-4" />
              {t('tabs.general')}
            </TabsTrigger>
            <TabsTrigger value="security" className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4" />
              {t('tabs.security')}
            </TabsTrigger>
            <TabsTrigger value="integrations" className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              {t('tabs.integrations')}
            </TabsTrigger>
            <TabsTrigger value="system" className="flex items-center gap-2">
              <HardDrive className="h-4 w-4" />
              {t('tabs.system')}
            </TabsTrigger>
          </TabsList>

          {/* ============================================ */}
          {/* GENERAL TAB */}
          {/* ============================================ */}
          <TabsContent value="general" className="space-y-8 mt-6">

        {/* System Name Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-medium">{t('systemName')}</h2>
            </div>
          </div>

          <div className="border rounded-lg bg-white p-4 space-y-4">
            <p className="text-xs text-muted-foreground">
              {t('systemNameDescription')}
            </p>

            <div className="flex gap-2">
              <Input
                value={systemName}
                onChange={(e) => setSystemName(e.target.value)}
                placeholder="License Management System"
                className="flex-1"
              />
              <Button size="sm" onClick={handleSaveSystemName} disabled={savingSystemName}>
                {savingSystemName ? <Loader2 className="h-4 w-4 animate-spin" /> : tCommon('save')}
              </Button>
            </div>
          </div>
        </section>

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

          </TabsContent>

          {/* ============================================ */}
          {/* SECURITY TAB */}
          {/* ============================================ */}
          <TabsContent value="security" className="space-y-8 mt-6">

        {/* Password Policy Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Lock className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-medium">{t('passwordPolicy.title')}</h2>
            </div>
          </div>

          <div className="border rounded-lg bg-white p-4 space-y-6">
            <p className="text-xs text-muted-foreground">
              {t('passwordPolicy.description')}
            </p>

            {/* Warning for min_length < 16 */}
            {passwordPolicyWarning && (
              <div className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-amber-800">
                  <p className="font-medium">{t('passwordPolicy.lengthWarningTitle')}</p>
                  <p className="text-xs mt-1">{t('passwordPolicy.lengthWarningDescription')}</p>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Minimum Length */}
              <div className="space-y-2">
                <Label htmlFor="min-length">{t('passwordPolicy.minLength')}</Label>
                <Input
                  id="min-length"
                  type="number"
                  value={passwordPolicy.min_length}
                  onChange={(e) => {
                    const value = parseInt(e.target.value) || 8;
                    setPasswordPolicy({ ...passwordPolicy, min_length: Math.max(8, value) });
                    setPasswordPolicyWarning(value < 16);
                  }}
                  min={8}
                  max={128}
                />
                <p className="text-xs text-muted-foreground">{t('passwordPolicy.minLengthHint')}</p>
              </div>

              {/* Password Expiry */}
              <div className="space-y-2">
                <Label htmlFor="expiry-days">{t('passwordPolicy.expiryDays')}</Label>
                <Input
                  id="expiry-days"
                  type="number"
                  value={passwordPolicy.expiry_days}
                  onChange={(e) => setPasswordPolicy({ ...passwordPolicy, expiry_days: parseInt(e.target.value) || 0 })}
                  min={0}
                  max={365}
                />
                <p className="text-xs text-muted-foreground">{t('passwordPolicy.expiryDaysHint')}</p>
              </div>

              {/* History Count */}
              <div className="space-y-2">
                <Label htmlFor="history-count">{t('passwordPolicy.historyCount')}</Label>
                <Input
                  id="history-count"
                  type="number"
                  value={passwordPolicy.history_count}
                  onChange={(e) => setPasswordPolicy({ ...passwordPolicy, history_count: parseInt(e.target.value) || 0 })}
                  min={0}
                  max={24}
                />
                <p className="text-xs text-muted-foreground">{t('passwordPolicy.historyCountHint')}</p>
              </div>

              {/* Max Failed Attempts */}
              <div className="space-y-2">
                <Label htmlFor="max-attempts">{t('passwordPolicy.maxFailedAttempts')}</Label>
                <Input
                  id="max-attempts"
                  type="number"
                  value={passwordPolicy.max_failed_attempts}
                  onChange={(e) => setPasswordPolicy({ ...passwordPolicy, max_failed_attempts: parseInt(e.target.value) || 5 })}
                  min={1}
                  max={20}
                />
                <p className="text-xs text-muted-foreground">{t('passwordPolicy.maxFailedAttemptsHint')}</p>
              </div>

              {/* Lockout Duration */}
              <div className="space-y-2">
                <Label htmlFor="lockout-duration">{t('passwordPolicy.lockoutDuration')}</Label>
                <Input
                  id="lockout-duration"
                  type="number"
                  value={passwordPolicy.lockout_duration_minutes}
                  onChange={(e) => setPasswordPolicy({ ...passwordPolicy, lockout_duration_minutes: parseInt(e.target.value) || 15 })}
                  min={1}
                  max={1440}
                />
                <p className="text-xs text-muted-foreground">{t('passwordPolicy.lockoutDurationHint')}</p>
              </div>
            </div>

            {/* Complexity Requirements */}
            <div className="space-y-3">
              <Label>{t('passwordPolicy.complexityRequirements')}</Label>
              <div className="grid grid-cols-2 gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={passwordPolicy.require_uppercase}
                    onChange={(e) => setPasswordPolicy({ ...passwordPolicy, require_uppercase: e.target.checked })}
                    className="rounded border-zinc-300"
                  />
                  <span className="text-sm">{t('passwordPolicy.requireUppercase')}</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={passwordPolicy.require_lowercase}
                    onChange={(e) => setPasswordPolicy({ ...passwordPolicy, require_lowercase: e.target.checked })}
                    className="rounded border-zinc-300"
                  />
                  <span className="text-sm">{t('passwordPolicy.requireLowercase')}</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={passwordPolicy.require_numbers}
                    onChange={(e) => setPasswordPolicy({ ...passwordPolicy, require_numbers: e.target.checked })}
                    className="rounded border-zinc-300"
                  />
                  <span className="text-sm">{t('passwordPolicy.requireNumbers')}</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={passwordPolicy.require_special_chars}
                    onChange={(e) => setPasswordPolicy({ ...passwordPolicy, require_special_chars: e.target.checked })}
                    className="rounded border-zinc-300"
                  />
                  <span className="text-sm">{t('passwordPolicy.requireSpecialChars')}</span>
                </label>
              </div>
            </div>

            {/* Save Button */}
            <div className="pt-4 border-t">
              <Button onClick={handleSavePasswordPolicy} disabled={savingPasswordPolicy}>
                {savingPasswordPolicy && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                {t('passwordPolicy.save')}
              </Button>
            </div>
          </div>
        </section>

          </TabsContent>

          {/* ============================================ */}
          {/* INTEGRATIONS TAB */}
          {/* ============================================ */}
          <TabsContent value="integrations" className="space-y-8 mt-6">

        {/* Email Configuration Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-medium">{t('emailConfiguration')}</h2>
            </div>
            <Button size="sm" variant="outline" onClick={handleOpenEmailDialog}>
              {emailConfigured ? <Pencil className="h-3.5 w-3.5 mr-1.5" /> : <Plus className="h-3.5 w-3.5 mr-1.5" />}
              {emailConfigured ? tCommon('edit') : t('configureEmail')}
            </Button>
          </div>

          <div className="border rounded-lg bg-white p-4 space-y-4">
            <p className="text-xs text-muted-foreground">
              {t('emailConfigDescription')}
            </p>

            {/* Email Configuration Status */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <div className={`h-2 w-2 rounded-full ${emailConfigured ? 'bg-emerald-500' : 'bg-zinc-300'}`} />
                <span className="text-sm font-medium">{emailConfigured ? t('emailConfigured') : t('emailNotConfigured')}</span>
              </div>

              {emailConfigured && emailConfig && (
                <div className="bg-zinc-50 rounded-lg p-3 space-y-2">
                  <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                    <div>
                      <span className="text-muted-foreground">{t('smtpHost')}:</span>
                      <span className="ml-2 font-medium">{emailConfig.host}:{emailConfig.port}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">{t('fromEmail')}:</span>
                      <span className="ml-2 font-medium">{emailConfig.from_email}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">{t('smtpUsername')}:</span>
                      <span className="ml-2 font-medium">{emailConfig.username}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">{t('tlsEnabled')}:</span>
                      <span className="ml-2 font-medium">{emailConfig.use_tls ? tCommon('yes') : tCommon('no')}</span>
                    </div>
                  </div>
                </div>
              )}

              {emailConfigured && (
                <div className="flex gap-2 pt-2 border-t">
                  <Input
                    type="email"
                    value={testEmailAddress}
                    onChange={(e) => setTestEmailAddress(e.target.value)}
                    placeholder={t('testEmailPlaceholder')}
                    className="flex-1"
                  />
                  <Button variant="outline" size="sm" onClick={handleTestEmail} disabled={testingEmail || !testEmailAddress.trim()}>
                    {testingEmail ? <Loader2 className="h-4 w-4 animate-spin" /> : <><Send className="h-4 w-4 mr-1" /> {t('test')}</>}
                  </Button>
                </div>
              )}

              {emailConfigured && (
                <div className="pt-2 border-t">
                  <Button variant="outline" size="sm" className="text-red-600 hover:text-red-700" onClick={handleDeleteEmailConfig}>
                    <Trash2 className="h-4 w-4 mr-1.5" />
                    {t('removeEmailConfig')}
                  </Button>
                </div>
              )}
            </div>
          </div>
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

          </TabsContent>

          {/* ============================================ */}
          {/* SYSTEM TAB */}
          {/* ============================================ */}
          <TabsContent value="system" className="space-y-8 mt-6">

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

          </TabsContent>
        </Tabs>
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

      {/* Email Configuration Dialog */}
      <Dialog open={emailDialogOpen} onOpenChange={setEmailDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{emailConfigured ? t('editEmailConfig') : t('configureEmail')}</DialogTitle>
            <DialogDescription>
              {emailConfigured ? t('editEmailConfigDescription') : t('configureEmailDescription')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2 space-y-2">
                <Label className="text-xs font-medium">{t('smtpHost')}</Label>
                <Input
                  value={emailForm.host}
                  onChange={(e) => setEmailForm({ ...emailForm, host: e.target.value })}
                  placeholder="smtp.example.com"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-xs font-medium">{t('smtpPort')}</Label>
                <Input
                  value={emailForm.port}
                  onChange={(e) => setEmailForm({ ...emailForm, port: parseInt(e.target.value) || 587 })}
                  placeholder="587"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-medium">{t('smtpUsername')}</Label>
              <Input
                value={emailForm.username}
                onChange={(e) => setEmailForm({ ...emailForm, username: e.target.value })}
                placeholder="user@example.com"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-medium">
                {t('smtpPassword')}
                {emailConfigured && <span className="text-muted-foreground font-normal"> ({t('leaveEmptyToKeep')})</span>}
              </Label>
              <Input
                type="password"
                value={emailForm.password}
                onChange={(e) => setEmailForm({ ...emailForm, password: e.target.value })}
                placeholder={emailConfigured ? '••••••••' : ''}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label className="text-xs font-medium">{t('fromEmail')}</Label>
                <Input
                  type="email"
                  value={emailForm.from_email}
                  onChange={(e) => setEmailForm({ ...emailForm, from_email: e.target.value })}
                  placeholder="noreply@example.com"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-xs font-medium">{t('fromName')}</Label>
                <Input
                  value={emailForm.from_name}
                  onChange={(e) => setEmailForm({ ...emailForm, from_name: e.target.value })}
                  placeholder="License Management System"
                />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="use_tls"
                  checked={emailForm.use_tls}
                  onChange={(e) => setEmailForm({ ...emailForm, use_tls: e.target.checked })}
                  className="rounded border-zinc-300"
                />
                <Label htmlFor="use_tls" className="text-xs font-medium cursor-pointer">
                  <ShieldCheck className="h-3.5 w-3.5 inline mr-1" />
                  {t('useTls')}
                </Label>
              </div>
              <p className="text-xs text-muted-foreground ml-5">{t('tlsHint')}</p>
            </div>

            <div className="bg-blue-50 rounded-lg p-3 text-xs text-blue-700">
              <Info className="h-4 w-4 inline mr-1" />
              {t('emailConfigInfo')}
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setEmailDialogOpen(false)}>{tCommon('cancel')}</Button>
            <Button onClick={handleSaveEmailConfig} disabled={!emailForm.host || !emailForm.username || !emailForm.from_email || savingEmail}>
              {savingEmail ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> {tCommon('loading')}</> : tCommon('save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
