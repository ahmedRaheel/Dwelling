import { useEffect, useState, type FormEvent } from 'react';
import { ArrowDown, ArrowRight, ArrowUpRight, Building2, ChevronLeft, ChevronRight, MapPin, Search, SlidersHorizontal, X, BookmarkPlus } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '@/api/client';
import type { Page, Property, PropertyKind, Purpose } from '@/api/types';
import { PropertyImage } from '@/components/listings/PropertyImage';
import { PropertyCard } from '@/components/PropertyCard';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';
import { useLanguage } from '@/context/LanguageContext';
import { currency, errorMessage } from '@/lib/utils';

type Filters = {
  q: string; city: string; society: string; block: string; kind: '' | PropertyKind; purpose: '' | Purpose;
  min_price: string; max_price: string; minimum_bedrooms: string; minimum_bathrooms: string; min_area: string; max_area: string;
  sort: 'newest' | 'price_asc' | 'price_desc' | 'area_desc';
};
const defaults: Filters = { q: '', city: '', society: '', block: '', kind: '', purpose: '', min_price: '', max_price: '', minimum_bedrooms: '', minimum_bathrooms: '', min_area: '', max_area: '', sort: 'newest' };
const kinds: { id: PropertyKind | ''; title: string }[] = [
  { id: '', title: 'Everything' }, { id: 'house', title: 'Houses' }, { id: 'apartment', title: 'Apartments' },
  { id: 'portion', title: 'Portions' }, { id: 'plot', title: 'Plots' },
  { id: 'pg', title: 'Shared / PG' }, { id: 'commercial_building', title: 'Commercial' },
];

export function Marketplace() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const agencySlug = searchParams.get('agency');
  const { language } = useLanguage();
  const [draft, setDraft] = useState<Filters>(defaults);
  const [filters, setFilters] = useState<Filters>(defaults);
  const [page, setPage] = useState(1);
  const [results, setResults] = useState<Page<Property> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [advanced, setAdvanced] = useState(false);
  const [savingSearch, setSavingSearch] = useState(false);
  const [searchName, setSearchName] = useState('');
  const [searchNotice, setSearchNotice] = useState('');
  const [locationHints, setLocationHints] = useState<string[]>([]);

  useEffect(() => {
    const term = draft.society.trim();
    if (term.length < 2) { setLocationHints([]); return; }
    let active = true;
    const debounce = window.setTimeout(() => {
      void api<string[]>(`/discovery/locations?q=${encodeURIComponent(term)}${draft.city.trim() ? `&city=${encodeURIComponent(draft.city.trim())}` : ''}`)
        .then(items => { if (active) setLocationHints(items); }).catch(() => {});
    }, 250);
    return () => { active = false; window.clearTimeout(debounce); };
  }, [draft.society, draft.city]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    const params = new URLSearchParams({ page: String(page), size: '12' });
    if (agencySlug) params.set('agency_slug', agencySlug);
    for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value);
    void api<Page<Property>>(`/listings?${params}`).then(data => {
      if (active) { setResults(data); setError(''); }
    }).catch(cause => { if (active) setError(errorMessage(cause)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [filters, page, agencySlug]);

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setPage(1); setFilters({ ...draft });
    document.getElementById('property-results')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  function selectType(kind: Filters['kind']) {
    setDraft(previous => ({ ...previous, kind }));
    setFilters(previous => ({ ...previous, kind })); setPage(1);
  }
  function reset() { setDraft(defaults); setFilters(defaults); setPage(1); }

  async function saveSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSearchNotice('');
    try {
      const { sort: _sort, ...searchFilters } = filters;
      void _sort;
      const cleaned = Object.fromEntries(Object.entries(searchFilters).filter(([, value]) => value !== ''));
      await api('/discovery/saved-searches', { method: 'POST', body: JSON.stringify({
        name: searchName.trim(), filters: cleaned, alerts_enabled: true,
      }) });
      setSavingSearch(false); setSearchName('');
      setSearchNotice('Search saved. New-match counts are available in your customer workspace.');
    } catch (cause) { setSearchNotice(errorMessage(cause)); }
  }

  const lead = results?.items.find(item => item.photos.length > 0) ?? results?.items[0];
  const professional = user?.role === 'owner' || user?.role === 'broker' || user?.role === 'admin';
  const activeFilters = Object.entries(filters).filter(([key, value]) => key !== 'sort' && Boolean(value)).length;

  return <main>
    <section className="hero-section">
      <div className="page-shell grid gap-12 pb-12 pt-14 lg:grid-cols-[1.06fr_.94fr] lg:items-center lg:gap-14 lg:pb-18 lg:pt-18">
        <div className="max-w-2xl">
          <p className="kicker mb-7 flex items-center gap-3"><span className="inline-block h-px w-7 bg-accent"/>PROPERTY DISCOVERY, CONSIDERED</p>
          <h1 className="hero-title">A place to <em>belong.</em><br/>A space to <em>grow.</em></h1>
          <p className="mt-7 max-w-[480px] text-base leading-8 text-[#646b60]">{language === 'ur' ? 'گھر، اپارٹمنٹ، پورشن، پلاٹ اور کاروباری جگہیں — ایک بہتر انتخاب کے لیے واضح معلومات اور حقیقی تصاویر۔' : 'Homes, apartments, portions and commercial spaces. Thoughtfully presented, clearly priced, and easier to compare.'}</p>
          <div className="mt-9 flex flex-wrap items-center gap-5">
            <a href="#property-results" className="inline-flex items-center gap-2 border-b border-ink pb-2 text-sm font-semibold text-ink">Explore current listings <ArrowDown size={16}/></a>
            {professional && <Link to="/broker/listings/new" className="inline-flex items-center gap-1 text-sm font-semibold text-accent">Advertise your property <ArrowUpRight size={16}/></Link>}
          </div>
          <div className="mt-14 hidden gap-10 border-t border-line pt-7 sm:flex"><div><strong className="block text-xl font-semibold">6</strong><span className="text-xs text-muted">Property categories</span></div><div><strong className="block text-xl font-semibold">EN / اردو</strong><span className="text-xs text-muted">Language choice</span></div><div><strong className="block text-xl font-semibold">AI</strong><span className="text-xs text-muted">Evidence-led insights</span></div></div>
        </div>
        <div className="hero-visual relative">
          <div className="hero-image h-[380px] overflow-hidden rounded-[3px] sm:h-[500px]">
            {lead ? <Link to={`/property/${lead.id}`} className="block h-full w-full"><PropertyImage property={lead} thumbnail={false} className="h-full w-full object-cover"/></Link> :
              <div className="hero-empty flex h-full flex-col justify-between p-8"><div className="flex justify-between text-xs tracking-[.22em]"><span>DWELLING / EST. 2026</span><span>01—06</span></div>
                <div className="hero-architecture" aria-hidden="true"><div className="building-one"/><div className="building-two"/><div className="building-three"/></div>
                <div><span className="text-xs tracking-[.18em]">AN OPEN DOOR</span><h2 className="mt-2 font-editorial text-4xl italic leading-none">A new perspective<br/>on property.</h2></div>
              </div>}
          </div>
          <div className="hero-figcaption mt-3 flex justify-between gap-2 text-[11px] tracking-[.08em] text-muted"><span>{lead ? `${lead.area_name || lead.city}, ${lead.city}` : 'Designed for every next chapter'}</span><span>THE PROPERTY EDIT</span></div>
          {lead && <Link to={`/property/${lead.id}`} className="feature-slip absolute -bottom-6 -start-5 hidden max-w-64 border border-line bg-white p-5 shadow-xl shadow-[#2a342515] sm:block"><p className="kicker">A CLOSER LOOK</p><p className="mt-2 line-clamp-2 font-medium">{lead.title}</p><p className="mt-2 text-lg font-semibold tabular-nums">{currency(lead.price, lead.currency, language)}</p><span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-accent">View details <ArrowRight size={14}/></span></Link>}
        </div>
      </div>
    </section>

    <section className="page-shell relative z-10 -mt-3 lg:-mt-4" aria-label="Property search">
      <form onSubmit={search} className="search-console studio-panel p-4 sm:p-6">
        <div className="grid gap-4 md:grid-cols-[1.4fr_1fr_1fr_auto] md:items-end">
          <label className="form-label">City<div className="relative mt-2"><MapPin size={17} className="pointer-events-none absolute start-3 top-3.5 text-muted"/><input className="field ps-10" value={draft.city} onChange={event => setDraft(previous => ({ ...previous, city: event.target.value }))} placeholder="Karachi, Lahore, Islamabad…" /></div></label>
          <label className="form-label">I want to<select className="field mt-2" value={draft.purpose} onChange={event => setDraft(previous => ({ ...previous, purpose: event.target.value as Filters['purpose'] }))}><option value="">Buy or rent</option><option value="sale">Buy</option><option value="rent">Rent</option></select></label>
          <label className="form-label">Property type<select className="field mt-2" value={draft.kind} onChange={event => setDraft(previous => ({ ...previous, kind: event.target.value as Filters['kind'] }))}>{kinds.map(kind => <option key={kind.id} value={kind.id}>{kind.title}</option>)}</select></label>
          <Button type="submit" className="h-[47px] !rounded-md"><Search size={18}/>Find properties</Button>
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
          <div className="flex min-w-0 items-center gap-2"><Search size={16} className="shrink-0 text-muted"/><input aria-label="Keyword search" placeholder="Street, building, feature or keyword…" className="min-w-0 flex-1 bg-transparent py-1 text-sm outline-none placeholder:text-muted" value={draft.q} onChange={event => setDraft(previous => ({ ...previous, q: event.target.value }))}/></div>
          <button type="button" className="inline-flex items-center gap-2 text-xs font-semibold text-ink" aria-expanded={advanced} onClick={() => setAdvanced(!advanced)}><SlidersHorizontal size={15}/>More filters{activeFilters > 0 ? ` (${activeFilters})` : ''}</button>
        </div>
        {advanced && <div className="mt-4 grid gap-3 border-t border-line pt-5 sm:grid-cols-4">
          <label className="form-label">Housing society / district<input className="field mt-2" value={draft.society} placeholder="DHA, Scheme 33…" list="known-locations" onChange={event => setDraft(previous => ({ ...previous, society: event.target.value }))}/><datalist id="known-locations">{locationHints.map(item => <option value={item} key={item}/>)}</datalist></label>
          <label className="form-label">Phase / block<input className="field mt-2" value={draft.block} placeholder="Phase 6, Block C…" onChange={event => setDraft(previous => ({ ...previous, block: event.target.value }))}/></label>
          <label className="form-label">Min. price (PKR)<input className="field mt-2" type="number" min="0" value={draft.min_price} onChange={event => setDraft(previous => ({ ...previous, min_price: event.target.value }))}/></label>
          <label className="form-label">Max. price (PKR)<input className="field mt-2" type="number" min="0" value={draft.max_price} onChange={event => setDraft(previous => ({ ...previous, max_price: event.target.value }))}/></label>
          <label className="form-label">Minimum bedrooms<input className="field mt-2" type="number" min="0" value={draft.minimum_bedrooms} onChange={event => setDraft(previous => ({ ...previous, minimum_bedrooms: event.target.value }))}/></label>
          <label className="form-label">Minimum bathrooms<input className="field mt-2" type="number" min="0" value={draft.minimum_bathrooms} onChange={event => setDraft(previous => ({ ...previous, minimum_bathrooms: event.target.value }))}/></label>
          <label className="form-label">Minimum area (sq ft)<input className="field mt-2" type="number" min="0" value={draft.min_area} onChange={event => setDraft(previous => ({ ...previous, min_area: event.target.value }))}/></label>
          <label className="form-label">Maximum area (sq ft)<input className="field mt-2" type="number" min="0" value={draft.max_area} onChange={event => setDraft(previous => ({ ...previous, max_area: event.target.value }))}/></label>
          <label className="form-label">Sort by<select className="field mt-2" value={draft.sort} onChange={event => setDraft(previous => ({ ...previous, sort: event.target.value as Filters['sort'] }))}><option value="newest">Newest first</option><option value="price_asc">Price: low to high</option><option value="price_desc">Price: high to low</option><option value="area_desc">Largest first</option></select></label>
          <button type="button" className="inline-flex items-center gap-1 text-xs font-medium text-muted hover:text-ink" onClick={reset}><X size={14}/>Reset all</button>
          <Button type="submit" size="sm" className="sm:col-start-4 !rounded-md">Apply filters</Button>
        </div>}
      </form>
      {user && <div className="mt-4 flex flex-wrap items-center gap-4 px-2">
        <button type="button" onClick={() => { setSavingSearch(value => !value); setSearchNotice(''); }} className="inline-flex items-center gap-2 text-xs font-semibold text-accent"><BookmarkPlus size={16}/>Save this search</button>
        {savingSearch && <form onSubmit={event => void saveSearch(event)} className="flex flex-wrap gap-2"><input className="field !w-52" minLength={2} maxLength={120} value={searchName} onChange={event => setSearchName(event.target.value)} placeholder="e.g. DHA family homes" required/><Button type="submit">Save preferences</Button></form>}
        {searchNotice && <span role="status" className="text-xs text-muted">{searchNotice}</span>}
      </div>}
    </section>

    <section id="property-results" className="page-shell scroll-mt-28 pb-20 pt-18 sm:pt-24">
      <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="kicker">THE PROPERTY COLLECTION / {new Date().getFullYear()}</p><h2 className="editorial-title mt-3 text-[clamp(2.2rem,4.6vw,3.8rem)]">{agencySlug ? 'An agency’s current collection.' : 'Spaces worth exploring.'}</h2>
        <p className="mt-3 text-sm text-muted">Find a good fit, without the guesswork.</p></div>
        <p className="text-sm tabular-nums text-muted">{loading ? 'Searching…' : `${results?.total ?? 0} listings available`}</p>
      </div>
      <div className="mt-8 flex flex-wrap gap-2 border-b border-line pb-5" aria-label="Property categories">{kinds.map(kind => <button type="button" key={kind.id} onClick={() => selectType(kind.id)}
        aria-pressed={filters.kind === kind.id} className={`category-filter rounded-full border px-4 py-2 text-xs font-semibold ${filters.kind === kind.id ? 'category-filter-active' : ''}`}>{kind.title}</button>)}</div>
      {error && <p role="alert" className="error-note mt-6">{error}</p>}
      {loading ? <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">{Array.from({ length: 6 }, (_, index) => <div key={index} className="h-[420px] animate-pulse bg-[#ece9e1]"/>)}</div> :
        (results?.items.length ?? 0) > 0 ? <div className="mt-8 grid gap-x-6 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">{results!.items.map(item => <PropertyCard property={item} key={item.id}/>)}</div> :
          <div className="empty-space mt-8"><Building2 size={36} strokeWidth={1}/><h3 className="mt-5 font-editorial text-3xl">Nothing quite like that, yet.</h3><p className="mt-3 text-sm text-muted">Try another city, property type, or price range.</p><button type="button" onClick={reset} className="link-text mt-5 text-sm">Clear filters</button></div>}
      {!loading && results && results.total > results.size && <nav className="mt-12 flex items-center justify-center gap-5" aria-label="Results pages">
        <Button variant="outline" disabled={page <= 1} onClick={() => { setPage(value => value - 1); }}><ChevronLeft size={16}/>Previous</Button>
        <span className="text-sm tabular-nums text-muted">{page} / {Math.ceil(results.total / results.size)}</span>
        <Button variant="outline" disabled={page >= Math.ceil(results.total / results.size)} onClick={() => setPage(value => value + 1)}>Next <ChevronRight size={16}/></Button></nav>}
    </section>
    <section className="bg-ink py-14 text-white"><div className="page-shell flex flex-wrap items-center justify-between gap-6"><div><p className="kicker !text-[#d6b9a7]">SELLING OR LETTING?</p><h2 className="mt-3 font-editorial text-3xl sm:text-4xl">Your property has a story. Tell it well.</h2></div>
      <Link to={professional ? '/broker/listings/new' : '/auth'} className="inline-flex items-center gap-2 border border-white/50 px-6 py-3 text-sm font-semibold transition-colors hover:bg-white hover:text-ink">Create a property ad <ArrowRight size={17}/></Link></div></section>
  </main>;
}
