"use client";

import { Menu } from "lucide-react";
import { usePathname } from "next/navigation";
import { Suspense, useState } from "react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { navItemFor } from "./nav-items";
import { SidebarContent } from "./sidebar-content";
import { StatusPill, StatusPillSkeleton } from "./status-pill";
import { ThemeToggle } from "./theme-toggle";

export function TopBar() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const current = navItemFor(pathname);
  const Icon = current?.icon;

  return (
    <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 border-b bg-background/80 px-4 backdrop-blur-md md:px-6">
      <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
        <SheetTrigger asChild>
          <Button
            variant="ghost"
            size="icon-sm"
            className="-ml-1.5 md:hidden"
            aria-label="Open navigation"
          >
            <Menu />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-64 bg-sidebar p-0" aria-describedby={undefined}>
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <SidebarContent onNavigate={() => setMenuOpen(false)} />
        </SheetContent>
      </Sheet>

      <h1 className="flex min-w-0 items-center gap-2 text-sm font-semibold">
        {Icon && <Icon className="size-4 text-muted-foreground" aria-hidden />}
        <span className="truncate">{current?.label ?? "Sentiment Pulse"}</span>
      </h1>

      <div className="ml-auto flex items-center gap-1.5">
        {/* Suspense lets the prerendered shell show a placeholder until the browser checks health. */}
        <Suspense fallback={<StatusPillSkeleton />}>
          <StatusPill />
        </Suspense>
        <ThemeToggle />
      </div>
    </header>
  );
}
