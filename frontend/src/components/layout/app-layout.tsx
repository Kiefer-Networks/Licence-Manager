'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Button } from '@/components/ui/button';
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
} from 'lucide-react';
import { useAuth, Permissions } from '@/components/auth-provider';

interface AppLayoutProps {
  children: React.ReactNode;
}

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  permission?: string;
}

const mainNavigation: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, permission: Permissions.DASHBOARD_VIEW },
  { name: 'Licenses', href: '/licenses', icon: Key, permission: Permissions.LICENSES_VIEW },
  { name: 'Employees', href: '/users', icon: Users, permission: Permissions.USERS_VIEW },
  { name: 'Providers', href: '/providers', icon: Package, permission: Permissions.PROVIDERS_VIEW },
  { name: 'Reports', href: '/reports', icon: FileText, permission: Permissions.REPORTS_VIEW },
  { name: 'Settings', href: '/settings', icon: Settings, permission: Permissions.SETTINGS_VIEW },
];

const adminNavigation: NavItem[] = [
  { name: 'Admin Users', href: '/admin/users', icon: UserCog, permission: Permissions.ADMIN_USERS_VIEW },
  { name: 'Roles', href: '/admin/roles', icon: Shield, permission: Permissions.ROLES_VIEW },
  { name: 'Audit Log', href: '/admin/audit', icon: ScrollText, permission: Permissions.AUDIT_VIEW },
];

export function AppLayout({ children }: AppLayoutProps) {
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

  const displayName = user?.name || user?.email || 'User';
  const displayEmail = user?.email || '';

  return (
    <div className="min-h-screen bg-zinc-50">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 w-60 bg-white border-r border-zinc-200">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center h-14 px-5 border-b border-zinc-200">
            <Link href="/dashboard" className="flex items-center gap-2.5">
              <div className="h-7 w-7 rounded-md bg-zinc-900 flex items-center justify-center">
                <Key className="h-4 w-4 text-white" />
              </div>
              <span className="font-semibold text-[15px] tracking-tight">Licenses</span>
            </Link>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
            {visibleMainNav.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-2.5 px-2.5 py-2 rounded-md text-[13px] font-medium transition-colors',
                    isActive
                      ? 'bg-zinc-100 text-zinc-900'
                      : 'text-zinc-500 hover:bg-zinc-50 hover:text-zinc-900'
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {item.name}
                </Link>
              );
            })}

            {/* Admin section */}
            {visibleAdminNav.length > 0 && (
              <>
                <div className="pt-4 pb-1 px-2.5">
                  <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                    Administration
                  </span>
                </div>
                {visibleAdminNav.map((item) => {
                  const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={cn(
                        'flex items-center gap-2.5 px-2.5 py-2 rounded-md text-[13px] font-medium transition-colors',
                        isActive
                          ? 'bg-zinc-100 text-zinc-900'
                          : 'text-zinc-500 hover:bg-zinc-50 hover:text-zinc-900'
                      )}
                    >
                      <item.icon className="h-4 w-4" />
                      {item.name}
                    </Link>
                  );
                })}
              </>
            )}
          </nav>

          {/* User menu */}
          <div className="p-3 border-t border-zinc-200">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="w-full justify-start h-auto py-2 px-2.5 hover:bg-zinc-50">
                  <div className="flex items-center gap-2.5">
                    <div className="h-7 w-7 rounded-full bg-zinc-100 flex items-center justify-center flex-shrink-0">
                      <span className="text-xs font-medium text-zinc-600">
                        {displayName.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div className="text-left min-w-0">
                      <p className="text-[13px] font-medium text-zinc-900 truncate">{displayName}</p>
                      <p className="text-[11px] text-zinc-500 truncate">
                        {displayEmail}
                      </p>
                    </div>
                  </div>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" side="top" className="w-52">
                <div className="px-2 py-1.5 text-xs text-zinc-500">
                  {user?.roles.join(', ') || 'No roles'}
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/profile" className="cursor-pointer">
                    <UserCog className="mr-2 h-4 w-4" />
                    Profile
                  </Link>
                </DropdownMenuItem>
                {hasPermission(Permissions.SETTINGS_VIEW) && (
                  <DropdownMenuItem asChild>
                    <Link href="/settings" className="cursor-pointer">
                      <Settings className="mr-2 h-4 w-4" />
                      Settings
                    </Link>
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="cursor-pointer text-red-600">
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign out
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
