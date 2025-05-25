"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import {
  Activity,
  Settings,
  Repeat,
  BarChart2,
  Menu,
} from "lucide-react";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: Activity },
  { href: "/strategies", label: "Strategies", icon: Repeat },
  { href: "/backtest",  label: "Backtest",  icon: BarChart2 },
  { href: "/settings",  label: "Settings",  icon: Settings },
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside className="flex h-full w-56 shrink-0 flex-col bg-background-light text-foreground">
      <div className="flex items-center gap-2 px-5 py-4 text-lg font-semibold">
        <Menu className="h-5 w-5" />
        <span>TRADING BOT</span>
      </div>

      <nav className="mt-4 flex flex-col gap-1 px-2">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = path === href;
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 rounded-md px-4 py-3 text-sm font-medium",
                active
                  ? "bg-primary/20 text-primary"
                  : "hover:bg-background focus-visible:bg-background"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
