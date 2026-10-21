import { SidebarContent } from "./sidebar-content";
import { TopBar } from "./top-bar";

const FOOTER_NOTE =
  "Predictions come from a TF-IDF + Logistic Regression model trained on 2015 US airline tweets. Confidence values are estimates.";

/** Sidebar (desktop) or sheet (mobile) navigation, top bar, page content and footer note. */
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-svh">
      <a
        href="#main"
        className="sr-only z-50 rounded-md bg-background px-3 py-2 text-sm font-medium shadow-md ring-1 ring-border focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >
        Skip to content
      </a>

      <aside className="sticky top-0 hidden h-svh w-60 shrink-0 border-r bg-sidebar md:block">
        <SidebarContent />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main id="main" className="flex-1">
          {children}
        </main>
        <footer className="border-t px-4 py-5 md:px-8">
          <p className="mx-auto max-w-6xl text-xs text-muted-foreground">{FOOTER_NOTE}</p>
        </footer>
      </div>
    </div>
  );
}
