import { Navigate, Route, Routes } from 'react-router-dom';
import { Navbar } from '@/components/Navbar';
import { useAuth } from '@/context/AuthContext';
import { useLanguage } from '@/context/LanguageContext';
import { AuthPage } from '@/pages/AuthPage';
import { BrokerDashboard } from '@/pages/BrokerDashboard';
import { CustomerPortal } from '@/pages/CustomerPortal';
import { Marketplace } from '@/pages/Marketplace';
import { PropertyDetail } from '@/pages/PropertyDetail';
import { ListingComposer } from '@/pages/ListingComposer';
import { AgencyDirectory } from '@/pages/AgencyDirectory';
import { BuyerTools } from '@/pages/BuyerTools';
import { PropertyCompare } from '@/pages/PropertyCompare';

function Protected({ children, broker = false }: { children: React.ReactNode; broker?: boolean }) {
  const { user, loading } = useAuth();
  if (loading) return <p className="page-shell py-12 text-[#678370]">Loading account…</p>;
  if (!user) return <Navigate to="/auth" replace />;
  if (broker && user.role === 'customer') return <Navigate to="/customer" replace />;
  return children;
}

export default function App() {
  const { t } = useLanguage();
  return <div className="min-h-dvh bg-[#fbfaf6]">
    <Navbar />
    <Routes>
      <Route path="/" element={<Marketplace />} />
      <Route path="/auth" element={<AuthPage />} />
      <Route path="/agencies" element={<AgencyDirectory />} />
      <Route path="/tools" element={<BuyerTools />} />
      <Route path="/compare" element={<PropertyCompare />} />
      <Route path="/property/:id" element={<PropertyDetail />} />
      <Route path="/broker" element={<Protected broker><BrokerDashboard /></Protected>} />
      <Route path="/broker/listings/new" element={<Protected broker><ListingComposer /></Protected>} />
      <Route path="/broker/listings/:id/edit" element={<Protected broker><ListingComposer /></Protected>} />
      <Route path="/customer" element={<Protected><CustomerPortal /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    <footer className="border-t border-line bg-[#f3f0e8] py-12 text-[#626d60]">
      <div className="page-shell flex flex-wrap items-center justify-between gap-5 text-xs"><span className="font-bold text-ink">dwelling. <span className="ms-3 font-normal text-muted">Property, with perspective.</span></span><span>© {new Date().getFullYear()} Dwelling · {t('marketplace')}</span></div>
    </footer>
  </div>;
}
