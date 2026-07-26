# Dashboard Design — Eco-Loop Building Agents

## Design Philosophy

The dashboard is modeled after enterprise monitoring platforms like **Datadog**, **Grafana**, **Azure Portal**, and **Tesla Energy**. It should feel premium, data-rich, and professional — not like a simple academic prototype.

---

## Color Palette

### Primary Palette

| Role | Name | Hex | HSL | Usage |
|---|---|---|---|---|
| Background | Slate 900 | `#0F172A` | `222 47% 11%` | Page background |
| Surface | Slate 800 | `#1E293B` | `217 33% 17%` | Card backgrounds |
| Elevated | Slate 700 | `#334155` | `215 25% 27%` | Hover states, borders |
| Text Primary | Slate 100 | `#F1F5F9` | `210 40% 96%` | Headings, values |
| Text Secondary | Slate 400 | `#94A3B8` | `215 16% 65%` | Labels, descriptions |
| Text Muted | Slate 500 | `#64748B` | `215 16% 47%` | Timestamps, tertiary |

### Semantic Colors

| Role | Name | Hex | Usage |
|---|---|---|---|
| Success / Energy | Emerald 500 | `#10B981` | Energy metrics, positive trends |
| Warning | Amber 500 | `#F59E0B` | Warnings, moderate alerts |
| AI Activity | Cyan 400 | `#22D3EE` | AI reasoning, MCP calls |
| Critical | Orange 500 | `#F97316` | Critical alerts, errors |
| Accent | Violet 500 | `#8B5CF6` | Interactive elements, highlights |
| Danger | Red 500 | `#EF4444` | Failures, severe alerts |

### Glassmorphism Properties

```css
/* Glass card */
.glass-card {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

/* Glass card hover */
.glass-card:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.15);
    transform: translateY(-1px);
    transition: all 0.2s ease;
}
```

---

## Typography

| Element | Font | Weight | Size | Color |
|---|---|---|---|---|
| Page title | Inter | 700 | 24px | Slate 100 |
| Section title | Inter | 600 | 18px | Slate 100 |
| Card title | Inter | 600 | 14px | Slate 300 |
| Metric value | JetBrains Mono | 700 | 32px | White |
| Metric unit | JetBrains Mono | 400 | 14px | Slate 400 |
| Body text | Inter | 400 | 14px | Slate 300 |
| Label | Inter | 500 | 12px | Slate 400 |
| Timestamp | JetBrains Mono | 400 | 12px | Slate 500 |

---

## Layout Structure

### Navigation (Sidebar)

```
┌──────────┐
│ 🏢 Eco   │
│   Loop   │
├──────────┤
│ 📊 Overview │
│ 🏗️ Building │
│ ❄️ HVAC     │
│ 🌤️ Weather  │
│ 👥 Occupancy│
│ 🌡️ Comfort  │
│ ⚡ Energy   │
│ 🌿 Carbon   │
│ 💰 Savings  │
│ ⏱️ Timeline │
│ 🤖 AI Agent │
│ 📡 Sensors  │
│ 📈 Trends   │
│ 📋 Reports  │
│ ⚙️ Settings │
└──────────┘
```

### Main Dashboard (Overview Page)

```
┌─────────────────────────────────────────────────────────────────┐
│  🏢 Eco-Loop Building Intelligence              🟢 All Online  │
│  Autonomous Building Optimization Dashboard     Last: 2m ago   │
├────────┬────────┬────────┬────────┬────────┬────────┬──────────┤
│⚡Energy│💰Saving│🌡️Comfrt│🌿Carbon│🤖AI    │👥Occup │❄️HVAC   │
│142 kWh │ 23.4%  │0.3 PMV │-18.2%  │Active  │  47    │Cooling  │
│↓ 12%   │↑ 2.1%  │ Good   │↓ 3.1kg │87% cnf │/56 max │72% fan  │
├────────┴────────┴────────┴────────┴────────┴────────┴──────────┤
│                                                                 │
│  📈 Energy Timeline                        [1H] [6H] [24H] [7D]│
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  ████                          Area Chart               │    │
│  │  ████████                      ── Baseline (gray)       │    │
│  │  ████████████                  ── Optimized (emerald)   │    │
│  │  ████████████████              ░░ Savings (green fill)  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
├─────────────────────────────┬───────────────────────────────────┤
│                             │                                   │
│  🌡️ Zone Temperatures       │  🤖 AI Reasoning                  │
│  ┌───────────────────────┐  │  ┌─────────────────────────────┐  │
│  │  Line chart            │  │  │ 🧠 Latest Analysis          │  │
│  │  -- Zone 1 (23.4°C)   │  │  │ "Zone 3 cooling setpoint   │  │
│  │  -- Zone 2 (22.8°C)   │  │  │  can be raised by 1°C..."  │  │
│  │  -- Zone 3 (24.1°C)   │  │  │                             │  │
│  │  -- Zone 4 (23.0°C)   │  │  │ Confidence: 87%            │  │
│  │  -- Core   (22.5°C)   │  │  │ Expected savings: 3.2 kWh  │  │
│  └───────────────────────┘  │  │                             │  │
│                             │  │ 🔧 Tool Calls:              │  │
│                             │  │ ✅ read_building_state      │  │
│                             │  │ ✅ update_hvac (Zone 3)     │  │
│                             │  │ ✅ run_simulation           │  │
│                             │  │ ✅ analyze_comfort          │  │
│                             │  └─────────────────────────────┘  │
├─────────────────────────────┼───────────────────────────────────┤
│                             │                                   │
│  ❄️ HVAC Status              │  📊 Comfort Analysis             │
│  ┌───────────────────────┐  │  ┌─────────────────────────────┐  │
│  │ Mode: Cooling         │  │  │ PMV Gauge: [-3 ─●─ +3]     │  │
│  │ Supply Air: 13°C      │  │  │ Current: 0.3 (Comfortable) │  │
│  │ Fan Speed: 72%        │  │  │                             │  │
│  │ COP: 3.8              │  │  │ PPD: 7%                    │  │
│  │ Runtime: 6.2 hrs      │  │  │ Category: A (< 6%)         │  │
│  └───────────────────────┘  │  └─────────────────────────────┘  │
│                             │                                   │
├─────────────────────────────┼───────────────────────────────────┤
│                             │                                   │
│  🌤️ Weather                 │  📋 Decision Timeline             │
│  ┌───────────────────────┐  │  ┌─────────────────────────────┐  │
│  │ 🌡️ 28.3°C  ☁️ Partly  │  │  │ 10:15 ✅ Raised Zone 3    │  │
│  │ 💧 45% RH             │  │  │       cooling SP to 24°C   │  │
│  │ 💨 3.2 m/s NW         │  │  │                             │  │
│  │ ☀️ 620 W/m²           │  │  │ 10:10 🧠 Analyzed: Zone 3  │  │
│  │                       │  │  │       overcooled by 1.5°C   │  │
│  │ Forecast: Clear       │  │  │                             │  │
│  └───────────────────────┘  │  │ 10:05 📊 Baseline sim done  │  │
│                             │  │       Energy: 165 kWh       │  │
│                             │  │                             │  │
│                             │  │ 10:00 🚀 Cycle #12 started  │  │
│                             │  └─────────────────────────────┘  │
├─────────────────────────────┴───────────────────────────────────┤
│                                                                 │
│  📈 Historical Trends           [Energy] [Comfort] [HVAC] [All]│
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Multi-line chart with selectable metrics                │    │
│  │  Zoomable, pannable                                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📡 Sensor Data Table                          [Export CSV]     │
│  ┌────────┬──────┬──────┬──────┬──────┬──────┬────────────┐    │
│  │ Zone   │ Temp │ Hum  │ CO2  │ Lux  │ Occ  │ Status     │    │
│  ├────────┼──────┼──────┼──────┼──────┼──────┼────────────┤    │
│  │ Zone 1 │23.4°C│ 45%  │ 620  │ 420  │  12  │ ✅ Good    │    │
│  │ Zone 2 │22.8°C│ 48%  │ 580  │ 380  │   8  │ ✅ Good    │    │
│  │ Zone 3 │24.1°C│ 42%  │ 710  │ 450  │  15  │ ⚠️ Warm    │    │
│  │ Zone 4 │23.0°C│ 50%  │ 540  │ 360  │   6  │ ✅ Good    │    │
│  │ Core   │22.5°C│ 47%  │ 490  │ 400  │   6  │ ✅ Good    │    │
│  └────────┴──────┴──────┴──────┴──────┴──────┴────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Inventory

### Metric Cards (Top Row)

Glass cards with:
- **Icon** (emoji or Lucide icon)
- **Label** (Inter 500 12px, Slate 400)
- **Value** (JetBrains Mono 700 32px, White)
- **Unit** (JetBrains Mono 400 14px, Slate 400)
- **Trend arrow** (▲ emerald or ▼ red, with percentage)
- **Subtle pulse animation** when value changes

### Charts (Recharts)

| Chart | Type | Data | Colors |
|---|---|---|---|
| Energy Timeline | AreaChart | Baseline vs Optimized over time | Gray (baseline), Emerald (optimized) |
| Zone Temperatures | LineChart | 5 zones over time | Distinct colors per zone |
| Comfort PMV | Gauge/RadialBar | Current PMV value | Green (-0.5 to +0.5), yellow, red |
| HVAC Load | BarChart | Heating vs Cooling per zone | Blue (cooling), Orange (heating) |
| Savings | AreaChart | Cumulative savings over time | Emerald fill |
| Weather | ComposedChart | Temp + humidity + solar | Multi-axis |
| Carbon | LineChart | CO2 emissions over time | Green |
| Historical | LineChart | Selectable metrics | Theme colors |

### Panels

| Panel | Content | Update Frequency |
|---|---|---|
| AI Reasoning | Latest agent thoughts, confidence, tool calls | Per optimization cycle |
| Decision Timeline | Chronological list of actions taken | Per action |
| HVAC Status | Current mode, setpoints, fan, COP, runtime | Per simulation |
| Weather | Current outdoor conditions, forecast | Per cycle |
| Sensor Table | Sortable zone-by-zone data table | Per simulation |

---

## Animations (Framer Motion)

| Element | Animation | Duration |
|---|---|---|
| Page load | Staggered fade-in from bottom | 0.3s per card, 0.05s stagger |
| Metric update | Number counter animation | 0.5s ease-out |
| Card hover | Scale 1.01 + shadow increase | 0.2s |
| Chart data | Smooth line transition | 0.8s |
| Timeline entry | Slide in from right | 0.3s |
| AI reasoning | Typewriter text effect | Character by character |
| Status indicator | Pulse glow | 2s infinite |
| Tab switch | Crossfade | 0.2s |

---

## Responsive Breakpoints

| Breakpoint | Layout |
|---|---|
| Desktop (≥1280px) | Sidebar + 2-column main grid |
| Tablet (768-1279px) | Collapsed sidebar + 1-column |
| Mobile (<768px) | Bottom nav + stacked cards |

---

## Real-Time Updates

The dashboard uses **WebSocket** for real-time data:

```typescript
// hooks/useWebSocket.ts
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/live');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    switch (data.type) {
        case 'sensor_update': updateSensors(data.payload); break;
        case 'simulation_complete': updateMetrics(data.payload); break;
        case 'agent_reasoning': updateAIPanel(data.payload); break;
        case 'optimization_result': updateSavings(data.payload); break;
    }
};
```

Auto-refresh fallback: REST polling every 30 seconds if WebSocket disconnects.

---

## Technology Stack

| Technology | Purpose |
|---|---|
| **Next.js 14** | React framework with App Router |
| **TypeScript** | Type safety |
| **TailwindCSS** | Utility-first styling |
| **shadcn/ui** | Accessible component library (Card, Table, Tabs, Badge, Button) |
| **Recharts** | React charting (Line, Area, Bar, Radial, Composed) |
| **Framer Motion** | Animations and transitions |
| **Lucide React** | Icon library |
| **Google Fonts** | Inter (sans-serif) + JetBrains Mono (monospace) |
