'use client';

import { useState, useEffect, useRef } from 'react';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/components/auth-provider';
import { api, UserNotificationPreference, NotificationEventType, UserNotificationPreferenceUpdate } from '@/lib/api';
import { AppLayout } from '@/components/layout/app-layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, Bell, MessageSquare, User, Shield, Camera, Trash2, Palette, Sun, Moon, Monitor, Check, Globe, Calendar, Hash, DollarSign, ShieldCheck, ShieldOff, RefreshCw } from 'lucide-react';
import { TotpSetupDialog, TotpBackupCodesDialog, TotpDisableDialog, TotpRegenerateDialog } from '@/components/totp';
import { TotpStatusResponse } from '@/lib/api';
import { useTheme } from '@/components/theme-provider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ImageCropDialog } from '@/components/ui/image-crop-dialog';

export default function ProfilePage() {
  const t = useTranslations('profile');
  const tCommon = useTranslations('common');
  const tNav = useTranslations('nav');
  const { user, refreshUser } = useAuth();
  const { theme, setTheme } = useTheme();

  // Locale settings state
  const [dateFormat, setDateFormat] = useState('DD.MM.YYYY');
  const [numberFormat, setNumberFormat] = useState('de-DE');
  const [currency, setCurrency] = useState('EUR');
  const [localeSaving, setLocaleSaving] = useState(false);
  const [localeSuccess, setLocaleSuccess] = useState('');
  const [localeError, setLocaleError] = useState('');

  // General tab state
  const [name, setName] = useState('');
  const [nameSaving, setNameSaving] = useState(false);
  const [generalError, setGeneralError] = useState('');
  const [generalSuccess, setGeneralSuccess] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [cropDialogOpen, setCropDialogOpen] = useState(false);
  const [selectedImageSrc, setSelectedImageSrc] = useState<string | null>(null);

  // Security tab state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [securityError, setSecurityError] = useState('');
  const [securitySuccess, setSecuritySuccess] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Notification preferences state
  const [notifPrefs, setNotifPrefs] = useState<UserNotificationPreference[]>([]);
  const [availableEventTypes, setAvailableEventTypes] = useState<NotificationEventType[]>([]);
  const [notifLoading, setNotifLoading] = useState(true);
  const [notifSaving, setNotifSaving] = useState(false);
  const [notifError, setNotifError] = useState('');
  const [notifSuccess, setNotifSuccess] = useState('');

  // TOTP state
  const [totpStatus, setTotpStatus] = useState<TotpStatusResponse | null>(null);
  const [totpLoading, setTotpLoading] = useState(true);
  const [showTotpSetup, setShowTotpSetup] = useState(false);
  const [showTotpDisable, setShowTotpDisable] = useState(false);
  const [showTotpRegenerate, setShowTotpRegenerate] = useState(false);
  const [showBackupCodes, setShowBackupCodes] = useState(false);
  const [backupCodes, setBackupCodes] = useState<string[]>([]);

  // Initialize name from user
  useEffect(() => {
    if (user?.name) {
      setName(user.name);
    }
  }, [user?.name]);

  // Initialize locale settings from user
  useEffect(() => {
    if (user) {
      setDateFormat(user.date_format || 'DD.MM.YYYY');
      setNumberFormat(user.number_format || 'de-DE');
      setCurrency(user.currency || 'EUR');
    }
  }, [user?.date_format, user?.number_format, user?.currency]);

  // Fetch notification preferences
  useEffect(() => {
    const fetchNotificationPreferences = async () => {
      try {
        const response = await api.getNotificationPreferences();
        setNotifPrefs(response.preferences);
        setAvailableEventTypes(response.available_event_types);
      } catch {
        // Error handled silently - notifications will show default state
      } finally {
        setNotifLoading(false);
      }
    };
    fetchNotificationPreferences();
  }, []);

  // Fetch TOTP status
  useEffect(() => {
    const fetchTotpStatus = async () => {
      try {
        const status = await api.getTotpStatus();
        setTotpStatus(status);
      } catch {
        // Error handled silently - TOTP will show as disabled
        setTotpStatus({ enabled: false, has_backup_codes: false });
      } finally {
        setTotpLoading(false);
      }
    };
    fetchTotpStatus();
  }, []);

  // Get preference for an event type
  const getPreference = (eventType: string): UserNotificationPreference | undefined => {
    return notifPrefs.find(p => p.event_type === eventType);
  };

  // Update a single preference locally
  const updateLocalPreference = (eventType: string, updates: Partial<UserNotificationPreferenceUpdate>) => {
    const eventInfo = availableEventTypes.find(e => e.code === eventType);
    setNotifPrefs(prev => {
      const existing = prev.find(p => p.event_type === eventType);
      if (existing) {
        return prev.map(p =>
          p.event_type === eventType
            ? { ...p, ...updates }
            : p
        );
      }
      return [
        ...prev,
        {
          id: '',
          event_type: eventType,
          event_name: eventInfo?.name || eventType,
          event_description: eventInfo?.description || '',
          enabled: true,
          slack_dm: false,
          ...updates,
        } as UserNotificationPreference,
      ];
    });
  };

  // Save notification preferences
  const saveNotificationPreferences = async () => {
    setNotifSaving(true);
    setNotifError('');
    setNotifSuccess('');

    try {
      const updates: UserNotificationPreferenceUpdate[] = availableEventTypes.map(eventType => {
        const pref = getPreference(eventType.code);
        return {
          event_type: eventType.code,
          enabled: pref?.enabled ?? true,
          slack_dm: pref?.slack_dm ?? false,
          slack_channel: pref?.slack_channel,
        };
      });

      const response = await api.updateNotificationPreferences(updates);
      setNotifPrefs(response.preferences);
      setNotifSuccess(t('preferencesSaved'));
      setTimeout(() => setNotifSuccess(''), 3000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('failedToSave');
      setNotifError(errorMessage);
    } finally {
      setNotifSaving(false);
    }
  };

  // Group event types by category
  const eventTypesByCategory = availableEventTypes.reduce((acc, et) => {
    if (!acc[et.category]) acc[et.category] = [];
    acc[et.category].push(et);
    return acc;
  }, {} as Record<string, NotificationEventType[]>);

  const tLicenses = useTranslations('licenses');
  const tEmployees = useTranslations('employees');
  const tDashboard = useTranslations('dashboard');
  const tSettings = useTranslations('settings');

  const categoryLabels: Record<string, string> = {
    licenses: tLicenses('title'),
    employees: tEmployees('title'),
    utilization: tDashboard('overview'),
    costs: tDashboard('totalCost'),
    duplicates: tDashboard('alerts'),
    system: tSettings('general'),
  };

  // Handle name save
  const handleSaveName = async () => {
    setNameSaving(true);
    setGeneralError('');
    setGeneralSuccess('');

    try {
      await api.updateProfile({ name: name || undefined });
      await refreshUser?.();
      setGeneralSuccess(t('nameUpdated'));
      setTimeout(() => setGeneralSuccess(''), 3000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('failedToUpdate');
      setGeneralError(errorMessage);
    } finally {
      setNameSaving(false);
    }
  };

  // Handle avatar file selection - opens crop dialog
  const handleAvatarSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      setGeneralError(t('invalidFileType'));
      return;
    }

    // Validate file size (5MB)
    if (file.size > 5 * 1024 * 1024) {
      setGeneralError(t('fileTooLarge'));
      return;
    }

    setGeneralError('');

    // Create object URL for the image and open crop dialog
    const imageUrl = URL.createObjectURL(file);
    setSelectedImageSrc(imageUrl);
    setCropDialogOpen(true);

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Handle cropped image upload
  const handleCroppedImageUpload = async (croppedBlob: Blob) => {
    setAvatarUploading(true);
    setGeneralError('');
    setGeneralSuccess('');

    try {
      // Convert blob to file
      const file = new File([croppedBlob], 'avatar.png', { type: 'image/png' });
      await api.uploadAvatar(file);
      await refreshUser?.();
      setGeneralSuccess(t('avatarUploaded'));
      setTimeout(() => setGeneralSuccess(''), 3000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('failedToUpdate');
      setGeneralError(errorMessage);
    } finally {
      setAvatarUploading(false);
      // Clean up object URL
      if (selectedImageSrc) {
        URL.revokeObjectURL(selectedImageSrc);
        setSelectedImageSrc(null);
      }
    }
  };

  // Handle avatar delete
  const handleDeleteAvatar = async () => {
    setAvatarUploading(true);
    setGeneralError('');
    setGeneralSuccess('');

    try {
      await api.deleteAvatar();
      await refreshUser?.();
      setGeneralSuccess(t('avatarDeleted'));
      setTimeout(() => setGeneralSuccess(''), 3000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('failedToUpdate');
      setGeneralError(errorMessage);
    } finally {
      setAvatarUploading(false);
    }
  };

  // Handle password change
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setSecurityError('');
    setSecuritySuccess('');

    if (newPassword !== confirmPassword) {
      setSecurityError(t('passwordsDoNotMatch'));
      return;
    }

    if (newPassword.length < 12) {
      setSecurityError(t('passwordTooShort'));
      return;
    }

    setIsSubmitting(true);

    try {
      await api.changePassword(currentPassword, newPassword);
      setSecuritySuccess(t('passwordChanged'));
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : t('failedToUpdate');
      setSecurityError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogoutAllSessions = async () => {
    try {
      const result = await api.logoutAllSessions();
      setSecuritySuccess(t('loggedOutSessions', { count: result.sessions_revoked }));
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : t('failedToUpdate');
      setSecurityError(errorMessage);
    }
  };

  // TOTP handlers
  const handleTotpSetupSuccess = (codes: string[]) => {
    setBackupCodes(codes);
    setShowBackupCodes(true);
    setTotpStatus({ enabled: true, has_backup_codes: true, verified_at: new Date().toISOString() });
    setSecuritySuccess(t('totpSetupSuccess'));
    refreshUser?.();
  };

  const handleTotpDisableSuccess = () => {
    setTotpStatus({ enabled: false, has_backup_codes: false });
    setSecuritySuccess(t('totpDisableSuccess'));
    refreshUser?.();
  };

  const handleTotpRegenerateSuccess = (codes: string[]) => {
    setBackupCodes(codes);
    setShowBackupCodes(true);
    setTotpStatus(prev => prev ? { ...prev, has_backup_codes: true } : prev);
  };

  // Handle locale settings save
  const handleSaveLocale = async () => {
    setLocaleSaving(true);
    setLocaleError('');
    setLocaleSuccess('');

    try {
      await api.updateProfile({
        date_format: dateFormat,
        number_format: numberFormat,
        currency: currency,
      });
      await refreshUser?.();
      setLocaleSuccess(t('localeSaved'));
      setTimeout(() => setLocaleSuccess(''), 3000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('failedToUpdate');
      setLocaleError(errorMessage);
    } finally {
      setLocaleSaving(false);
    }
  };

  // Check if locale settings have changed
  const hasLocaleChanges =
    dateFormat !== (user?.date_format || 'DD.MM.YYYY') ||
    numberFormat !== (user?.number_format || 'de-DE') ||
    currency !== (user?.currency || 'EUR');

  return (
    <AppLayout>
      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold">{t('title')}</h1>
          <p className="text-muted-foreground">{t('subtitle')}</p>
        </div>

        <Tabs defaultValue="general" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="general" className="flex items-center gap-2">
              <User className="h-4 w-4" />
              {t('general')}
            </TabsTrigger>
            <TabsTrigger value="appearance" className="flex items-center gap-2">
              <Palette className="h-4 w-4" />
              {t('appearance')}
            </TabsTrigger>
            <TabsTrigger value="security" className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              {t('security')}
            </TabsTrigger>
            <TabsTrigger value="notifications" className="flex items-center gap-2">
              <Bell className="h-4 w-4" />
              {t('notifications')}
            </TabsTrigger>
          </TabsList>

          {/* General Tab */}
          <TabsContent value="general" className="space-y-6 mt-6">
            {generalError && (
              <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
                {generalError}
              </div>
            )}
            {generalSuccess && (
              <div className="bg-green-50 text-green-700 text-sm p-3 rounded-md">
                {generalSuccess}
              </div>
            )}

            {/* Avatar Section */}
            <Card>
              <CardHeader>
                <CardTitle>{t('profilePicture')}</CardTitle>
                <CardDescription>{t('profilePictureDescription')}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-6">
                  <div className="relative">
                    <div className="h-24 w-24 rounded-full bg-zinc-100 flex items-center justify-center overflow-hidden border-2 border-zinc-200">
                      {user?.picture_url ? (
                        <img
                          src={user.picture_url}
                          alt={t('avatar')}
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <span className="text-3xl font-semibold text-zinc-600">
                          {(user?.name || user?.email || 'U').charAt(0).toUpperCase()}
                        </span>
                      )}
                    </div>
                    {avatarUploading && (
                      <div className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-full">
                        <Loader2 className="h-6 w-6 animate-spin text-white" />
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col gap-2">
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleAvatarSelect}
                      accept="image/jpeg,image/png,image/gif,image/webp"
                      className="hidden"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={avatarUploading}
                    >
                      <Camera className="h-4 w-4 mr-2" />
                      {t('uploadPhoto')}
                    </Button>
                    {user?.picture_url && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleDeleteAvatar}
                        disabled={avatarUploading}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        {t('removePhoto')}
                      </Button>
                    )}
                    <p className="text-xs text-muted-foreground">
                      {t('photoFormats')}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Display Name */}
            <Card>
              <CardHeader>
                <CardTitle>{t('displayName')}</CardTitle>
                <CardDescription>{t('displayNameDescription')}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center gap-4">
                    <div className="flex-1">
                      <Input
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder={t('enterDisplayName')}
                        className="text-base"
                      />
                    </div>
                    <Button
                      onClick={handleSaveName}
                      disabled={nameSaving || name === (user?.name || '')}
                    >
                      {nameSaving ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          {t('saving')}
                        </>
                      ) : (
                        t('saveName')
                      )}
                    </Button>
                  </div>
                  {name !== (user?.name || '') && (
                    <p className="text-sm text-amber-600">
                      {tCommon('unsavedChanges')}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Account Info */}
            <Card>
              <CardHeader>
                <CardTitle>{t('accountInfo')}</CardTitle>
                <CardDescription>{t('accountInfoDescription')}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4">
                  <div className="space-y-2">
                    <Label className="text-muted-foreground text-xs">{tCommon('email')}</Label>
                    <p className="font-medium">{user?.email}</p>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-muted-foreground text-xs">{tNav('roles')}</Label>
                    <div className="flex flex-wrap gap-1">
                      {user?.roles.map((role) => (
                        <Badge key={role} variant="secondary">{role}</Badge>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Appearance Tab */}
          <TabsContent value="appearance" className="space-y-6 mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Palette className="h-5 w-5" />
                  {t('themeSettings')}
                </CardTitle>
                <CardDescription>{t('themeDescription')}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4">
                  <button
                    onClick={() => setTheme('light')}
                    className={`relative flex flex-col items-center gap-3 p-4 rounded-lg border-2 transition-colors ${
                      theme === 'light'
                        ? 'border-primary bg-primary/5'
                        : 'border-zinc-200 dark:border-zinc-700 hover:border-zinc-300 dark:hover:border-zinc-600'
                    }`}
                  >
                    <div className="h-12 w-12 rounded-full bg-amber-100 flex items-center justify-center">
                      <Sun className="h-6 w-6 text-amber-600" />
                    </div>
                    <span className="font-medium text-sm">{t('themeLight')}</span>
                    {theme === 'light' && (
                      <div className="absolute top-2 right-2 h-5 w-5 rounded-full bg-primary flex items-center justify-center">
                        <Check className="h-3 w-3 text-primary-foreground" />
                      </div>
                    )}
                  </button>
                  <button
                    onClick={() => setTheme('dark')}
                    className={`relative flex flex-col items-center gap-3 p-4 rounded-lg border-2 transition-colors ${
                      theme === 'dark'
                        ? 'border-primary bg-primary/5'
                        : 'border-zinc-200 dark:border-zinc-700 hover:border-zinc-300 dark:hover:border-zinc-600'
                    }`}
                  >
                    <div className="h-12 w-12 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center">
                      <Moon className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
                    </div>
                    <span className="font-medium text-sm">{t('themeDark')}</span>
                    {theme === 'dark' && (
                      <div className="absolute top-2 right-2 h-5 w-5 rounded-full bg-primary flex items-center justify-center">
                        <Check className="h-3 w-3 text-primary-foreground" />
                      </div>
                    )}
                  </button>
                  <button
                    onClick={() => setTheme('system')}
                    className={`relative flex flex-col items-center gap-3 p-4 rounded-lg border-2 transition-colors ${
                      theme === 'system'
                        ? 'border-primary bg-primary/5'
                        : 'border-zinc-200 dark:border-zinc-700 hover:border-zinc-300 dark:hover:border-zinc-600'
                    }`}
                  >
                    <div className="h-12 w-12 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center">
                      <Monitor className="h-6 w-6 text-zinc-600 dark:text-zinc-400" />
                    </div>
                    <span className="font-medium text-sm">{t('themeSystem')}</span>
                    {theme === 'system' && (
                      <div className="absolute top-2 right-2 h-5 w-5 rounded-full bg-primary flex items-center justify-center">
                        <Check className="h-3 w-3 text-primary-foreground" />
                      </div>
                    )}
                  </button>
                </div>
                <p className="mt-4 text-sm text-muted-foreground">
                  {t('themeSystemHint')}
                </p>
              </CardContent>
            </Card>

            {/* Locale Settings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Globe className="h-5 w-5" />
                  {t('localeSettings')}
                </CardTitle>
                <CardDescription>{t('localeDescription')}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {localeError && (
                  <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
                    {localeError}
                  </div>
                )}
                {localeSuccess && (
                  <div className="bg-green-50 text-green-700 text-sm p-3 rounded-md">
                    {localeSuccess}
                  </div>
                )}

                {/* Date Format */}
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    {t('dateFormat')}
                  </Label>
                  <p className="text-sm text-muted-foreground">{t('dateFormatDescription')}</p>
                  <Select value={dateFormat} onValueChange={setDateFormat}>
                    <SelectTrigger className="w-full max-w-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="DD.MM.YYYY">{t('dateFormatDMY')}</SelectItem>
                      <SelectItem value="MM/DD/YYYY">{t('dateFormatMDY')}</SelectItem>
                      <SelectItem value="YYYY-MM-DD">{t('dateFormatYMD')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Number Format */}
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Hash className="h-4 w-4 text-muted-foreground" />
                    {t('numberFormat')}
                  </Label>
                  <p className="text-sm text-muted-foreground">{t('numberFormatDescription')}</p>
                  <Select value={numberFormat} onValueChange={setNumberFormat}>
                    <SelectTrigger className="w-full max-w-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="de-DE">{t('numberFormatDE')}</SelectItem>
                      <SelectItem value="en-US">{t('numberFormatEN')}</SelectItem>
                      <SelectItem value="de-CH">{t('numberFormatCH')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Currency */}
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <DollarSign className="h-4 w-4 text-muted-foreground" />
                    {t('currency')}
                  </Label>
                  <p className="text-sm text-muted-foreground">{t('currencyDescription')}</p>
                  <Select value={currency} onValueChange={setCurrency}>
                    <SelectTrigger className="w-full max-w-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="EUR">{t('currencyEUR')}</SelectItem>
                      <SelectItem value="USD">{t('currencyUSD')}</SelectItem>
                      <SelectItem value="GBP">{t('currencyGBP')}</SelectItem>
                      <SelectItem value="CHF">{t('currencyCHF')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Save Button */}
                <div className="pt-4 border-t">
                  <Button
                    onClick={handleSaveLocale}
                    disabled={localeSaving || !hasLocaleChanges}
                  >
                    {localeSaving ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        {t('saving')}
                      </>
                    ) : (
                      t('saveLocale')
                    )}
                  </Button>
                  {hasLocaleChanges && (
                    <p className="mt-2 text-sm text-amber-600">
                      {tCommon('unsavedChanges')}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Security Tab */}
          <TabsContent value="security" className="space-y-6 mt-6">
            {/* Change Password */}
            <Card>
              <CardHeader>
                <CardTitle>{t('changePassword')}</CardTitle>
                <CardDescription>{t('updatePassword')}</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleChangePassword} className="space-y-4">
                  {securityError && (
                    <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
                      {securityError}
                    </div>
                  )}
                  {securitySuccess && (
                    <div className="bg-green-50 text-green-700 text-sm p-3 rounded-md">
                      {securitySuccess}
                    </div>
                  )}
                  <div className="space-y-2">
                    <Label htmlFor="current-password">{t('currentPassword')}</Label>
                    <Input
                      id="current-password"
                      type="password"
                      autoComplete="current-password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="new-password">{t('newPassword')}</Label>
                    <Input
                      id="new-password"
                      type="password"
                      autoComplete="new-password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      minLength={12}
                      required
                    />
                    <p className="text-xs text-muted-foreground">
                      {t('passwordRequirements')}
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="confirm-password">{t('confirmNewPassword')}</Label>
                    <Input
                      id="confirm-password"
                      type="password"
                      autoComplete="new-password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      minLength={12}
                      required
                    />
                  </div>
                  <Button type="submit" disabled={isSubmitting}>
                    {isSubmitting ? t('changing') : t('changePassword')}
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* Two-Factor Authentication */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {totpStatus?.enabled ? (
                    <ShieldCheck className="h-5 w-5 text-green-600" />
                  ) : (
                    <Shield className="h-5 w-5" />
                  )}
                  {t('twoFactorAuth')}
                </CardTitle>
                <CardDescription>{t('twoFactorAuthDescription')}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {totpLoading ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : totpStatus?.enabled ? (
                  <div className="space-y-4">
                    {/* Status Badge */}
                    <div className="flex items-center gap-3">
                      <Badge variant="default" className="bg-green-600">
                        {t('totpEnabled')}
                      </Badge>
                      {totpStatus.verified_at && (
                        <span className="text-sm text-muted-foreground">
                          {t('totpEnabledAt', { date: new Date(totpStatus.verified_at).toLocaleDateString() })}
                        </span>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowTotpRegenerate(true)}
                      >
                        <RefreshCw className="h-4 w-4 mr-2" />
                        {t('totpManage')}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowTotpDisable(true)}
                        className="text-destructive hover:text-destructive"
                      >
                        <ShieldOff className="h-4 w-4 mr-2" />
                        {t('totpDisable')}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Status Badge */}
                    <div className="flex items-center gap-3">
                      <Badge variant="secondary">
                        {t('totpDisabled')}
                      </Badge>
                    </div>

                    {/* Setup Button */}
                    <Button onClick={() => setShowTotpSetup(true)}>
                      <ShieldCheck className="h-4 w-4 mr-2" />
                      {t('totpSetup')}
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Session Management */}
            <Card>
              <CardHeader>
                <CardTitle>{t('activeSessions')}</CardTitle>
                <CardDescription>{t('manageSessionsDescription')}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-3">
                    {t('sessionCompromised')}
                  </p>
                  <Button variant="outline" onClick={handleLogoutAllSessions}>
                    {t('signOutAllSessions')}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Notifications Tab */}
          <TabsContent value="notifications" className="space-y-6 mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="h-5 w-5" />
                  {t('notificationPreferences')}
                </CardTitle>
                <CardDescription>
                  {t('notificationDescription')}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {notifLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : (
                  <div className="space-y-6">
                    {notifError && (
                      <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
                        {notifError}
                      </div>
                    )}
                    {notifSuccess && (
                      <div className="bg-green-50 text-green-700 text-sm p-3 rounded-md">
                        {notifSuccess}
                      </div>
                    )}

                    {/* Legend */}
                    <div className="flex items-center gap-6 text-sm text-muted-foreground border-b pb-4">
                      <div className="flex items-center gap-2">
                        <Bell className="h-4 w-4" />
                        <span>{tCommon('enabled')}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <MessageSquare className="h-4 w-4" />
                        <span>{t('slackDm')}</span>
                      </div>
                    </div>

                    {Object.entries(eventTypesByCategory).map(([category, eventTypes]) => (
                      <div key={category} className="space-y-3">
                        <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">
                          {categoryLabels[category] || category}
                        </h4>
                        <div className="space-y-3">
                          {eventTypes.map(eventType => {
                            const pref = getPreference(eventType.code);
                            const isEnabled = pref?.enabled ?? true;
                            return (
                              <div
                                key={eventType.code}
                                className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                              >
                                <div className="flex-1">
                                  <p className="font-medium text-sm">{eventType.name}</p>
                                  <p className="text-xs text-muted-foreground">{eventType.description}</p>
                                </div>
                                <div className="flex items-center gap-4">
                                  {/* Enabled toggle */}
                                  <div className="flex items-center gap-2">
                                    <Switch
                                      checked={isEnabled}
                                      onCheckedChange={(checked) =>
                                        updateLocalPreference(eventType.code, { enabled: checked })
                                      }
                                    />
                                  </div>
                                  {/* Slack DM toggle */}
                                  <div className="flex items-center gap-2">
                                    <MessageSquare className="h-4 w-4 text-muted-foreground" />
                                    <Switch
                                      checked={pref?.slack_dm ?? false}
                                      disabled={!isEnabled}
                                      onCheckedChange={(checked) =>
                                        updateLocalPreference(eventType.code, { slack_dm: checked })
                                      }
                                    />
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}

                    <div className="pt-4 border-t">
                      <Button onClick={saveNotificationPreferences} disabled={notifSaving}>
                        {notifSaving ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            {t('saving')}
                          </>
                        ) : (
                          t('savePreferences')
                        )}
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* TOTP Dialogs */}
      <TotpSetupDialog
        open={showTotpSetup}
        onOpenChange={setShowTotpSetup}
        onSuccess={handleTotpSetupSuccess}
      />
      <TotpBackupCodesDialog
        open={showBackupCodes}
        onOpenChange={setShowBackupCodes}
        backupCodes={backupCodes}
      />
      <TotpDisableDialog
        open={showTotpDisable}
        onOpenChange={setShowTotpDisable}
        onSuccess={handleTotpDisableSuccess}
      />
      <TotpRegenerateDialog
        open={showTotpRegenerate}
        onOpenChange={setShowTotpRegenerate}
        onSuccess={handleTotpRegenerateSuccess}
      />

      {/* Image Crop Dialog */}
      {selectedImageSrc && (
        <ImageCropDialog
          open={cropDialogOpen}
          onOpenChange={(open) => {
            setCropDialogOpen(open);
            if (!open && selectedImageSrc) {
              URL.revokeObjectURL(selectedImageSrc);
              setSelectedImageSrc(null);
            }
          }}
          imageSrc={selectedImageSrc}
          onCropComplete={handleCroppedImageUpload}
          aspectRatio={1}
          circularCrop={true}
        />
      )}
    </AppLayout>
  );
}
