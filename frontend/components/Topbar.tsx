"use client";

import { Bell, UserCircle } from "lucide-react";

export default function Topbar() {
  return (
    <header className="flex items-center justify-end gap-4 border-b border-border bg-background-light px-6 py-3">
      <button className="rounded-full p-2 hover:bg-background">
        <Bell className="h-5 w-5" />
      </button>

      <div className="flex items-center gap-2">
        <UserCircle className="h-6 w-6" />
        <span className="text-sm">Guest</span>
      </div>
    </header>
  );
}
