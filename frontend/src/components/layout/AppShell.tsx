"use client";

import Sidebar from "./Sidebar";
import Navbar  from "./Navbar";

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen" style={{ background: "#080c14" }}>
      {/* Fixed sidebar */}
      <Sidebar />

      {/* Main column */}
      <div className="flex flex-col flex-1 min-w-0" style={{ marginLeft: "220px" }}>
        <Navbar />
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
