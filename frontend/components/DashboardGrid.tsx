import React from "react";

export default function DashboardGrid({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="grid flex-1 grid-cols-12 gap-6 p-6">{children}</div>
  );
}
