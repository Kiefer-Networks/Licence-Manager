'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { LanguageSwitcher } from '@/components/ui/language-switcher';
import { useKeyboardShortcuts } from '@/hooks/use-keyboard-shortcuts';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Key,
  Users,
  FileText,
  Settings,
  LogOut,
  Package,
  Shield,
  UserCog,
  ScrollText,
  Clock,
  Wallet,
} from 'lucide-react';
import { useAuth, Permissions } from '@/components/auth-provider';

interface AppLayoutProps {
  children: React.ReactNode;
}

interface NavItem {
  nameKey: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  permission?: string;
}

const mainNavigation: NavItem[] = [
  { nameKey: 'dashboard', href: '/dashboard', icon: LayoutDashboard, permission: Permissions.DASHBOARD_VIEW },
  { nameKey: 'licenses', href: '/licenses', icon: Key, permission: Permissions.LICENSES_VIEW },
  { nameKey: 'lifecycle', href: '/lifecycle', icon: Clock, permission: Permissions.LICENSES_VIEW },
  { nameKey: 'employees', href: '/users', icon: Users, permission: Permissions.USERS_VIEW },
  { nameKey: 'providers', href: '/providers', icon: Package, permission: Permissions.PROVIDERS_VIEW },
  { nameKey: 'finance', href: '/finance', icon: Wallet, permission: Permissions.PAYMENT_METHODS_VIEW },
  { nameKey: 'reports', href: '/reports', icon: FileText, permission: Permissions.REPORTS_VIEW },
];

const adminNavigation: NavItem[] = [
  { nameKey: 'adminUsers', href: '/admin/users', icon: UserCog, permission: Permissions.ADMIN_USERS_VIEW },
  { nameKey: 'roles', href: '/admin/roles', icon: Shield, permission: Permissions.ROLES_VIEW },
  { nameKey: 'auditLog', href: '/admin/audit', icon: ScrollText, permission: Permissions.AUDIT_VIEW },
  { nameKey: 'settings', href: '/settings', icon: Settings, permission: Permissions.SETTINGS_VIEW },
];

export function AppLayout({ children }: AppLayoutProps) {
  const t = useTranslations('nav');
  const tCommon = useTranslations('common');
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout, hasPermission, isLoading, isAuthenticated, isSuperAdmin } = useAuth();

  // Enable keyboard shortcuts for navigation (Alt+D, Alt+L, etc.)
  useKeyboardShortcuts();

  // Redirect to login if not authenticated (must be in useEffect to avoid render loop)
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/auth/signin');
    }
  }, [isLoading, isAuthenticated, router]);

  // Filter navigation items based on permissions
  const visibleMainNav = mainNavigation.filter(
    item => !item.permission || isSuperAdmin || hasPermission(item.permission)
  );
  const visibleAdminNav = adminNavigation.filter(
    item => !item.permission || isSuperAdmin || hasPermission(item.permission)
  );

  const handleLogout = async () => {
    await logout();
  };

  // Show loading state or redirect pending
  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  const displayName = user?.name || user?.email || tCommon('user');
  const displayEmail = user?.email || '';

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 w-60 bg-white dark:bg-zinc-900 border-r border-zinc-200 dark:border-zinc-800">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between h-14 px-5 border-b border-zinc-200 dark:border-zinc-800">
            <Link href="/dashboard" className="flex items-center gap-2.5">
              <div className="h-7 w-7 rounded-md bg-zinc-900 dark:bg-zinc-100 flex items-center justify-center">
                <Key className="h-4 w-4 text-white dark:text-zinc-900" />
              </div>
              <span className="font-semibold text-[15px] tracking-tight text-zinc-900 dark:text-zinc-100">{t('licenses')}</span>
            </Link>
            <LanguageSwitcher />
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
            {visibleMainNav.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
              return (
                <Link
                  key={item.nameKey}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-2.5 px-2.5 py-2 rounded-md text-[13px] font-medium transition-colors',
                    isActive
                      ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100'
                      : 'text-zinc-500 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-zinc-100'
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {t(item.nameKey)}
                </Link>
              );
            })}

            {/* Admin section */}
            {visibleAdminNav.length > 0 && (
              <>
                <div className="pt-4 pb-1 px-2.5">
                  <span className="text-[11px] font-semibold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider">
                    {t('administration')}
                  </span>
                </div>
                {visibleAdminNav.map((item) => {
                  const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
                  return (
                    <Link
                      key={item.nameKey}
                      href={item.href}
                      className={cn(
                        'flex items-center gap-2.5 px-2.5 py-2 rounded-md text-[13px] font-medium transition-colors',
                        isActive
                          ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100'
                          : 'text-zinc-500 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-zinc-100'
                      )}
                    >
                      <item.icon className="h-4 w-4" />
                      {t(item.nameKey)}
                    </Link>
                  );
                })}
              </>
            )}
          </nav>

          {/* User menu */}
          <div className="p-3 border-t border-zinc-200 dark:border-zinc-800">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="w-full justify-start h-auto py-2 px-2.5 hover:bg-zinc-50 dark:hover:bg-zinc-800">
                  <div className="flex items-center gap-2.5">
                    <div className="h-7 w-7 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center flex-shrink-0 overflow-hidden">
                      {user?.picture_url ? (
                        <img
                          src={user.picture_url}
                          alt=""
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <span className="text-xs font-medium text-zinc-600 dark:text-zinc-300">
                          {displayName.charAt(0).toUpperCase()}
                        </span>
                      )}
                    </div>
                    <div className="text-left min-w-0">
                      <p className="text-[13px] font-medium text-zinc-900 dark:text-zinc-100 truncate">{displayName}</p>
                      <p className="text-[11px] text-zinc-500 dark:text-zinc-400 truncate">
                        {displayEmail}
                      </p>
                    </div>
                  </div>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" side="top" className="w-52">
                <div className="px-2 py-1.5 text-xs text-zinc-500 dark:text-zinc-400">
                  {user?.roles.join(', ') || t('noRoles')}
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/profile" className="cursor-pointer">
                    <UserCog className="mr-2 h-4 w-4" />
                    {t('profile')}
                  </Link>
                </DropdownMenuItem>
                {hasPermission(Permissions.SETTINGS_VIEW) && (
                  <DropdownMenuItem asChild>
                    <Link href="/settings" className="cursor-pointer">
                      <Settings className="mr-2 h-4 w-4" />
                      {t('settings')}
                    </Link>
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="cursor-pointer text-red-600 dark:text-red-400">
                  <LogOut className="mr-2 h-4 w-4" />
                  {t('signOut')}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="pl-60">
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
