import Link from "next/link";
import { LogoMark } from "./logo";
import { SidebarNav } from "./sidebar-nav";

/** Shared by the desktop sidebar and the mobile navigation sheet. */
export function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col gap-6 px-3 py-4">
      <Link
        href="/"
        onClick={onNavigate}
        className="flex items-center gap-2.5 rounded-md px-1.5 py-0.5 outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        <LogoMark />
        <span className="text-[15px] font-semibold tracking-tight">Sentiment Pulse</span>
      </Link>
      <div className="grid gap-1.5">
        <p className="px-2.5 text-xs font-medium text-muted-foreground/80">Workspace</p>
        <SidebarNav onNavigate={onNavigate} />
      </div>
    </div>
  );
}
