'use client';

import { useState, useEffect, useRef } from 'react';
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
import { Loader2, Bell, MessageSquare, User, Shield, Camera, Trash2 } from 'lucide-react';

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();

  // General tab state
  const [name, setName] = useState('');
  const [nameSaving, setNameSaving] = useState(false);
  const [generalError, setGeneralError] = useState('');
  const [generalSuccess, setGeneralSuccess] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [avatarUploading, setAvatarUploading] = useState(false);

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

  // Initialize name from user
  useEffect(() => {
    if (user?.name) {
      setName(user.name);
    }
  }, [user?.name]);

  // Fetch notification preferences
  useEffect(() => {
    const fetchNotificationPreferences = async () => {
      try {
        const response = await api.getNotificationPreferences();
        setNotifPrefs(response.preferences);
        setAvailableEventTypes(response.available_event_types);
      } catch (err) {
        console.error('Failed to fetch notification preferences:', err);
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
      setNotifSuccess('Notification preferences saved');
      setTimeout(() => setNotifSuccess(''), 3000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save preferences';
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

  const categoryLabels: Record<string, string> = {
    licenses: 'Licenses',
    employees: 'Employees',
    utilization: 'Utilization',
    costs: 'Costs',
    duplicates: 'Duplicates',
    system: 'System',
  };

  // Handle name save
  const handleSaveName = async () => {
    setNameSaving(true);
    setGeneralError('');
    setGeneralSuccess('');

    try {
      await api.updateProfile({ name: name || undefined });
      await refreshUser?.();
      setGeneralSuccess('Name updated successfully');
      setTimeout(() => setGeneralSuccess(''), 3000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update name';
      setGeneralError(errorMessage);
    } finally {
      setNameSaving(false);
    }
  };

  // Handle avatar upload
  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      setGeneralError('Invalid file type. Allowed: JPG, PNG, GIF, WebP');
      return;
    }

    // Validate file size (5MB)
    if (file.size > 5 * 1024 * 1024) {
      setGeneralError('File too large. Maximum size: 5 MB');
      return;
    }

    setAvatarUploading(true);
    setGeneralError('');
    setGeneralSuccess('');

    try {
      await api.uploadAvatar(file);
      await refreshUser?.();
      setGeneralSuccess('Avatar uploaded successfully');
      setTimeout(() => setGeneralSuccess(''), 3000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to upload avatar';
      setGeneralError(errorMessage);
    } finally {
      setAvatarUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
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
      setGeneralSuccess('Avatar deleted successfully');
      setTimeout(() => setGeneralSuccess(''), 3000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete avatar';
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
      setSecurityError('New passwords do not match');
      return;
    }

    if (newPassword.length < 12) {
      setSecurityError('Password must be at least 12 characters');
      return;
    }

    setIsSubmitting(true);

    try {
      await api.changePassword(currentPassword, newPassword);
      setSecuritySuccess('Password changed successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to change password';
      setSecurityError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogoutAllSessions = async () => {
    try {
      const result = await api.logoutAllSessions();
      setSecuritySuccess(`Logged out from ${result.sessions_revoked} sessions`);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to logout sessions';
      setSecurityError(errorMessage);
    }
  };

  return (
    <AppLayout>
      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Profile</h1>
          <p className="text-muted-foreground">Manage your account settings</p>
        </div>

        <Tabs defaultValue="general" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="general" className="flex items-center gap-2">
              <User className="h-4 w-4" />
              General
            </TabsTrigger>
            <TabsTrigger value="security" className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              Security
            </TabsTrigger>
            <TabsTrigger value="notifications" className="flex items-center gap-2">
              <Bell className="h-4 w-4" />
              Notifications
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
                <CardTitle>Profile Picture</CardTitle>
                <CardDescription>Upload a profile picture to personalize your account</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-6">
                  <div className="relative">
                    <div className="h-24 w-24 rounded-full bg-zinc-100 flex items-center justify-center overflow-hidden border-2 border-zinc-200">
                      {user?.picture_url ? (
                        <img
                          src={user.picture_url}
                          alt="Avatar"
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
                      onChange={handleAvatarUpload}
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
                      Upload Photo
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
                        Remove
                      </Button>
                    )}
                    <p className="text-xs text-muted-foreground">
                      JPG, PNG, GIF or WebP. Max 5MB.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Display Name */}
            <Card>
              <CardHeader>
                <CardTitle>Display Name</CardTitle>
                <CardDescription>This name will be shown across the application</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center gap-4">
                    <div className="flex-1">
                      <Input
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Enter your display name"
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
                          Saving...
                        </>
                      ) : (
                        'Save Name'
                      )}
                    </Button>
                  </div>
                  {name !== (user?.name || '') && (
                    <p className="text-sm text-amber-600">
                      You have unsaved changes
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Account Info */}
            <Card>
              <CardHeader>
                <CardTitle>Account Information</CardTitle>
                <CardDescription>Your account details (read-only)</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4">
                  <div className="space-y-2">
                    <Label className="text-muted-foreground text-xs">Email</Label>
                    <p className="font-medium">{user?.email}</p>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-muted-foreground text-xs">Roles</Label>
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

          {/* Security Tab */}
          <TabsContent value="security" className="space-y-6 mt-6">
            {/* Change Password */}
            <Card>
              <CardHeader>
                <CardTitle>Change Password</CardTitle>
                <CardDescription>Update your password</CardDescription>
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
                    <Label htmlFor="current-password">Current Password</Label>
                    <Input
                      id="current-password"
                      type="password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="new-password">New Password</Label>
                    <Input
                      id="new-password"
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      minLength={12}
                      required
                    />
                    <p className="text-xs text-muted-foreground">
                      Minimum 12 characters, including uppercase, lowercase, number, and special character.
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="confirm-password">Confirm New Password</Label>
                    <Input
                      id="confirm-password"
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      minLength={12}
                      required
                    />
                  </div>
                  <Button type="submit" disabled={isSubmitting}>
                    {isSubmitting ? 'Changing...' : 'Change Password'}
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* Session Management */}
            <Card>
              <CardHeader>
                <CardTitle>Active Sessions</CardTitle>
                <CardDescription>Manage your active sessions</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-3">
                    If you suspect your account has been compromised, you can sign out of all active sessions.
                  </p>
                  <Button variant="outline" onClick={handleLogoutAllSessions}>
                    Sign out all other sessions
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
                  Notification Preferences
                </CardTitle>
                <CardDescription>
                  Choose how and when you want to be notified about license management events
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
                        <span>Enabled</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <MessageSquare className="h-4 w-4" />
                        <span>Slack DM</span>
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
                            Saving...
                          </>
                        ) : (
                          'Save Preferences'
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
    </AppLayout>
  );
}
