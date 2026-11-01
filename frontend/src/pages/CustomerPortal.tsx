import { useEffect, useState, type FormEvent } from 'react';
import { ArrowRight, Heart, MessageSquare, SlidersHorizontal, Sparkles, Trash2, Bookmark, CalendarDays, ArrowUpRight } from 'lucide-react';
import { api } from '@/api/client';
import { Link } from 'react-router-dom';
import type { CustomerInquiry, Property, PropertyKind, Purpose, Recommendation, SavedSearch, SavedSearchMatches, Viewing } from '@/api/types';
import { PropertyCard } from '@/components/PropertyCard';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/context/AuthContext';
import { useLanguage } from '@/context/LanguageContext';
import { errorMessage } from '@/lib/utils';

type Tab = 'recommended' | 'saved' | 'inquiries' | 'searches' | 'viewings';
const propertyTypes: PropertyKind[] = ['house', 'apartment', 'portion', 'plot', 'pg', 'commercial_building'];

export function CustomerPortal() {
  const { user, reload } = useAuth();
  const { t } = useLanguage();
  const [tab, setTab] = useState<Tab>('recommended');
  const [matches, setMatches] = useState<Recommendation[]>([]);
  const [saved, setSaved] = useState<Property[]>([]);
  const [inquiries, setInquiries] = useState<CustomerInquiry[]>([]);
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [viewings, setViewings] = useState<Viewing[]>([]);
  const [searchMatches, setSearchMatches] = useState<SavedSearchMatches | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let active = true;
    void Promise.all([
      api<Recommendation[]>('/ai/recommendations'),
      api<Property[]>('/listings/saved'),
      api<CustomerInquiry[]>('/leads/mine'),
      api<SavedSearch[]>('/discovery/saved-searches'),
      api<Viewing[]>('/viewings/mine'),
    ]).then(([recommended, bookmarks, conversations, savedSearches, appointments]) => {
      if (active) { setMatches(recommended); setSaved(bookmarks); setInquiries(conversations); setSearches(savedSearches); setViewings(appointments); }
    }).catch(cause => { if (active) setError(errorMessage(cause)); });
    return () => { active = false; };
  }, [refresh]);

  async function savePreferences(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(''); setNotice('');
    const form = new FormData(event.currentTarget);
    const preferences: Record<string, string | number> = {};
    for (const key of ['city', 'kind', 'purpose']) {
      const value = String(form.get(key) ?? '').trim();
      if (value) preferences[key] = value;
    }
    const maximum = Number(form.get('max_price'));
    const bedrooms = Number(form.get('minimum_bedrooms'));
    if (maximum > 0) preferences.max_price = maximum;
    if (bedrooms > 0) preferences.minimum_bedrooms = bedrooms;
    try {
      await api('/auth/me/preferences', { method: 'PATCH', body: JSON.stringify(preferences) });
      await reload(); setRefresh(value => value + 1);
      setNotice('Your search preferences have been updated.');
    } catch (cause) { setError(errorMessage(cause)); }
  }

  async function removeBookmark(id: string) {
    try {
      await api(`/listings/saved/${id}`, { method: 'DELETE' });
      setSaved(previous => previous.filter(property => property.id !== id));
    } catch (cause) { setError(errorMessage(cause)); }
  }

  async function showSearchMatches(search: SavedSearch) {
    try {
      setError('');
      const results = await api<SavedSearchMatches>(`/discovery/saved-searches/${search.id}/matches`);
      setSearchMatches(results);
      await api(`/discovery/saved-searches/${search.id}/check`, { method: 'POST' });
      setRefresh(value => value + 1);
    } catch (cause) { setError(errorMessage(cause)); }
  }
  async function deleteSearch(searchId: string) {
    try {
      await api(`/discovery/saved-searches/${searchId}`, { method: 'DELETE' });
      setSearches(previous => previous.filter(item => item.id !== searchId));
      if (searchMatches?.search.id === searchId) setSearchMatches(null);
    } catch (cause) { setError(errorMessage(cause)); }
  }
  async function cancelViewing(id: string) {
    try {
      await api(`/viewings/${id}`, { method: 'PATCH', body: JSON.stringify({ status: 'cancelled' }) });
      setRefresh(value => value + 1);
    } catch (cause) { setError(errorMessage(cause)); }
  }

  return <main className="page-shell pb-24 pt-12">
    <p className="kicker">YOUR PERSONAL PROPERTY DESK</p>
    <h1 className="editorial-title mt-3 text-[clamp(2.2rem,5vw,4rem)]">Welcome back, {user?.full_name.split(' ')[0]}.</h1>
    <p className="mt-3 text-sm text-muted">A considered shortlist, built around what matters to you.</p>
    {error && <p role="alert" className="error-note mt-6">{error}</p>}
    {notice && <p role="status" className="success-note mt-6">{notice}</p>}
    <div className="mt-9 grid gap-9 lg:grid-cols-[290px_minmax(0,1fr)] xl:gap-14">
      <aside className="studio-panel self-start p-6 lg:sticky lg:top-28">
        <div className="flex items-center gap-2"><SlidersHorizontal size={18} className="text-accent"/><h2 className="text-base font-semibold">Your preferences</h2></div>
        <p className="mt-2 text-xs leading-5 text-muted">Tell us what you're looking for. Recommendations update as listings become available.</p>
        <form onSubmit={event => void savePreferences(event)} className="mt-6 space-y-4">
          <label className="form-label">Preferred city<Input name="city" className="mt-2" placeholder="Karachi" defaultValue={user?.preferences.city ?? ''}/></label>
          <label className="form-label">Property type<select className="field mt-2" name="kind" defaultValue={user?.preferences.kind ?? ''}><option value="">Any property</option>{propertyTypes.map(kind => <option key={kind} value={kind}>{kind.replaceAll('_', ' ')}</option>)}</select></label>
          <label className="form-label">Looking to<select className="field mt-2" name="purpose" defaultValue={user?.preferences.purpose ?? ''}><option value="">Buy or rent</option>{(['sale', 'rent'] satisfies Purpose[]).map(purpose => <option value={purpose} key={purpose}>{purpose === 'sale' ? 'Buy' : 'Rent'}</option>)}</select></label>
          <label className="form-label">Max budget (PKR)<Input name="max_price" className="mt-2" type="number" min={1} defaultValue={user?.preferences.max_price ?? ''}/></label>
          <label className="form-label">Minimum bedrooms<Input name="minimum_bedrooms" className="mt-2" type="number" min={0} max={30} defaultValue={user?.preferences.minimum_bedrooms ?? ''}/></label>
          <Button type="submit" className="mt-2 w-full">Update preferences <ArrowRight size={15}/></Button>
        </form>
      </aside>
      <section className="min-w-0">
        <div className="flex flex-wrap gap-6 border-b border-line">
          <button type="button" className={`workspace-tab flex items-center gap-2 pb-4 text-sm ${tab === 'recommended' ? 'workspace-tab-active' : ''}`} onClick={() => setTab('recommended')}><Sparkles size={16}/>{t('recommendations')}</button>
          <button type="button" className={`workspace-tab flex items-center gap-2 pb-4 text-sm ${tab === 'saved' ? 'workspace-tab-active' : ''}`} onClick={() => setTab('saved')}><Heart size={16}/>Saved ({saved.length})</button>
          <button type="button" className={`workspace-tab flex items-center gap-2 pb-4 text-sm ${tab === 'searches' ? 'workspace-tab-active' : ''}`} onClick={() => setTab('searches')}><Bookmark size={16}/>Saved searches ({searches.length})</button>
          <button type="button" className={`workspace-tab flex items-center gap-2 pb-4 text-sm ${tab === 'viewings' ? 'workspace-tab-active' : ''}`} onClick={() => setTab('viewings')}><CalendarDays size={16}/>Appointments ({viewings.length})</button>
          <button type="button" className={`workspace-tab flex items-center gap-2 pb-4 text-sm ${tab === 'inquiries' ? 'workspace-tab-active' : ''}`} onClick={() => setTab('inquiries')}><MessageSquare size={16}/>My enquiries ({inquiries.length})</button>
        </div>
        {tab === 'recommended' && <div className="pt-7"><p className="kicker mb-5">MATCHED TO YOUR SEARCH</p>{matches.length > 0 ?
          <div className="grid gap-x-6 gap-y-10 sm:grid-cols-2">{matches.map(item => <PropertyCard key={item.property.id} property={item.property} reason={item.reasons.slice(0, 2).join(' · ')}/>)}</div> :
          <div className="empty-space"><Sparkles size={30}/><p className="mt-4 text-sm text-muted">Recommendations will appear once published listings match your preferences.</p></div>}</div>}
        {tab === 'saved' && <div className="pt-7"><p className="kicker mb-5">YOUR SHORTLIST</p>{saved.length > 0 ?
          <div className="grid gap-9 sm:grid-cols-2">{saved.map(property => <div key={property.id}><PropertyCard property={property}/>
            <button type="button" onClick={() => void removeBookmark(property.id)} className="mt-3 inline-flex items-center gap-1 text-xs text-muted hover:text-[#a34e3d]"><Trash2 size={13}/>Remove from shortlist</button></div>)}</div> :
          <div className="empty-space"><Heart size={30}/><p className="mt-4 text-sm text-muted">Save a property from its listing to build your shortlist.</p></div>}</div>}
        {tab === 'searches' && <div className="pt-7"><p className="kicker mb-5">YOUR WATCHLISTS</p>
          {searches.length === 0 ? <div className="empty-space">Save search criteria from the marketplace to monitor new matching listings.</div> :
            <div className="studio-panel divide-y divide-line">{searches.map(item => <article key={item.id} className="flex flex-wrap items-center justify-between gap-4 p-5">
              <div><h3 className="font-semibold">{item.name}</h3><p className="mt-2 text-xs text-muted">{Object.entries(item.filters).map(([key, value]) => `${key.replaceAll('_',' ')}: ${value}`).join(' · ') || 'All properties'}</p></div>
              <div className="flex gap-2"><button className="mini-action" onClick={() => void showSearchMatches(item)}>See matches <ArrowUpRight size={14}/></button><button className="mini-action" onClick={() => void deleteSearch(item.id)} aria-label={`Delete ${item.name}`}><Trash2 size={14}/></button></div>
            </article>)}</div>}
          {searchMatches && <section className="mt-8"><p className="kicker">{searchMatches.search.name.toUpperCase()} / {searchMatches.new_count} NEW SINCE YOUR LAST CHECK</p>
            <p className="mt-3 text-xs text-muted">In-app matching only. Email notifications are not configured.</p>
            <div className="mt-5 grid gap-6 sm:grid-cols-2">{searchMatches.items.map(property => <PropertyCard key={property.id} property={property}/>)}</div></section>}
        </div>}
        {tab === 'viewings' && <div className="pt-7"><p className="kicker mb-5">YOUR APPOINTMENT REQUESTS</p>
          {viewings.length === 0 ? <div className="empty-space">Request a viewing from a property page to see it here.</div> :
            <div className="studio-panel divide-y divide-line">{viewings.map(visit => <article key={visit.id} className="flex flex-wrap items-center justify-between gap-4 p-5">
              <div><Link to={`/property/${visit.property_id}`} className="font-semibold text-accent">View property</Link><p className="mt-2 text-sm">{new Date(visit.preferred_at).toLocaleString()}</p><span className="status-chip status-draft mt-2">{visit.status}</span><p className="mt-2 text-xs text-muted">{visit.status === 'requested' ? 'Awaiting agency confirmation' : visit.note}</p></div>
              {['requested','confirmed'].includes(visit.status) && <button className="mini-action" onClick={() => void cancelViewing(visit.id)}>Cancel request</button>}
            </article>)}</div>}
        </div>}
        {tab === 'inquiries' && <div className="pt-7"><p className="kicker mb-5">YOUR CONVERSATIONS</p>{inquiries.length > 0 ?
          <div className="studio-panel divide-y divide-line">{inquiries.map(lead => <div key={lead.id} className="p-6"><div className="flex items-center justify-between gap-3"><span className="status-chip status-draft">{lead.status}</span><span className="text-xs text-muted">{new Date(lead.created_at).toLocaleDateString()}</span></div>
            <p className="mt-3 text-sm text-ink">{lead.message || 'Viewing enquiry'}</p></div>)}</div> :
          <div className="empty-space"><MessageSquare size={30}/><p className="mt-4 text-sm text-muted">Your enquiries to listing agencies will appear here.</p></div>}</div>}
      </section>
    </div>
  </main>;
}
