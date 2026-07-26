import { Suspense, lazy } from "react";
import { Routes, Route } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { LoadingScreen } from "@/components/LoadingScreen";

const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Investigation = lazy(() => import("@/pages/Investigation"));
const CustomerDetails = lazy(() => import("@/pages/CustomerDetails"));
const Analytics = lazy(() => import("@/pages/Analytics"));
const ModelInsights = lazy(() => import("@/pages/ModelInsights"));
const Settings = lazy(() => import("@/pages/Settings"));
const NotFound = lazy(() => import("@/pages/NotFound"));

export default function App() {
  return (
    <Suspense fallback={<LoadingScreen />}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="investigation" element={<Investigation />} />
          <Route path="customers" element={<CustomerDetails />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="models" element={<ModelInsights />} />
          <Route path="settings" element={<Settings />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
