'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth, Permissions } from '@/components/auth-provider';
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
import { NOTIFICATION_EVENT_TYPES } from '@/lib/api';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Plus, Pencil, Trash2, CheckCircle2, XCircle, Loader2, Globe, X, MessageSquare, Bell, Send, Hash, Power, Settings2, HardDrive, Info, Mail, Database, ShieldCheck } from 'lucide-react';
import { BackupsTab } from '@/components/settings/BackupsTab';
import { Textarea } from '@/components/ui/textarea';
import { useSettings } from '@/hooks/use-settings';

export default function SettingsPage() {
  const t = useTranslations('settings');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { hasPermission, isLoading: authLoading } = useAuth();
  const canUpdate = hasPermission(Permissions.SETTINGS_UPDATE);

  const {
    loading,
    toast,
    showToast,
    activeTab,
    setActiveTab,
    systemName,
    setSystemName,
    systemUrl,
    setSystemUrl,
    savingSystemSettings,
    handleSaveSystemSettings,
    companyDomains,
    newDomain,
    setNewDomain,
    savingDomains,
    handleAddDomain,
    handleRemoveDomain,
    handleSaveDomains,
    slackBotToken,
    setSlackBotToken,
    slackConfigured,
    savingSlack,
    testingSlack,
    testChannel,
    setTestChannel,
    handleSaveSlackConfig,
    handleTestSlack,
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
    thresholds,
    setThresholds,
    savingThresholds,
    handleSaveThresholds,
  } = useSettings(t, tCommon);

  useEffect(() => {
    if (!authLoading && !hasPermission(Permissions.SETTINGS_VIEW)) {
      router.push('/unauthorized');
      return;
    }
  }, [authLoading, hasPermission, router]);

  if (authLoading || loading) {
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
          <div className={`fixed bottom-6 right-6 z-[9999] flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
            toast.type === 'success' ? 'bg-primary text-primary-foreground' : 'bg-destructive text-destructive-foreground'
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
            <TabsTrigger value="integrations" className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              {t('tabs.integrations')}
            </TabsTrigger>
            <TabsTrigger value="backups" className="flex items-center gap-2">
              <Database className="h-4 w-4" />
              {t('tabs.backups')}
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

        {/* System Settings Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-medium">{t('systemSettings')}</h2>
            </div>
          </div>

          <div className="border rounded-lg bg-card p-4 space-y-4">
            <p className="text-xs text-muted-foreground">
              {t('systemSettingsDescription')}
            </p>

            <div className="space-y-3">
              <div>
                <Label className="text-xs font-medium">{t('systemName')}</Label>
                <Input
                  value={systemName}
                  onChange={(e) => setSystemName(e.target.value)}
                  placeholder={t('systemNamePlaceholder')}
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs font-medium">{t('systemUrl')}</Label>
                <Input
                  value={systemUrl}
                  onChange={(e) => setSystemUrl(e.target.value)}
                  placeholder={t('systemUrlPlaceholder')}
                  className="mt-1"
                />
                <p className="text-xs text-muted-foreground mt-1">{t('systemUrlDescription')}</p>
              </div>
            </div>

            <Button size="sm" onClick={handleSaveSystemSettings} disabled={!canUpdate || savingSystemSettings}>
              {savingSystemSettings ? <Loader2 className="h-4 w-4 animate-spin" /> : tCommon('save')}
            </Button>
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

          <div className="border rounded-lg bg-card p-4 space-y-4">
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
                    className="bg-muted text-muted-foreground pr-1.5 flex items-center gap-1"
                  >
                    {domain}
                    <button
                      onClick={() => handleRemoveDomain(domain)}
                      className="ml-1 hover:bg-accent rounded p-0.5"
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
              <Button size="sm" onClick={handleSaveDomains} disabled={!canUpdate || savingDomains}>
                {savingDomains ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                {tCommon('save')}
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

          <div className="border rounded-lg bg-card p-4 space-y-4">
            <p className="text-xs text-muted-foreground">
              {t('emailConfigDescription')}
            </p>

            {/* Email Configuration Status */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <div className={`h-2 w-2 rounded-full ${emailConfigured ? 'bg-emerald-500' : 'bg-muted-foreground/30'}`} />
                <span className="text-sm font-medium">{emailConfigured ? t('emailConfigured') : t('emailNotConfigured')}</span>
              </div>

              {emailConfigured && emailConfig && (
                <div className="bg-muted/50 rounded-lg p-3 space-y-2">
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

          <div className="border rounded-lg bg-card p-4 space-y-4">
            <p className="text-xs text-muted-foreground">
              {t('slackDescription')}
            </p>

            {/* Slack Configuration */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <div className={`h-2 w-2 rounded-full ${slackConfigured ? 'bg-emerald-500' : 'bg-muted-foreground/30'}`} />
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
                <Button variant="outline" size="sm" onClick={handleSaveSlackConfig} disabled={!canUpdate || savingSlack || !slackBotToken.trim()}>
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
            <div className="border rounded-lg bg-muted/50 p-4 text-center">
              <MessageSquare className="h-8 w-8 mx-auto text-muted-foreground/50 mb-2" />
              <p className="text-sm text-muted-foreground">{t('configureSlackFirst')}</p>
            </div>
          ) : notificationRules.length > 0 ? (
            <div className="border rounded-lg bg-card divide-y">
              {notificationRules.map((rule) => {
                const eventType = NOTIFICATION_EVENT_TYPES.find(t => t.value === rule.event_type);
                return (
                  <div key={rule.id} className="flex items-center justify-between p-4">
                    <div className="flex items-center gap-3">
                      <div className={`h-9 w-9 rounded-lg flex items-center justify-center ${rule.enabled ? 'bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400' : 'bg-muted text-muted-foreground'}`}>
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
                        className={`h-8 w-8 ${rule.enabled ? 'text-emerald-600 dark:text-emerald-400' : 'text-muted-foreground'}`}
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
              <Bell className="h-8 w-8 mx-auto text-muted-foreground/50 mb-2" />
              <p className="text-sm text-muted-foreground">{t('noRulesConfigured')}</p>
            </div>
          )}
        </section>

          </TabsContent>

          {/* ============================================ */}
          {/* BACKUPS TAB */}
          {/* ============================================ */}
          <TabsContent value="backups" className="space-y-8 mt-6">
            <BackupsTab showToast={(type, message) => showToast(type, message)} />
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

          <div className="border rounded-lg bg-card p-4 space-y-6">
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
              <Button size="sm" onClick={handleSaveThresholds} disabled={!canUpdate || savingThresholds}>
                {savingThresholds ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                {t('saveThresholds')}
              </Button>
            </div>
          </div>
        </section>

          </TabsContent>
        </Tabs>
      </div>

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
                  placeholder={t('smtpHostPlaceholder')}
                />
              </div>
              <div className="space-y-2">
                <Label className="text-xs font-medium">{t('smtpPort')}</Label>
                <Input
                  value={emailForm.port}
                  onChange={(e) => setEmailForm({ ...emailForm, port: parseInt(e.target.value) || 587 })}
                  placeholder={t('smtpPortPlaceholder')}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-medium">{t('smtpUsername')}</Label>
              <Input
                value={emailForm.username}
                onChange={(e) => setEmailForm({ ...emailForm, username: e.target.value })}
                placeholder={t('smtpUsernamePlaceholder')}
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
                  placeholder={t('fromEmailPlaceholder')}
                />
              </div>
              <div className="space-y-2">
                <Label className="text-xs font-medium">{t('fromName')}</Label>
                <Input
                  value={emailForm.from_name}
                  onChange={(e) => setEmailForm({ ...emailForm, from_name: e.target.value })}
                  placeholder={t('fromNamePlaceholder')}
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
