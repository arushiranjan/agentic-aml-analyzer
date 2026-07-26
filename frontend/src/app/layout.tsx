import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";

export const metadata: Metadata = {
  title: "Eco-Loop Building Agents",
  description: "Autonomous closed-loop building optimization dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background min-h-screen font-sans antialiased">
        <div className="mx-auto flex max-w-[1400px] gap-6 p-6">
          <Sidebar />
          <main className="flex-1">{children}</main>
        </div>
      </body>
    </html>
  );
}
