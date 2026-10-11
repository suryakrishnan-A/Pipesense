import { Outlet, Link, useLocation } from 'react-router-dom';
import { 
  Activity, 
  GitBranch, 
  Thermometer, 
  AlertTriangle, 
  UserCircle,
  Briefcase,
  CheckSquare,
  Settings,
  FileText,
  Moon,
  Sun
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { fetchAgentStatus, type AgentStatus } from '../lib/api';

const NAV_ITEMS = [
  { path: '/dashboard', label: 'Overview', icon: Activity },
  { path: '/topology', label: 'Pipeline Topology', icon: GitBranch },
  { path: '/meters', label: 'Meter Inventory', icon: Thermometer },
  { path: '/incidents', label: 'Incidents & Evidence', icon: AlertTriangle },
  { path: '/work-orders', label: 'Work Orders', icon: Briefcase },
  { path: '/verify', label: 'Repair Verification', icon: CheckSquare },
  { path: '/audit', label: 'Audit Trail', icon: FileText },
  { path: '/settings', label: 'Admin & Thresholds', icon: Settings },
];

export default function Layout() {
  const location = useLocation();
  const [isDark, setIsDark] = useState(
    document.documentElement.classList.contains('dark')
  );
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);

  useEffect(() => {
    fetchAgentStatus()
      .then(setAgentStatus)
      .catch(() => {
        setAgentStatus({
          mode: 'local_demo',
          provider: 'Local Deterministic Rules',
          bedrock_enabled: false,
          status_text: 'Local Demo Mode',
          description: 'Running with local deterministic rules.'
        });
      });
  }, []);

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);


  return (
    <div className="flex h-screen w-full bg-[var(--color-pipesense-bg)] text-[var(--color-pipesense-text)] overflow-hidden">
      {/* Sidebar Navigation */}
      <aside className="w-64 border-r border-[var(--color-pipesense-border)] bg-[var(--color-pipesense-panel)] flex flex-col transition-colors">
        <div className="h-16 flex items-center px-6 border-b border-[var(--color-pipesense-border)]">
          <Activity className="w-6 h-6 text-[var(--color-pipesense-cyan)] mr-3" />
          <span className="font-hud font-bold text-xl tracking-wider">PIPESENSE</span>
        </div>
        
        <nav className="flex-1 overflow-y-auto py-6 px-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  isActive 
                    ? 'bg-[var(--color-pipesense-cyan)]/10 text-[var(--color-pipesense-cyan)] font-medium' 
                    : 'text-[var(--color-pipesense-muted)] hover:bg-[var(--color-pipesense-secondary)] hover:text-[var(--color-pipesense-text)]'
                }`}
              >
                <Icon className={`w-5 h-5 mr-3 ${isActive ? 'text-[var(--color-pipesense-cyan)]' : ''}`} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-[var(--color-pipesense-border)] space-y-2">
          <button 
            onClick={() => setIsDark(!isDark)}
            className="w-full flex items-center px-3 py-2 rounded-lg text-sm text-[var(--color-pipesense-muted)] hover:bg-[var(--color-pipesense-secondary)] hover:text-[var(--color-pipesense-text)] transition-colors"
          >
            {isDark ? <Sun className="w-5 h-5 mr-3" /> : <Moon className="w-5 h-5 mr-3" />}
            {isDark ? 'Light Mode' : 'Dark Mode'}
          </button>
          <button className="w-full flex items-center px-3 py-2 rounded-lg text-sm text-[var(--color-pipesense-muted)] hover:bg-[var(--color-pipesense-secondary)] hover:text-[var(--color-pipesense-text)] transition-colors">
            <UserCircle className="w-5 h-5 mr-3" />
            Profile & Prefs
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Top Header */}
        <header className="h-16 border-b border-[var(--color-pipesense-border)] bg-[var(--color-pipesense-panel)] flex items-center justify-between px-8">
          <div className="flex items-center space-x-4 text-sm">
            <span className="text-[var(--color-pipesense-muted)]">Organization:</span>
            <span className="font-medium">Apex Manufacturing</span>
            <span className="text-[var(--color-pipesense-border)] mx-2">/</span>
            <span className="text-[var(--color-pipesense-muted)]">Site:</span>
            <span className="font-medium text-[var(--color-pipesense-cyan)] cursor-pointer hover:underline">North Campus</span>
          </div>
          <div className="flex items-center space-x-4">
            <Link
              to="/settings"
              title={agentStatus?.description || 'Agent configuration'}
              className="flex items-center space-x-2 text-xs px-2.5 py-1 rounded-full border border-[var(--color-pipesense-border)] bg-[var(--color-pipesense-secondary)] hover:border-[var(--color-pipesense-cyan)] transition-colors"
            >
              <span className={`w-2 h-2 rounded-full ${
                agentStatus?.status_key === 'bedrock_active' || agentStatus?.bedrock_enabled ? 'bg-emerald-400 animate-pulse' :
                agentStatus?.status_key === 'bedrock_configured_unverified' ? 'bg-amber-400' :
                agentStatus?.status_key === 'bedrock_unavailable' ? 'bg-rose-400' :
                'bg-cyan-400'
              }`}></span>
              <span className="font-medium text-[var(--color-pipesense-text)]">
                {agentStatus?.status_text || 'Local Demo Mode'}
              </span>
            </Link>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-auto custom-scrollbar p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
