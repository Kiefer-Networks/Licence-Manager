'use client';

import { useState, useEffect, useRef } from 'react';
import { api, UserNotificationPreference, NotificationEventType, UserNotificationPreferenceUpdate } from '@/lib/api';

/**
 * Translation functions required by the useProfile hook.
 */
interface ProfileTranslations {
  t: (key: string, params?: Record<string, string | number>) => string;
  tCommon: (key: string) => string;
}

/**
 * Return type for the useProfile hook.
 */
export interface UseProfileReturn {
  // Locale settings state
  dateFormat: string;
  setDateFormat: (v: string) => void;
  numberFormat: string;
  setNumberFormat: (v: string) => void;
  currency: string;
  setCurrency: (v: string) => void;
  localeSaving: boolean;
  localeSuccess: string;
  localeError: string;

  // General tab state
  name: string;
  setName: (v: string) => void;
  nameSaving: boolean;
  generalError: string;
  generalSuccess: string;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  avatarUploading: boolean;
  cropDialogOpen: boolean;
  setCropDialogOpen: (v: boolean) => void;
  selectedImageSrc: string | null;
  setSelectedImageSrc: (v: string | null) => void;

  // Security tab state
  securityError: string;
  securitySuccess: string;

  // Notification preferences state
  notifPrefs: UserNotificationPreference[];
  availableEventTypes: NotificationEventType[];
  notifLoading: boolean;
  notifSaving: boolean;
  notifError: string;
  notifSuccess: string;

  // Derived data
  eventTypesByCategory: Record<string, NotificationEventType[]>;
  hasLocaleChanges: boolean;

  // Handlers
  getPreference: (eventType: string) => UserNotificationPreference | undefined;
  updateLocalPreference: (eventType: string, updates: Partial<UserNotificationPreferenceUpdate>) => void;
  saveNotificationPreferences: () => Promise<void>;
  handleSaveName: () => Promise<void>;
  handleAvatarSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleCroppedImageUpload: (croppedBlob: Blob) => Promise<void>;
  handleDeleteAvatar: () => Promise<void>;
  handleLogoutAllSessions: () => Promise<void>;
  handleSaveLocale: () => Promise<void>;
}

/**
 * Custom hook that encapsulates all business logic for the Profile page.
 * Manages profile data, locale settings, notifications, and avatar upload.
 */
export function useProfile(
  { t, tCommon }: ProfileTranslations,
  user: { name?: string; email?: string; picture_url?: string; date_format?: string; number_format?: string; currency?: string; roles: string[] } | null | undefined,
  refreshUser: (() => Promise<void>) | undefined,
): UseProfileReturn {
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
  const [securityError, setSecurityError] = useState('');
  const [securitySuccess, setSecuritySuccess] = useState('');

  // Notification preferences state
  const [notifPrefs, setNotifPrefs] = useState<UserNotificationPreference[]>([]);
  const [availableEventTypes, setAvailableEventTypes] = useState<NotificationEventType[]>([]);
  const [notifLoading, setNotifLoading] = useState(true);
  const [notifSaving, setNotifSaving] = useState(false);
  const [notifError, setNotifError] = useState('');
  const [notifSuccess, setNotifSuccess] = useState('');

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

  const handleLogoutAllSessions = async () => {
    try {
      const result = await api.logoutAllSessions();
      setSecuritySuccess(t('loggedOutSessions', { count: result.sessions_revoked }));
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : t('failedToUpdate');
      setSecurityError(errorMessage);
    }
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

  return {
    // Locale settings state
    dateFormat,
    setDateFormat,
    numberFormat,
    setNumberFormat,
    currency,
    setCurrency,
    localeSaving,
    localeSuccess,
    localeError,

    // General tab state
    name,
    setName,
    nameSaving,
    generalError,
    generalSuccess,
    fileInputRef,
    avatarUploading,
    cropDialogOpen,
    setCropDialogOpen,
    selectedImageSrc,
    setSelectedImageSrc,

    // Security tab state
    securityError,
    securitySuccess,

    // Notification preferences state
    notifPrefs,
    availableEventTypes,
    notifLoading,
    notifSaving,
    notifError,
    notifSuccess,

    // Derived data
    eventTypesByCategory,
    hasLocaleChanges,

    // Handlers
    getPreference,
    updateLocalPreference,
    saveNotificationPreferences,
    handleSaveName,
    handleAvatarSelect,
    handleCroppedImageUpload,
    handleDeleteAvatar,
    handleLogoutAllSessions,
    handleSaveLocale,
  };
}
