import { X, Home, User, Settings, LogOut, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Separator } from '@/components/ui/separator';

interface AppSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const NAV_ITEMS = [
  { icon: Home, label: '홈', href: '/' },
  { icon: User, label: '내 정보', href: '/profile' },
  { icon: Settings, label: '설정', href: '/settings' },
  { icon: Shield, label: '관리자', href: '/admin' },
] as const;

export function AppSidebar({ isOpen, onClose }: AppSidebarProps) {
  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent side="left" className="w-72 p-0">
        <SheetHeader className="sr-only">
          <SheetTitle>네비게이션</SheetTitle>
          <SheetDescription>앱 메뉴</SheetDescription>
        </SheetHeader>

        {/* 상단 프로필 영역 */}
        <div className="p-6 pb-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-sm">2026 UOS SMASH</p>
              <p className="text-xs text-muted-foreground mt-0.5">로그인이 필요합니다</p>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose} className="size-8">
              <X className="size-4" />
            </Button>
          </div>
        </div>

        <Separator />

        {/* 네비게이션 메뉴 */}
        <nav className="flex flex-col gap-1 p-3">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.label}
              onClick={onClose}
              className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium text-foreground hover:bg-accent transition-colors"
            >
              <item.icon className="size-4 text-muted-foreground" />
              {item.label}
            </button>
          ))}
        </nav>

        <Separator />

        {/* 하단 로그아웃 */}
        <div className="p-3">
          <button
            onClick={onClose}
            className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium text-destructive hover:bg-destructive/10 transition-colors w-full"
          >
            <LogOut className="size-4" />
            로그아웃
          </button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
