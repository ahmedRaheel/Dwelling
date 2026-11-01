import { useEffect, useState } from 'react';
import { ArrowRight, Building2, MapPin, Phone, Search } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '@/api/client';
import type { Agency } from '@/api/types';
import { errorMessage } from '@/lib/utils';

export function AgencyDirectory() {
  const [city, setCity] = useState('');
  const [query, setQuery] = useState('');
  const [agencies, setAgencies] = useState<Agency[]>([]);
  const [error, setError] = useState('');
  useEffect(() => {
    let mounted = true;
    void api<Agency[]>(`/agencies${query ? `?city=${encodeURIComponent(query)}` : ''}`)
      .then(items => { if (mounted) { setAgencies(items); setError(''); } })
      .catch(cause => { if (mounted) setError(errorMessage(cause)); });
    return () => { mounted = false; };
  }, [query]);

  return <main className="page-shell pb-24 pt-12">
    <p className="kicker">PEOPLE BEHIND THE PROPERTIES</p><h1 className="editorial-title mt-3 text-[clamp(2.4rem,5vw,4rem)]">Find a local property expert.</h1>
    <p className="mt-4 max-w-2xl text-sm leading-7 text-muted">Meet agencies, see their current published inventory and contact them directly when they've chosen to share their details.</p>
    <form className="mt-9 flex max-w-xl items-end gap-3" onSubmit={event => { event.preventDefault(); setQuery(city.trim()); }}><label className="form-label flex-1">City<input className="field mt-2" placeholder="Karachi, Islamabad, Lahore…" value={city} onChange={event => setCity(event.target.value)}/></label><button type="submit" className="mb-0.5 inline-flex h-11 items-center gap-2 bg-ink px-5 text-sm font-semibold text-white"><Search size={16}/>Search</button></form>
    {error && <p className="error-note mt-6" role="alert">{error}</p>}
    {agencies.length === 0 ? <div className="empty-space mt-10">No agencies found. Try another city.</div> :
      <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-3">{agencies.map(agency => <article key={agency.id} className="studio-panel flex flex-col p-7">
        <div className="flex items-start justify-between gap-3"><div className="flex size-12 items-center justify-center bg-[#efece4] text-accent"><Building2 size={21}/></div><span className="text-xs text-muted">{agency.published_listings} live listings</span></div>
        <h2 className="mt-6 text-xl font-semibold">{agency.name}</h2><p className="mt-3 line-clamp-3 min-h-16 text-sm leading-6 text-muted">{agency.public_description || 'An active property agency. View its current listings to learn more.'}</p>
        {agency.public_city && <p className="mt-3 flex items-center gap-2 text-xs text-muted"><MapPin size={14}/>{agency.public_city}</p>}
        {agency.public_phone && <a className="mt-3 inline-flex items-center gap-2 text-xs font-semibold" href={`tel:${agency.public_phone}`}><Phone size={14}/>{agency.public_phone}</a>}
        <Link className="link-text mt-7 inline-flex items-center gap-2 border-t border-line pt-5 text-sm" to={`/?agency=${encodeURIComponent(agency.slug)}`}>Browse agency properties <ArrowRight size={15}/></Link>
      </article>)}</div>}
    <p className="mt-8 text-xs text-muted">Agency details are self-reported. A listing count is not an identity or title verification.</p>
  </main>;
}
