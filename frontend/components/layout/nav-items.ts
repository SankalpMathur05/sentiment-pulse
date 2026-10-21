import {
  BrainCircuit,
  FileSpreadsheet,
  History,
  LayoutDashboard,
  ScanText,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Analyze", icon: ScanText },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/history", label: "History", icon: History },
  { href: "/batch", label: "Batch", icon: FileSpreadsheet },
  { href: "/model", label: "Model", icon: BrainCircuit },
];

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

export function navItemFor(pathname: string): NavItem | undefined {
  return NAV_ITEMS.find((item) => isActive(pathname, item.href));
}
