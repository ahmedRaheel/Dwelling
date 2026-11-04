import { useCallback, useEffect, useState, type FormEvent } from 'react';
import {
  ArrowLeft, ArrowRight, BadgeCheck, CheckCircle2, CircleAlert, Eye,
  FileText, Image as ImageIcon, LoaderCircle, MapPin, Save, Send,
} from 'lucide-react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { api } from '@/api/client';
import type {
  ListingInsights, ListingReadiness, PortionKind, Property, PropertyInput, PropertyKind,
  Purpose, RoomType,
} from '@/api/types';
import { PropertyImage } from '@/components/listings/PropertyImage';
import { PhotoManager } from '@/components/listings/PhotoManager';
import { VideoManager } from '@/components/listings/VideoManager';
import { Button } from '@/components/ui/button';
import { useLanguage } from '@/context/LanguageContext';
import { currency, errorMessage } from '@/lib/utils';

type Stage = 'details' | 'photos' | 'publish';
const stages: { key: Stage; name: string; icon: typeof FileText }[] = [
  { key: 'details', name: 'Property details', icon: FileText },
  { key: 'photos', name: 'Photography', icon: ImageIcon },
  { key: 'publish', name: 'Review & publish', icon: Eye },
];
const amenityChoices = [
  'Parking', 'Elevator', 'Security', 'Generator', 'Solar power', 'Balcony',
  'Garden', 'Terrace', 'Air conditioning', 'Gas connection', 'Water supply',
  'Internet', 'Near school', 'Near transport', 'Corner property', 'Gated community',
];
const kinds: { value: PropertyKind; label: string }[] = [
  { value: 'house', label: 'House' }, { value: 'apartment', label: 'Apartment' },
  { value: 'portion', label: 'Portion / floor' }, { value: 'plot', label: 'Plot' },
  { value: 'commercial_building', label: 'Commercial' }, { value: 'pg', label: 'Paying guest / shared' },
];

const text = (form: FormData, field: string) => String(form.get(field) ?? '').trim();
const number = (form: FormData, field: string) => Number(form.get(field) || 0);
const checked = (form: FormData, field: string) => form.has(field);

function toListing(form: FormData, kind: PropertyKind, purpose: Purpose, amenities: string[]): PropertyInput {
  const floor = text(form, 'floor_number');
  const latitude = text(form, 'latitude');
  const longitude = text(form, 'longitude');
  return {
    title: text(form, 'title'), description: text(form, 'description'), kind,
    purpose: kind === 'pg' ? 'rent' : purpose, status: 'draft',
    city: text(form, 'city'), area_name: text(form, 'area_name'), address: text(form, 'address'),
    society: text(form, 'society'), block: text(form, 'block'),
    price_negotiable: checked(form, 'price_negotiable'), ready_to_move: checked(form, 'ready_to_move'),
    video_url: text(form, 'video_url') || null,
    price: text(form, 'price'), currency: 'PKR', area_sqft: text(form, 'area_sqft'),
    bedrooms: number(form, 'bedrooms'), bathrooms: number(form, 'bathrooms'),
    furnished: checked(form, 'furnished'), photo_url: null,
    amenities, highlights: text(form, 'highlights').split('\n').map(line => line.trim()).filter(Boolean),
    contact_phone: text(form, 'contact_phone') || null,
    latitude: latitude ? Number(latitude) : null, longitude: longitude ? Number(longitude) : null,
    pg: kind === 'pg' ? {
      room_type: text(form, 'room_type') as RoomType,
      total_beds: number(form, 'total_beds'), available_beds: number(form, 'available_beds'),
      food_included: checked(form, 'food_included'),
      rules: text(form, 'pg_rules') ? { house_rules: text(form, 'pg_rules') } : {},
    } : null,
    portion: kind === 'portion' ? {
      portion_kind: text(form, 'portion_kind') as PortionKind,
      floor_number: floor ? Number(floor) : null,
      separate_electricity_meter: checked(form, 'separate_electricity_meter'),
      separate_gas_meter: checked(form, 'separate_gas_meter'),
      separate_water_meter: checked(form, 'separate_water_meter'),
      parent_property_id: text(form, 'parent_property_id') || null,
    } : null,
  };
}

export function ListingComposer() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { language } = useLanguage();
  const [property, setProperty] = useState<Property | null>(null);
  const [loading, setLoading] = useState(Boolean(id));
  const [kind, setKind] = useState<PropertyKind>('house');
  const [purpose, setPurpose] = useState<Purpose>('sale');
  const [amenities, setAmenities] = useState<string[]>([]);
  const initialStage = new URLSearchParams(location.search).get('step');
  const [stage, setStage] = useState<Stage>(initialStage === 'photos' ? 'photos' : initialStage === 'publish' ? 'publish' : 'details');
  const [readiness, setReadiness] = useState<ListingReadiness | null>(null);
  const [insights, setInsights] = useState<ListingInsights | null>(null);
  const [insightsError, setInsightsError] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [savedMessage, setSavedMessage] = useState('');

  const reload = useCallback(async () => {
    if (!id) return;
    const latest = await api<Property>(`/listings/${id}`);
    setProperty(latest);
    setKind(latest.kind); setPurpose(latest.purpose); setAmenities(latest.amenities);
  }, [id]);

  useEffect(() => {
    if (!id) return;
    void reload().catch(cause => setError(errorMessage(cause))).finally(() => setLoading(false));
  }, [id, reload]);

  useEffect(() => {
    if (!property || stage !== 'publish') return;
    void api<ListingReadiness>(`/listings/${property.id}/readiness`).then(setReadiness).catch(cause => setError(errorMessage(cause)));
    setInsights(null); setInsightsError('');
    void api<ListingInsights>(`/listings/${property.id}/insights`).then(setInsights).catch(cause => setInsightsError(errorMessage(cause))); 
  }, [stage, property]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(''); setSavedMessage('');
    const payload = toListing(new FormData(event.currentTarget), kind, purpose, amenities);
    try {
      let updated: Property;
      if (property) {
        updated = await api<Property>(`/listings/${property.id}`, {
          method: 'PATCH', body: JSON.stringify({ ...payload, status: property.status, expected_version: property.version }),
        });
      } else {
        updated = await api<Property>('/listings', { method: 'POST', body: JSON.stringify(payload) });
      }
      setProperty(updated);
      setSavedMessage('Your changes have been saved.');
      if (!id) navigate(`/broker/listings/${updated.id}/edit?step=photos`, { replace: true });
      setStage('photos');
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  }

  async function publish(action: 'publish' | 'unpublish') {
    if (!property) return;
    setBusy(true); setError('');
    try {
      const updated = await api<Property>(`/listings/${property.id}/${action}`, { method: 'POST' });
      setProperty(updated);
      setReadiness(await api<ListingReadiness>(`/listings/${property.id}/readiness`));
      setSavedMessage(action === 'publish' ? 'Your ad is now live in the marketplace.' : 'Your ad is back in drafts.');
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  }

  if (loading) return <main className="page-shell py-20 text-muted">Loading listing editor…</main>;
  if (id && !property) return <main className="page-shell py-20"><p className="error-note">{error || 'Unable to open this listing.'}</p><Link className="link-text" to="/broker">Back to workspace</Link></main>;

  const field = (label: string, name: string, value: string | number = '', type = 'text', required = false, placeholder = '') =>
    <label className="form-label" key={name}>{label}
      <input className="field mt-2" name={name} defaultValue={value} type={type} step={type === 'number' ? 'any' : undefined} required={required} placeholder={placeholder}/>
    </label>;

  return <main className="page-shell pb-24 pt-9">
    <Link to="/broker" className="inline-flex items-center gap-2 text-sm font-medium text-muted hover:text-ink"><ArrowLeft size={17}/>Back to workspace</Link>
    <div className="mt-8 flex flex-wrap items-end justify-between gap-4">
      <div><p className="kicker">THE LISTING STUDIO / {property ? `DW-${property.id.slice(0, 8).toUpperCase()}` : 'NEW AD'}</p>
        <h1 className="editorial-title mt-2 text-[clamp(2rem,4vw,3.5rem)]">{property ? 'Make a lasting first impression.' : 'Every great listing starts here.'}</h1>
        <p className="mt-3 max-w-xl text-sm leading-6 text-muted">Thoughtful details, honest photographs and a clear story help customers see themselves in your space.</p></div>
      {property && <span className={`status-chip status-${property.status}`}>{property.status}</span>}
    </div>

    <div className="mt-9 grid gap-8 lg:grid-cols-[245px_minmax(0,1fr)] xl:gap-14">
      <aside className="self-start lg:sticky lg:top-28">
        <nav aria-label="Listing editor steps" className="space-y-1">
          {stages.map((item, index) => <button key={item.key} type="button" disabled={!property && item.key !== 'details'}
            onClick={() => { setStage(item.key); setError(''); setSavedMessage(''); }}
            className={`step-link flex w-full items-center gap-3 rounded px-3 py-4 text-start text-sm ${stage === item.key ? 'step-link-active' : ''}`}>
            <span className="flex size-8 shrink-0 items-center justify-center rounded-full border border-current/20 text-xs tabular-nums">{index + 1}</span>
            <span className="font-medium">{item.name}</span>
          </button>)}
        </nav>
        <div className="mt-8 border-t border-line pt-6">
          <p className="kicker">AN AD THAT WORKS HARDER</p>
          <p className="mt-3 text-sm leading-6 text-muted">A complete gallery and honest description make it easier to arrange qualified viewings.</p>
          {property && <Link to={`/property/${property.id}`} className="link-text mt-4 inline-flex items-center gap-2 text-sm">Preview listing <ArrowRight size={15}/></Link>}
        </div>
      </aside>

      <div className="min-w-0 space-y-6">
        {error && <div role="alert" className="error-note">{error}</div>}
        {savedMessage && <p role="status" className="success-note"><CheckCircle2 size={16}/>{savedMessage}</p>}
        {stage === 'details' && <form key={property?.id ?? 'new'} onSubmit={event => void save(event)} className="studio-panel space-y-9 p-5 sm:p-9">
          <section className="space-y-5"><div><p className="kicker">01 / OVERVIEW</p><h2 className="studio-heading">The essentials</h2></div>
            <div className="grid gap-5 sm:grid-cols-2">
              {field('Property headline *', 'title', property?.title ?? '', 'text', true, 'e.g. Sunlit two-bedroom apartment in Clifton')}
              {field('City *', 'city', property?.city ?? 'Karachi', 'text', true)}
              {field('Neighbourhood *', 'area_name', property?.area_name ?? '', 'text', true, 'DHA Phase 6')}
              {field('Housing society / locality', 'society', property?.society ?? '', 'text', false, 'DHA, Bahria Town, Scheme 33…')}
              {field('Phase / block', 'block', property?.block ?? '', 'text', false, 'Phase 6, Block B…')}
              {field('Address (public listing)', 'address', property?.address ?? '')}
              <label className="form-label">Property type<select className="field mt-2" value={kind} onChange={event => { const next = event.target.value as PropertyKind; setKind(next); if (next === 'pg') setPurpose('rent'); }}>{kinds.map(type => <option key={type.value} value={type.value}>{type.label}</option>)}</select></label>
              <label className="form-label">Offer type<select className="field mt-2" value={kind === 'pg' ? 'rent' : purpose} disabled={kind === 'pg'} onChange={event => setPurpose(event.target.value as Purpose)}><option value="sale">For sale</option><option value="rent">For rent</option></select></label>
              {field(kind === 'pg' ? 'Monthly price per bed (PKR) *' : purpose === 'rent' ? 'Monthly rent (PKR) *' : 'Asking price (PKR) *', 'price', property?.price ?? '', 'number', true)}
              {field('Covered / plot area (sq ft) *', 'area_sqft', property?.area_sqft ?? '', 'number', true)}
              {kind !== 'plot' && <>{field('Bedrooms', 'bedrooms', property?.bedrooms ?? 0, 'number')}{field('Bathrooms', 'bathrooms', property?.bathrooms ?? 0, 'number')}</>}
              {field('Video tour (YouTube / Vimeo HTTPS)', 'video_url', property?.video_url ?? '', 'url')}
              {field('Agent or owner phone (optional)', 'contact_phone', property?.contact_phone ?? '', 'tel', false, '+92 3XX XXXXXXX')}
              <label className="flex items-center gap-3 self-end pb-3 text-sm font-medium"><input type="checkbox" name="furnished" defaultChecked={property?.furnished ?? false} className="accent-[#ad6b4a]"/>Furnished</label>
              <label className="flex items-center gap-3 self-end pb-3 text-sm font-medium"><input type="checkbox" name="ready_to_move" defaultChecked={property?.ready_to_move ?? false} className="accent-[#ad6b4a]"/>Ready for possession</label>
              <label className="flex items-center gap-3 self-end pb-3 text-sm font-medium"><input type="checkbox" name="price_negotiable" defaultChecked={property?.price_negotiable ?? false} className="accent-[#ad6b4a]"/>Price negotiable</label>
            </div>
          </section>
          {kind === 'portion' && <section className="space-y-5 border-t border-line pt-8"><div><p className="kicker">PORTION / FLOOR CONFIGURATION</p><h2 className="studio-heading">Independent space</h2></div>
            <div className="grid gap-5 sm:grid-cols-2">
              <label className="form-label">Portion type<select className="field mt-2" name="portion_kind" defaultValue={property?.portion?.portion_kind ?? 'upper'}><option value="upper">Upper portion</option><option value="lower">Lower portion</option><option value="floor">Separate floor</option></select></label>
              {field('Floor number', 'floor_number', property?.portion?.floor_number ?? '', 'number')}
              {field('Parent property listing ID (optional)', 'parent_property_id', property?.portion?.parent_property_id ?? '')}
            </div>
            <div className="flex flex-wrap gap-5">{(['separate_electricity_meter', 'separate_gas_meter', 'separate_water_meter'] as const).map(key => <label key={key} className="flex items-center gap-2 text-sm"><input name={key} type="checkbox" defaultChecked={property?.portion?.[key] ?? false}/>{key.replaceAll('_', ' ')}</label>)}</div>
          </section>}
          {kind === 'pg' && <section className="space-y-5 border-t border-line pt-8"><div><p className="kicker">PAYING GUEST</p><h2 className="studio-heading">Room-sharing details</h2></div>
            <div className="grid gap-5 sm:grid-cols-2">
              <label className="form-label">Room type<select className="field mt-2" name="room_type" defaultValue={property?.pg?.room_type ?? 'single'}><option value="single">Single</option><option value="twin">Twin sharing</option><option value="dormitory">Dormitory</option></select></label>
              {field('Total beds *', 'total_beds', property?.pg?.total_beds ?? 1, 'number', true)}
              {field('Available beds *', 'available_beds', property?.pg?.available_beds ?? 1, 'number', true)}
              {field('House rules', 'pg_rules', String(property?.pg?.rules.house_rules ?? ''))}
            </div>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="food_included" defaultChecked={property?.pg?.food_included ?? false}/>Meals included in rent</label>
          </section>}
          <section className="space-y-5 border-t border-line pt-8"><div><p className="kicker">02 / PRESENTATION</p><h2 className="studio-heading">Tell the whole story</h2></div>
            <label className="form-label">Property description *<textarea name="description" className="field mt-2 min-h-44 resize-y" defaultValue={property?.description ?? ''} placeholder="Describe the layout, condition, natural light, nearby conveniences and what makes this property different…"/>
              <span className="mt-2 block text-xs font-normal text-muted">At least 50 characters required to publish. Be accurate and specific.</span></label>
            <label className="form-label">Key selling points (one per line)<textarea name="highlights" maxLength={1200} className="field mt-2 min-h-28 resize-y" defaultValue={property?.highlights.join('\n') ?? ''} placeholder={'Covered parking\nCorner-facing living room\nMinutes from the main road'}/></label>
            <div><p className="form-label mb-3">Features & amenities</p><div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{amenityChoices.map(name => <label key={name} className={`amenity-chip flex items-center gap-2 rounded border px-3 py-3 text-xs font-medium ${amenities.includes(name) ? 'amenity-selected' : ''}`}>
              <input type="checkbox" checked={amenities.includes(name)} onChange={event => setAmenities(previous => event.target.checked ? [...previous, name] : previous.filter(value => value !== name))}/>{name}</label>)}</div></div>
          </section>
          <section className="space-y-5 border-t border-line pt-8"><div><p className="kicker">03 / LOCATION</p><h2 className="studio-heading">Show where it is</h2><p className="mt-2 text-xs text-muted">Coordinates are optional. Only add them if you are comfortable sharing the location publicly.</p></div>
            <div className="grid gap-5 sm:grid-cols-2">
              {field('Latitude', 'latitude', property?.latitude ?? '', 'number')}
              {field('Longitude', 'longitude', property?.longitude ?? '', 'number')}
            </div>
          </section>
          <div className="flex flex-wrap justify-between gap-3 border-t border-line pt-7"><p className="self-center text-xs text-muted">Saved as a draft until you publish.</p>
            <Button type="submit" disabled={busy} className="!rounded-md">{busy ? <LoaderCircle size={16} className="animate-spin"/> : <Save size={16}/>}Save & continue <ArrowRight size={16}/></Button></div>
        </form>}

        {stage === 'photos' && property && <div className="studio-panel p-5 sm:p-9"><PhotoManager property={property} onChanged={async () => {
          const latest = await api<Property>(`/listings/${property.id}`); setProperty(latest);
        }}/><VideoManager property={property}/><div className="mt-9 flex justify-end border-t border-line pt-6"><Button onClick={() => { setStage('publish'); setSavedMessage(''); }} className="!rounded-md">Review ad <ArrowRight size={16}/></Button></div></div>}

        {stage === 'publish' && property && <div className="space-y-6">
          <section className="studio-panel overflow-hidden"><div className="grid sm:grid-cols-[200px_1fr]">
            <PropertyImage property={property} thumbnail={false} className="h-48 w-full object-cover sm:h-full"/>
            <div className="p-6"><p className="kicker">LISTING PREVIEW</p><h2 className="mt-2 text-xl font-semibold">{property.title}</h2>
              <p className="mt-2 flex items-center gap-1 text-sm text-muted"><MapPin size={15}/>{property.area_name}, {property.city}</p>
              <p className="mt-4 text-2xl font-semibold tabular-nums">{currency(property.price, property.currency, language)}{property.purpose === 'rent' && <span className="ms-2 text-xs font-normal text-muted">per month</span>}</p>
              <Link to={`/property/${property.id}`} className="link-text mt-4 inline-flex items-center gap-1 text-sm">Open full preview <ArrowRight size={15}/></Link>
            </div></div></section>
          <section className="studio-panel space-y-4 p-6 sm:p-9" aria-label="Smart listing insights">
            <p className="kicker">SMART LISTING INSIGHTS</p>
            <h2 className="studio-heading">Know your local asking-price position</h2>
            {insightsError && <p role="status" className="text-sm text-muted">Pricing context unavailable: {insightsError}</p>}
            {!insights && !insightsError && <p className="text-sm text-muted">Reviewing comparable published ads…</p>}
            {insights && <>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-md border border-line p-4"><p className="text-xs text-muted">Your asking price / sq ft</p><p className="mt-2 text-xl font-semibold">{insights.asking_price_per_sqft === null ? 'N/A' : currency(insights.asking_price_per_sqft, property.currency, language)}</p></div>
                <div className="rounded-md border border-line p-4"><p className="text-xs text-muted">Local median asking price</p><p className="mt-2 text-xl font-semibold">{insights.local_median_asking_price === null ? 'Not enough data' : currency(insights.local_median_asking_price, property.currency, language)}</p></div>
                <div className="rounded-md border border-line p-4"><p className="text-xs text-muted">Comparable listings</p><p className="mt-2 text-xl font-semibold">{insights.local_sample_size}</p></div>
              </div>
              {insights.difference_from_local_median_pct !== null && <p className="text-sm font-medium">Your advertised price is {Math.abs(insights.difference_from_local_median_pct)}% {insights.difference_from_local_median_pct > 0 ? 'above' : insights.difference_from_local_median_pct < 0 ? 'below' : 'equal to'} the local asking-price median.</p>}
              {insights.warnings.map(warning => <p key={warning} className="flex gap-2 text-sm text-muted"><CircleAlert size={16} className="mt-0.5 shrink-0"/>{warning}</p>)}
              <p className="text-xs leading-5 text-muted">{insights.disclaimer}</p>
            </>}
          </section>
          <section className="studio-panel space-y-5 p-6 sm:p-9">
            <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="kicker">QUALITY CHECK</p><h2 className="studio-heading mt-2">Ready for the marketplace?</h2></div>
              {readiness && <div className="quality-score"><strong>{readiness.score}</strong><span>/ 100</span></div>}</div>
            {!readiness ? <p className="text-muted">Checking your listing…</p> : <>
              {readiness.blockers.length > 0 && <div className="rounded border border-[#efd5c5] bg-[#fff6f0] p-4"><p className="mb-2 flex items-center gap-2 text-sm font-semibold text-[#9c4f36]"><CircleAlert size={17}/>Complete before publishing</p><ul className="list-disc space-y-1 ps-5 text-sm text-[#8a5f4e]">{readiness.blockers.map(item => <li key={item}>{item}</li>)}</ul></div>}
              {readiness.ready && <p className="success-note"><BadgeCheck size={17}/>All publication requirements are met.</p>}
              {readiness.suggestions.length > 0 && <div className="space-y-3"><h3 className="text-sm font-semibold">Worth improving</h3>{readiness.suggestions.map(item => <p key={item} className="flex items-start gap-2 text-sm text-muted"><CheckCircle2 size={16} className="mt-0.5 shrink-0"/>{item}</p>)}</div>}
            </>}
            <div className="flex flex-wrap items-center gap-3 border-t border-line pt-6">
              {property.status === 'published' ? <Button variant="outline" disabled={busy} onClick={() => void publish('unpublish')}>Move back to drafts</Button> :
                <Button disabled={busy || !readiness?.ready} onClick={() => void publish('publish')} className="!rounded-md"><Send size={16}/>Publish listing</Button>}
              <button type="button" onClick={() => setStage('details')} className="link-text text-sm">Edit details</button>
              <button type="button" onClick={() => setStage('photos')} className="link-text text-sm">Manage photos</button>
            </div>
          </section>
        </div>}
      </div>
    </div>
  </main>;
}
