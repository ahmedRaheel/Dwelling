import { useEffect, useState, type FormEvent } from 'react';
import { Activity, ArrowRight, Building2, Camera, ChartNoAxesColumn,
  ChevronRight, CirclePlus, Eye, MessageCircle, Pencil, Sparkles, UsersRound, CalendarDays, Store } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '@/api/client';
import type { Agency, BrokerMatch, Lead, LeadStatus, Page, Property, Trend, Viewing } from '@/api/types';
import { PropertyImage } from '@/components/listings/PropertyImage';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';
import { useLanguage } from '@/context/LanguageContext';
import { currency, errorMessage } from '@/lib/utils';

type Tab = 'inventory' | 'enquiries' | 'matching' | 'market' | 'viewings' | 'agency';
const leadStatuses: LeadStatus[] = ['new', 'contacted', 'qualified', 'won', 'lost'];

export function BrokerDashboard() {
  const { user } = useAuth();
  const { t } = useLanguage();
  const [tab, setTab] = useState<Tab>('inventory');
  const [inventory, setInventory] = useState<Property[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [matches, setMatches] = useState<BrokerMatch[]>([]);
  const [trends, setTrends] = useState<Trend[]>([]);
  const [viewings, setViewings] = useState<Viewing[]>([]);
  const [agency, setAgency] = useState<Agency | null>(null);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    void Promise.all([
      api<Page<Property>>('/listings?mine=true&size=50'),
      api<Lead[]>('/leads'),
      api<BrokerMatch[]>('/ai/broker/matches'),
      api<Viewing[]>('/viewings/agency'),
      api<Agency>('/agencies/me'),
    ]).then(async ([properties, enquiries, potential, visits, agencyProfile]) => {
      if (!active) return;
      setInventory(properties.items); setLeads(enquiries); setMatches(potential); setViewings(visits); setAgency(agencyProfile); setError('');
      if (properties.items.length > 0) {
        const city = properties.items[0].city;
        const local = await api<Trend[]>(`/ai/trends?city=${encodeURIComponent(city)}`).catch(() => []);
        if (active) setTrends(local);
      }
    }).catch(cause => { if (active) setError(errorMessage(cause)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [refresh]);

  const reload = () => setRefresh(previous => previous + 1);
  async function updateLead(lead: Lead, status: LeadStatus) {
    try {
      await api(`/leads/${lead.id}`, { method: 'PATCH', body: JSON.stringify({ status, notes: lead.notes }) });
      reload();
    } catch (cause) { setError(errorMessage(cause)); }
  }
  async function archive(item: Property) {
    if (!window.confirm('Archive this ad? It will disappear from the public marketplace.')) return;
    try { await api(`/listings/${item.id}`, { method: 'DELETE' }); reload(); }
    catch (cause) { setError(errorMessage(cause)); }
  }

  async function updateViewing(viewing: Viewing, status: Viewing['status']) {
    try {
      await api(`/viewings/${viewing.id}`, { method: 'PATCH', body: JSON.stringify({ status }) });
      setNotice('Appointment status updated.'); reload();
    } catch (cause) { setError(errorMessage(cause)); }
  }

  async function saveAgency(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    try {
      const fields = ['public_description', 'public_city', 'public_phone', 'public_email'];
      const payload = Object.fromEntries(fields.map(field => [field, String(values.get(field) || '').trim() || null]));
      await api('/agencies/me', { method: 'PATCH', body: JSON.stringify({ ...payload,
        public_description: payload.public_description ?? '', public_city: payload.public_city ?? '',
      }) });
      setNotice('Public agency information updated.'); reload();
    } catch (cause) { setError(errorMessage(cause)); }
  }

  const navigation: { id: Tab; label: string; icon: typeof Building2 }[] = [
    { id: 'inventory', label: t('listings'), icon: Building2 },
    { id: 'enquiries', label: t('leads'), icon: UsersRound },
    { id: 'matching', label: t('leadMatches'), icon: Sparkles },
    { id: 'market', label: t('insights'), icon: Activity },
    { id: 'viewings', label: 'Viewings', icon: CalendarDays },
    ...(user?.role === 'owner' || user?.role === 'admin' ? [{ id: 'agency' as Tab, label: 'Agency profile', icon: Store }] : []),
  ];

  return <main className="page-shell pb-24 pt-10">
    <div className="flex flex-wrap items-end justify-between gap-5 border-b border-line pb-9">
      <div><p className="kicker">YOUR REAL ESTATE BUSINESS / WORKSPACE</p><h1 className="editorial-title mt-3 text-[clamp(2.1rem,5vw,4rem)]">Good morning, {user?.full_name.split(' ')[0]}.</h1>
        <p className="mt-3 text-sm text-muted">A clear view of your portfolio, active conversations and the next opportunity.</p></div>
      <Button asChild className="!rounded-md"><Link to="/broker/listings/new"><CirclePlus size={17}/>Create property ad</Link></Button>
    </div>

    <div className="my-8 grid gap-3 sm:grid-cols-3">
      {[{ title: 'Live properties', value: inventory.filter(item => item.status === 'published').length, icon: Building2, detail: 'Visible to buyers & renters' },
        { title: 'New enquiries', value: leads.filter(item => item.status === 'new').length, icon: MessageCircle, detail: 'Waiting for your response' },
        { title: 'Potential matches', value: matches.length, icon: ChartNoAxesColumn, detail: 'Based on inquiry preferences' }]
        .map(item => <div className="stat-tile" key={item.title}><div className="flex items-start justify-between"><span className="kicker">{item.title}</span><item.icon size={19} strokeWidth={1.4} className="text-accent"/></div><p className="mt-4 text-4xl font-semibold tabular-nums tracking-tight">{item.value}</p><p className="mt-2 text-xs text-muted">{item.detail}</p></div>)}
    </div>
    {error && <p role="alert" className="error-note mb-5">{error}</p>}
    {notice && <p role="status" className="success-note mb-5">{notice}</p>}
    <div className="mb-8 flex flex-wrap gap-2 border-b border-line" role="tablist" aria-label="Agency operations">
      {navigation.map(item => <button type="button" role="tab" aria-selected={tab === item.id} key={item.id}
        onClick={() => setTab(item.id)} className={`workspace-tab flex items-center gap-2 px-4 py-4 text-sm ${tab === item.id ? 'workspace-tab-active' : ''}`}><item.icon size={16}/>{item.label}</button>)}
    </div>

    {tab === 'inventory' && <section>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3"><div><p className="kicker">PROPERTY PORTFOLIO</p><h2 className="studio-heading mt-2">Your current advertisements</h2></div>
        <p className="text-sm tabular-nums text-muted">{inventory.length} listings</p></div>
      {loading ? <div className="studio-panel p-12 text-muted">Loading inventory…</div> : inventory.length === 0 ?
        <div className="empty-space"><Building2 size={36} strokeWidth={1}/><h3 className="mt-4 text-xl font-medium">Your first listing starts here.</h3>
          <p className="mt-2 max-w-sm text-sm text-muted">Add the address, details and real photographs. We will help you publish a polished ad.</p>
          <Link to="/broker/listings/new" className="mt-6 inline-flex items-center gap-2 font-semibold text-accent">Create an ad <ArrowRight size={17}/></Link></div> :
        <div className="studio-panel overflow-hidden"><div className="divide-y divide-line">{inventory.map(item =>
          <article key={item.id} className="flex flex-wrap items-center gap-5 p-4 sm:flex-nowrap sm:p-5">
            <Link to={`/property/${item.id}`} className="block h-24 w-32 shrink-0 overflow-hidden rounded bg-sand"><PropertyImage property={item} className="h-full w-full"/></Link>
            <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><span className={`status-chip status-${item.status}`}>{item.status}</span>
              <span className="text-xs text-muted">DW-{item.id.slice(0, 8).toUpperCase()}</span></div>
              <h3 className="mt-2 line-clamp-1 text-base font-semibold">{item.title}</h3><p className="mt-1 text-xs text-muted">{item.area_name}, {item.city} · {currency(item.price)}</p>
              <p className="mt-2 flex items-center gap-1 text-xs text-muted"><Camera size={13}/>{item.photos.length} photo{item.photos.length === 1 ? '' : 's'}</p>
            </div><div className="ms-auto flex flex-wrap items-center gap-2">
              <Link className="mini-action" to={`/broker/listings/${item.id}/edit`}><Pencil size={14}/>Edit</Link>
              <Link className="mini-action" to={`/broker/listings/${item.id}/edit?step=photos`}><Camera size={14}/>Photos</Link>
              <Link className="mini-action" to={`/property/${item.id}`} aria-label="Preview advertisement"><Eye size={16}/></Link>
              {item.status !== 'archived' && <button type="button" className="mini-action text-[#9d5043]" onClick={() => void archive(item)}>Archive</button>}
            </div>
          </article>)}</div></div>}
    </section>}

    {tab === 'enquiries' && <section className="studio-panel overflow-hidden"><div className="p-6"><p className="kicker">CUSTOMER RELATIONSHIPS</p><h2 className="studio-heading mt-2">Enquiries & follow-ups</h2></div>
      {leads.length === 0 ? <div className="p-8 text-sm text-muted">No inquiries yet. Your messages will appear here as customers contact you.</div> :
        <div className="divide-y divide-line">{leads.map(lead => <div key={lead.id} className="grid gap-4 p-5 md:grid-cols-[1fr_1.3fr_auto] md:items-center">
          <div><p className="font-semibold">{lead.contact_name}</p><a href={`mailto:${lead.contact_email}`} className="link-text mt-1 block text-sm">{lead.contact_email}</a>{lead.contact_phone && <p className="mt-1 text-xs tabular-nums text-muted">{lead.contact_phone}</p>}</div>
          <div><p className="text-sm text-muted">{lead.message || 'Property inquiry'}</p><span className="mt-2 block text-xs text-muted">{new Date(lead.created_at).toLocaleString()}</span></div>
          <label className="text-xs text-muted">Stage<select className="field mt-1" aria-label="Lead stage" value={lead.status} onChange={event => void updateLead(lead, event.target.value as LeadStatus)}>{leadStatuses.map(status => <option key={status} value={status}>{status}</option>)}</select></label>
        </div>)}</div>}
    </section>}

    {tab === 'viewings' && <section className="studio-panel overflow-hidden">
      <div className="p-6"><p className="kicker">APPOINTMENTS DESK</p><h2 className="studio-heading mt-2">Viewing requests</h2><p className="mt-2 text-xs text-muted">A customer-selected time is not confirmed until your agency accepts it.</p></div>
      {viewings.length === 0 ? <div className="p-8 text-sm text-muted">No viewing requests yet.</div> : <div className="divide-y divide-line">{viewings.map(visit => <article className="grid gap-4 p-5 md:grid-cols-[1.1fr_1fr_auto] md:items-center" key={visit.id}>
        <div><Link className="font-semibold hover:text-accent" to={`/property/${visit.property_id}`}>View property</Link><p className="mt-1 text-sm">{visit.contact_name}</p><a href={`tel:${visit.contact_phone}`} className="mt-1 block text-xs text-muted">{visit.contact_phone}</a></div>
        <div><p className="text-sm font-medium">{new Date(visit.preferred_at).toLocaleString()}</p><p className="mt-1 text-xs text-muted">{visit.note || 'No additional notes'}</p><span className="status-chip status-draft mt-2">{visit.status}</span></div>
        <div className="flex flex-wrap gap-2">{visit.status === 'requested' && <><button className="mini-action" onClick={() => void updateViewing(visit, 'confirmed')}>Confirm</button><button className="mini-action" onClick={() => void updateViewing(visit, 'declined')}>Decline</button></>}
          {visit.status === 'confirmed' && <button className="mini-action" onClick={() => void updateViewing(visit, 'completed')}>Completed</button>}</div>
      </article>)}</div>}
    </section>}

    {tab === 'agency' && agency && <section className="studio-panel p-7 sm:p-9">
      <p className="kicker">YOUR PUBLIC PRESENCE</p><h2 className="studio-heading mt-2">Agency profile</h2><p className="mt-3 max-w-xl text-sm leading-6 text-muted">Make it easy for clients to identify your agency. Enter only contact information you want shown publicly.</p>
      <form onSubmit={event => void saveAgency(event)} key={agency.id} className="mt-8 grid max-w-2xl gap-5 sm:grid-cols-2">
        <label className="form-label sm:col-span-2">Agency description<textarea name="public_description" maxLength={2000} className="field mt-2 min-h-32" defaultValue={agency.public_description}/></label>
        <label className="form-label">Primary city<input className="field mt-2" name="public_city" defaultValue={agency.public_city}/></label>
        <label className="form-label">Public phone<input className="field mt-2" name="public_phone" defaultValue={agency.public_phone || ''}/></label>
        <label className="form-label sm:col-span-2">Public email<input className="field mt-2" name="public_email" type="email" defaultValue={agency.public_email || ''}/></label>
        <div className="sm:col-span-2"><Button type="submit">Save agency profile</Button></div>
      </form>
      <p className="mt-6 text-xs text-muted">These details are self-published by the agency; no independent accreditation is implied.</p>
    </section>}

    {tab === 'matching' && <section><p className="kicker">EXPLAINABLE RECOMMENDATIONS</p><h2 className="studio-heading mb-5 mt-2">Potential buyers & renters</h2>
      {matches.length === 0 ? <div className="empty-space"><Sparkles size={33} strokeWidth={1}/><p className="mt-4 text-sm text-muted">Matches appear when published properties align with incoming enquiries.</p></div> :
        <div className="grid gap-4 md:grid-cols-2">{matches.map((match, index) => <article key={`${match.lead.id}:${match.property.id}:${index}`} className="studio-panel p-6">
          <p className="kicker">{Math.round(match.score * 100)}% HEURISTIC MATCH</p><h3 className="mt-3 text-lg font-semibold">{match.lead.contact_name}</h3>
          <p className="mt-1 text-sm text-muted">May be interested in {match.property.title}</p><p className="mt-4 text-xs text-muted">{match.reasons.join(' · ')}</p>
          <Link to={`/property/${match.property.id}`} className="link-text mt-5 inline-flex items-center gap-1 text-sm">View property <ChevronRight size={15}/></Link>
        </article>)}</div>}
    </section>}

    {tab === 'market' && <section className="studio-panel p-6 sm:p-9"><p className="kicker">VERIFIED MARKET DATA</p><h2 className="studio-heading mb-2 mt-2">Local benchmarks</h2>
      <p className="mb-6 max-w-xl text-sm text-muted">Only verified third-party or administrator-imported monthly benchmarks are shown. No fabricated returns or valuations.</p>
      {trends.length === 0 ? <p className="border-t border-line py-8 text-sm text-muted">No verified trend data has been imported for your area.</p> :
        <div className="overflow-x-auto"><table className="w-full text-start text-sm"><thead><tr className="border-b border-line text-xs text-muted"><th className="p-3 text-start">Month</th><th className="p-3 text-start">Area</th><th className="p-3 text-start">Type</th><th className="p-3 text-start">Sale benchmark</th><th className="p-3 text-start">Rental benchmark</th></tr></thead><tbody>{trends.map(row => <tr key={`${row.month}:${row.area_name}:${row.kind}`} className="border-b border-line"><td className="p-3 tabular-nums">{row.month.slice(0, 7)}</td><td className="p-3">{row.area_name || row.city}</td><td className="p-3 capitalize">{row.kind.replaceAll('_', ' ')}</td><td className="p-3 tabular-nums">{row.median_sale_price ? currency(row.median_sale_price) : '—'}</td><td className="p-3 tabular-nums">{row.median_monthly_rent ? currency(row.median_monthly_rent) : '—'}</td></tr>)}</tbody></table></div>}
    </section>}
  </main>;
}
