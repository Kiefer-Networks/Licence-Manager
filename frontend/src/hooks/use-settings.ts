'use client';

import { useEffect, useState, useCallback } from 'react';
import { api, NotificationRule, NOTIFICATION_EVENT_TYPES, ThresholdSettings, SmtpConfig, SmtpConfigRequest } from '@/lib/api';
import { handleSilentError } from '@/lib/error-handler';

/**
 * Toast state for user feedback.
 */
export interface SettingsToast {
  type: 'success' | 'error';
  text: string;
}

/**
 * Return type for the useSettings hook.
 */
export interface UseSettingsReturn {
  // Loading state
  loading: boolean;

  // Toast
  toast: SettingsToast | null;
  showToast: (type: 'success' | 'error', text: string) => void;

  // Tab state
  activeTab: string;
  setActiveTab: (tab: string) => void;

  // System Settings
  systemName: string;
  setSystemName: (name: string) => void;
  systemUrl: string;
  setSystemUrl: (url: string) => void;
  savingSystemSettings: boolean;
  handleSaveSystemSettings: () => Promise<void>;

  // Company Domains
  companyDomains: string[];
  newDomain: string;
  setNewDomain: (domain: string) => void;
  savingDomains: boolean;
  handleAddDomain: () => void;
  handleRemoveDomain: (domain: string) => void;
  handleSaveDomains: () => Promise<void>;

  // Slack Integration
  slackBotToken: string;
  setSlackBotToken: (token: string) => void;
  slackConfigured: boolean;
  savingSlack: boolean;
  testingSlack: boolean;
  testChannel: string;
  setTestChannel: (channel: string) => void;
  handleSaveSlackConfig: () => Promise<void>;
  handleTestSlack: () => Promise<void>;

  // Email/SMTP
  emailConfig: SmtpConfig | null;
  emailConfigured: boolean;
  emailDialogOpen: boolean;
  setEmailDialogOpen: (open: boolean) => void;
  savingEmail: boolean;
  testingEmail: boolean;
  testEmailAddress: string;
  setTestEmailAddress: (addr: string) => void;
  emailForm: EmailFormState;
  setEmailForm: React.Dispatch<React.SetStateAction<EmailFormState>>;
  handleOpenEmailDialog: () => void;
  handleSaveEmailConfig: () => Promise<void>;
  handleDeleteEmailConfig: () => Promise<void>;
  handleTestEmail: () => Promise<void>;

  // Notification Rules
  notificationRules: NotificationRule[];
  ruleDialogOpen: boolean;
  setRuleDialogOpen: (open: boolean) => void;
  editingRule: NotificationRule | null;
  ruleForm: RuleFormState;
  setRuleForm: React.Dispatch<React.SetStateAction<RuleFormState>>;
  handleOpenRuleDialog: (rule?: NotificationRule) => void;
  handleSaveRule: () => Promise<void>;
  handleToggleRule: (rule: NotificationRule) => Promise<void>;
  handleDeleteRule: (id: string) => Promise<void>;

  // Threshold Settings
  thresholds: ThresholdSettings;
  setThresholds: React.Dispatch<React.SetStateAction<ThresholdSettings>>;
  savingThresholds: boolean;
  handleSaveThresholds: () => Promise<void>;
}

export interface EmailFormState {
  host: string;
  port: number;
  username: string;
  password: string;
  from_email: string;
  from_name: string;
  use_tls: boolean;
}

export interface RuleFormState {
  event_type: string;
  slack_channel: string;
  template: string;
}

/**
 * Custom hook that encapsulates all business logic for the Settings page.
 * Manages system settings, company domains, Slack integration, email/SMTP,
 * notification rules, and threshold settings.
 */
export function useSettings(
  t: (key: string, params?: Record<string, string | number>) => string,
  tCommon: (key: string) => string,
): UseSettingsReturn {
  // Loading
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<SettingsToast | null>(null);

  // Active tab state
  const [activeTab, setActiveTab] = useState('general');

  // System Settings state
  const [systemName, setSystemName] = useState('License Management System');
  const [systemUrl, setSystemUrl] = useState('');
  const [savingSystemSettings, setSavingSystemSettings] = useState(false);

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
  const [ruleForm, setRuleForm] = useState<RuleFormState>({
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
  const [emailForm, setEmailForm] = useState<EmailFormState>({
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

  // -- Toast helper --

  const showToast = useCallback((type: 'success' | 'error', text: string) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 3000);
  }, []);

  // -- Fetch functions --

  const fetchSystemSettings = useCallback(async () => {
    try {
      const settings = await api.getSystemSettings();
      setSystemName(settings.name);
      setSystemUrl(settings.url || '');
    } catch (error) {
      handleSilentError('fetchSystemSettings', error);
    }
  }, []);

  const fetchCompanyDomains = useCallback(async () => {
    try {
      const domains = await api.getCompanyDomains();
      setCompanyDomains(domains);
    } catch (error) {
      handleSilentError('fetchCompanyDomains', error);
    }
  }, []);

  const fetchSlackConfig = useCallback(async () => {
    try {
      const config = await api.getSlackConfig();
      setSlackConfigured(config.configured);
    } catch (error) {
      handleSilentError('fetchSlackConfig', error);
    }
  }, []);

  const fetchNotificationRules = useCallback(async () => {
    try {
      const rules = await api.getNotificationRules();
      setNotificationRules(rules);
    } catch (error) {
      handleSilentError('fetchNotificationRules', error);
    }
  }, []);

  const fetchThresholdSettings = useCallback(async () => {
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
  }, []);

  const fetchEmailConfig = useCallback(async () => {
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
  }, []);

  // -- Initial data load --

  useEffect(() => {
    Promise.all([
      fetchSystemSettings(),
      fetchCompanyDomains(),
      fetchSlackConfig(),
      fetchNotificationRules(),
      fetchThresholdSettings(),
      fetchEmailConfig(),
    ]).finally(() => setLoading(false));
  }, []);

  // -- Handlers --

  const handleSaveSystemSettings = useCallback(async () => {
    if (!systemName.trim()) {
      showToast('error', t('systemNameRequired'));
      return;
    }
    setSavingSystemSettings(true);
    try {
      await api.updateSystemSettings({
        name: systemName.trim(),
        url: systemUrl.trim() || null,
      });
      showToast('success', t('systemSettingsSaved'));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToSave');
      showToast('error', message);
    } finally {
      setSavingSystemSettings(false);
    }
  }, [systemName, systemUrl, showToast, t]);

  const handleSaveThresholds = useCallback(async () => {
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
  }, [thresholds, showToast, t]);

  // Email configuration handlers
  const handleOpenEmailDialog = useCallback(() => {
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
  }, [emailConfig]);

  const handleSaveEmailConfig = useCallback(async () => {
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
  }, [emailForm, emailConfigured, showToast, t, fetchEmailConfig]);

  const handleDeleteEmailConfig = useCallback(async () => {
    try {
      await api.deleteEmailConfig();
      setEmailConfig(null);
      setEmailConfigured(false);
      showToast('success', t('emailConfigDeleted'));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToDeleteEmailConfig');
      showToast('error', message);
    }
  }, [showToast, t]);

  const handleTestEmail = useCallback(async () => {
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
  }, [testEmailAddress, showToast, t]);

  // Company Domains handlers
  const handleAddDomain = useCallback(() => {
    const domain = newDomain.trim().toLowerCase();
    if (!domain) return;
    if (companyDomains.includes(domain)) {
      showToast('error', t('domainAlreadyExists'));
      return;
    }
    setCompanyDomains([...companyDomains, domain]);
    setNewDomain('');
  }, [newDomain, companyDomains, showToast, t]);

  const handleRemoveDomain = useCallback((domain: string) => {
    setCompanyDomains(prev => prev.filter((d) => d !== domain));
  }, []);

  const handleSaveDomains = useCallback(async () => {
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
  }, [companyDomains, showToast, t]);

  // Slack handlers
  const handleSaveSlackConfig = useCallback(async () => {
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
  }, [slackBotToken, showToast, t]);

  const handleTestSlack = useCallback(async () => {
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
  }, [testChannel, showToast, t]);

  // Notification rule handlers
  const handleOpenRuleDialog = useCallback((rule?: NotificationRule) => {
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
  }, []);

  const handleSaveRule = useCallback(async () => {
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
  }, [ruleForm, editingRule, showToast, t, fetchNotificationRules]);

  const handleToggleRule = useCallback(async (rule: NotificationRule) => {
    try {
      await api.updateNotificationRule(rule.id, { enabled: !rule.enabled });
      await fetchNotificationRules();
      showToast('success', rule.enabled ? t('ruleDisabled') : t('ruleEnabled'));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToUpdateRule');
      showToast('error', message);
    }
  }, [showToast, t, fetchNotificationRules]);

  const handleDeleteRule = useCallback(async (id: string) => {
    try {
      await api.deleteNotificationRule(id);
      await fetchNotificationRules();
      showToast('success', t('ruleDeleted'));
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('failedToDeleteRule');
      showToast('error', message);
    }
  }, [showToast, t, fetchNotificationRules]);

  return {
    // Loading state
    loading,

    // Toast
    toast,
    showToast,

    // Tab state
    activeTab,
    setActiveTab,

    // System Settings
    systemName,
    setSystemName,
    systemUrl,
    setSystemUrl,
    savingSystemSettings,
    handleSaveSystemSettings,

    // Company Domains
    companyDomains,
    newDomain,
    setNewDomain,
    savingDomains,
    handleAddDomain,
    handleRemoveDomain,
    handleSaveDomains,

    // Slack Integration
    slackBotToken,
    setSlackBotToken,
    slackConfigured,
    savingSlack,
    testingSlack,
    testChannel,
    setTestChannel,
    handleSaveSlackConfig,
    handleTestSlack,

    // Email/SMTP
    emailConfig,
    emailConfigured,
    emailDialogOpen,
    setEmailDialogOpen,
    savingEmail,
    testingEmail,
    testEmailAddress,
    setTestEmailAddress,
    emailForm,
    setEmailForm,
    handleOpenEmailDialog,
    handleSaveEmailConfig,
    handleDeleteEmailConfig,
    handleTestEmail,

    // Notification Rules
    notificationRules,
    ruleDialogOpen,
    setRuleDialogOpen,
    editingRule,
    ruleForm,
    setRuleForm,
    handleOpenRuleDialog,
    handleSaveRule,
    handleToggleRule,
    handleDeleteRule,

    // Threshold Settings
    thresholds,
    setThresholds,
    savingThresholds,
    handleSaveThresholds,
  };
}
