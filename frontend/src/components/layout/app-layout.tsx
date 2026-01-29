'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Button } from '@/components/ui/button';
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
} from 'lucide-react';

interface AppLayoutProps {
  children: React.ReactNode;
}

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Licenses', href: '/licenses', icon: Key },
  { name: 'Employees', href: '/users', icon: Users },
  { name: 'Providers', href: '/providers', icon: Package },
  { name: 'Reports', href: '/reports', icon: FileText },
  { name: 'Settings', href: '/settings', icon: Settings },
];

// Dev mode mock user
const devUser = {
  name: 'Dev Admin',
  email: 'dev@example.com',
};

export function AppLayout({ children }: AppLayoutProps) {
  const pathname = usePathname();

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
          <nav className="flex-1 px-3 py-3 space-y-0.5">
            {navigation.map((item) => {
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
          </nav>

          {/* User menu */}
          <div className="p-3 border-t border-zinc-200">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="w-full justify-start h-auto py-2 px-2.5 hover:bg-zinc-50">
                  <div className="flex items-center gap-2.5">
                    <div className="h-7 w-7 rounded-full bg-zinc-100 flex items-center justify-center flex-shrink-0">
                      <span className="text-xs font-medium text-zinc-600">
                        {devUser.name.charAt(0)}
                      </span>
                    </div>
                    <div className="text-left min-w-0">
                      <p className="text-[13px] font-medium text-zinc-900 truncate">{devUser.name}</p>
                      <p className="text-[11px] text-zinc-500 truncate">
                        {devUser.email}
                      </p>
                    </div>
                  </div>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" side="top" className="w-52">
                <DropdownMenuItem asChild>
                  <Link href="/settings" className="cursor-pointer">
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem disabled className="text-zinc-400">
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
