import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import HeroSequence from './components/HeroSequence';
import OperationalDashboard from './components/OperationalDashboard';
import Layout from './components/Layout';
import TopologyView from './components/TopologyView';
import IncidentsView from './components/IncidentsView';
import WorkOrdersView from './components/WorkOrdersView';
import MetersView from './components/MetersView';
import RepairVerificationView from './components/RepairVerificationView';
import AuditTrailView from './components/AuditTrailView';
import SettingsView from './components/SettingsView';

// Wrapper to handle the transition from Hero to Dashboard
function HeroWrapper() {
  const navigate = useNavigate();
  return <HeroSequence key="hero" onInspect={() => navigate('/dashboard')} />;
}

// Wrapper for Dashboard back button logic
function DashboardWrapper() {
  const navigate = useNavigate();
  return <OperationalDashboard key="dashboard" onBack={() => navigate('/')} />;
}

function App() {
  return (
    <BrowserRouter>
      <div className="bg-[var(--color-pipesense-bg)] min-h-screen text-[var(--color-pipesense-text)] font-sans antialiased selection:bg-[var(--color-pipesense-cyan)] selection:text-black transition-colors duration-300">
        <Routes>
          {/* Landing Sequence */}
          <Route path="/" element={<HeroWrapper />} />
          
          {/* Main App Layout */}
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<DashboardWrapper />} />
            <Route path="/topology" element={<TopologyView />} />
            <Route path="/meters" element={<MetersView />} />
            <Route path="/incidents" element={<IncidentsView />} />
            <Route path="/work-orders" element={<WorkOrdersView />} />
            <Route path="/verify" element={<RepairVerificationView />} />
            <Route path="/audit" element={<AuditTrailView />} />
            <Route path="/settings" element={<SettingsView />} />
          </Route>
        </Routes>
      </div>
    </BrowserRouter>
  );
}


export default App;
