import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import "../globals.css";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      <Sidebar />

      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar />
        {children}
      </div>
    </div>
  );
}
