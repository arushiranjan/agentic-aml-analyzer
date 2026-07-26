"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Gauge, Leaf, LayoutDashboard, Settings, Thermometer } from "lucide-react";

const items = [
  { label: "Overview", href: "/overview", icon: LayoutDashboard },
  { label: "Live Building", href: "/live-building", icon: Thermometer },
  { label: "Energy", href: "/energy", icon: Gauge },
  { label: "Carbon", href: "/carbon", icon: Leaf },
  { label: "Agent Reasoning", href: "/agent-reasoning", icon: Activity },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="glass hidden w-60 shrink-0 flex-col gap-1 rounded-2xl p-4 lg:flex">
      <div className="mb-6 flex items-center gap-2 px-2">
        <div className="h-2.5 w-2.5 rounded-full bg-emerald shadow-[0_0_8px_2px_rgba(16,185,129,0.6)]" />
        <span className="text-sm font-semibold text-white">Eco-Loop</span>
      </div>
      {items.map(({ label, href, icon: Icon }) => {
        const active = pathname === href || (href === "/overview" && pathname === "/");
        return (
          <Link
            key={label}
            href={href}
            className={`flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors ${
              active ? "bg-cyan/10 text-cyan" : "text-muted hover:bg-white/5 hover:text-white"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        );
      })}
    </aside>
  );
}
