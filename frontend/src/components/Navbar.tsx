import { ArrowUpRight, Building2, LayoutGrid, LogOut, Menu, Plus, Search, ArrowLeftRight, Calculator } from 'lucide-react';
import { Link, NavLink } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { useLanguage } from '@/context/LanguageContext';
import { Button } from './ui/button';
import { LanguageToggle } from './LanguageToggle';

export function Navbar() {
  const { user, logout } = useAuth();
  const { t } = useLanguage();
  const professional = user?.role === 'owner' || user?.role === 'admin' || user?.role === 'broker';
  return <header className="top-nav sticky top-0 z-40 border-b border-line bg-[#fbfaf6]/95 backdrop-blur-md">
    <div className="page-shell flex min-h-[78px] items-center justify-between gap-4">
      <Link to="/" aria-label="Dwelling home" className="brand-mark shrink-0"><span className="brand-icon"><Building2 size={19} strokeWidth={1.8}/></span>
        <span>dwelling<span className="text-accent">.</span></span></Link>
      <nav aria-label="Main navigation" className="hidden items-center gap-8 text-[13px] font-semibold text-[#505b50] md:flex">
        <NavLink to="/" end className={({ isActive }) => isActive ? 'nav-active' : 'hover:text-ink'}><Search size={14} className="me-2 inline"/>{t('marketplace')}</NavLink>
        <NavLink to="/agencies" className={({ isActive }) => isActive ? 'nav-active' : 'hover:text-ink'}>Agencies</NavLink>
        <NavLink to="/tools" className={({ isActive }) => isActive ? 'nav-active' : 'hover:text-ink'}><Calculator size={14} className="me-2 inline"/>Tools</NavLink>
        <NavLink to="/compare" className={({ isActive }) => isActive ? 'nav-active' : 'hover:text-ink'}><ArrowLeftRight size={14} className="me-2 inline"/>Compare</NavLink>
        {user && <NavLink to={professional ? '/broker' : '/customer'} className={({ isActive }) => isActive ? 'nav-active' : 'hover:text-ink'}><LayoutGrid size={14} className="me-2 inline"/>{professional ? 'My workspace' : 'My search'}</NavLink>}
      </nav>
      <div className="flex items-center gap-3"><LanguageToggle/>
        {professional && <Link className="hidden items-center gap-1 text-xs font-semibold text-accent lg:inline-flex" to="/broker/listings/new"><Plus size={16}/>Post property</Link>}
        {user ? <><span className="hidden max-w-32 truncate text-xs text-muted sm:block">{user.full_name}</span>
          <Button type="button" variant="outline" size="sm" onClick={() => void logout()}><LogOut size={15}/><span className="hidden sm:inline">{t('signOut')}</span></Button>
          <Link to={professional ? '/broker' : '/customer'} className="md:hidden" aria-label="Open dashboard"><Menu size={20}/></Link></> :
          <Link to="/auth" className="inline-flex items-center gap-1.5 rounded-sm border border-ink px-4 py-2 text-xs font-semibold transition-colors hover:bg-ink hover:text-white">{t('signIn')} <ArrowUpRight size={14}/></Link>}
      </div>
    </div>
    <nav aria-label="Mobile navigation" className="flex gap-5 overflow-x-auto border-t border-line px-5 py-3 text-xs font-semibold text-[#505b50] md:hidden">
      <Link className="shrink-0" to="/">Properties</Link>
      <Link className="shrink-0" to="/agencies">Agencies</Link>
      <Link className="shrink-0" to="/tools">Buyer tools</Link>
      <Link className="shrink-0" to="/compare">Compare</Link>
      {user && <Link className="shrink-0" to={professional ? '/broker' : '/customer'}>My workspace</Link>}
    </nav>
  </header>;
}
