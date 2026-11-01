import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { ArrowLeft, ArrowRight, ArrowUpRight, Bath, BedDouble, Check, ChevronLeft, ChevronRight,
  Copy, Heart, MapPin, Maximize2, Ruler, Share2, Sparkles, Utensils, X, Zap } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { api } from '@/api/client';
import type { Forecast, Prediction, Property } from '@/api/types';
import { PropertyImage } from '@/components/listings/PropertyImage';
import { CompareControl } from '@/components/CompareControl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/context/AuthContext';
import { useLanguage } from '@/context/LanguageContext';
import { currency, errorMessage } from '@/lib/utils';

export function PropertyDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const { t, language } = useLanguage();
  const [property, setProperty] = useState<Property | null>(null);
  const [valuation, setValuation] = useState<Prediction | null>(null);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [error, setError] = useState('');
  const [activePhoto, setActivePhoto] = useState(0);
  const [galleryOpen, setGalleryOpen] = useState(false);
  const [saved, setSaved] = useState(false);
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);
  const [shared, setShared] = useState(false);
  const [viewingSent, setViewingSent] = useState(false);
  const [viewingBusy, setViewingBusy] = useState(false);

  useEffect(() => {
    if (!id) return;
    let active = true;
    void api<Property>(`/listings/${id}`).then(item => {
      if (!active) return;
      setProperty(item);
      void api<Prediction>(`/ai/valuation/${id}`).then(data => { if (active) setValuation(data); }).catch(() => {});
      if (item.purpose === 'rent') void api<Forecast>(`/ai/rent-forecast/${id}`).then(data => { if (active) setForecast(data); }).catch(() => {});
    }).catch(cause => { if (active) setError(errorMessage(cause)); });
    return () => { active = false; };
  }, [id]);

  const photos = useMemo(() => {
    if (!property) return [];
    const ordered = [...property.photos].filter(photo => photo.category === 'gallery').sort((a, b) => a.position - b.position);
    const cover = ordered.find(item => item.is_cover);
    return cover ? [cover, ...ordered.filter(photo => photo.id !== cover.id)] : ordered;
  }, [property]);

  useEffect(() => {
    if (!galleryOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setGalleryOpen(false);
      if (event.key === 'ArrowRight') setActivePhoto(value => (value + 1) % photos.length);
      if (event.key === 'ArrowLeft') setActivePhoto(value => (value + photos.length - 1) % photos.length);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [galleryOpen, photos.length]);

  async function save() {
    if (!property || !user) return;
    try {
      await api('/ai/interactions', { method: 'POST', body: JSON.stringify({ property_id: property.id, action: 'save' }) });
      setSaved(true);
    } catch (cause) { setError(errorMessage(cause)); }
  }
  async function share() {
    const url = window.location.href;
    try {
      if (navigator.share) await navigator.share({ title: property?.title, url });
      else { await navigator.clipboard.writeText(url); setShared(true); }
    } catch { /* User may dismiss the native share dialog. */ }
  }
  async function sendInquiry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!property || !user) return;
    setSending(true); setError('');
    const fields = new FormData(event.currentTarget);
    try {
      await api('/leads/inquiries', { method: 'POST', body: JSON.stringify({
        property_id: property.id, contact_name: String(fields.get('name')),
        contact_email: String(fields.get('email')), contact_phone: String(fields.get('phone')) || null,
        message: String(fields.get('message')),
      }) });
      await api('/ai/interactions', { method: 'POST', body: JSON.stringify({ property_id: property.id, action: 'inquiry' }) }).catch(() => {});
      setSent(true);
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setSending(false); }
  }

  async function requestViewing(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!property || !user) return;
    setViewingBusy(true); setError('');
    const form = new FormData(event.currentTarget);
    const requestedDate = new Date(String(form.get('preferred_at')));
    try {
      if (Number.isNaN(requestedDate.getTime())) throw new Error('Choose a valid viewing date and time.');
      await api('/viewings', { method: 'POST', body: JSON.stringify({
        property_id: property.id, preferred_at: requestedDate.toISOString(),
        contact_name: String(form.get('contact_name')),
        contact_phone: String(form.get('contact_phone')),
        note: String(form.get('note') ?? ''),
      }) });
      setViewingSent(true);
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setViewingBusy(false); }
  }

  if (!property) return <main className="page-shell py-20">{error ? <p role="alert" className="error-note">{error}</p> : <p className="text-muted">{t('loading')}</p>}</main>;
  const area = [property.area_name, property.city].filter(Boolean).join(', ');
  const whatsapp = property.contact_phone?.replace(/\D/g, '') ?? '';
  const hasWhatsapp = whatsapp.length >= 10 && whatsapp.length <= 15;
  const mapUrl = property.latitude != null && property.longitude != null
    ? `https://www.google.com/maps/search/?api=1&query=${property.latitude},${property.longitude}` : null;

  return <main className="page-shell pb-24 pt-9">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <Link to="/" className="inline-flex items-center gap-2 text-xs font-medium text-muted hover:text-ink"><ArrowLeft size={17}/>Back to properties</Link>
      <div className="flex items-center gap-2"><span className="text-xs text-muted">DW-{property.id.slice(0, 8).toUpperCase()}</span>
        <button type="button" onClick={() => void share()} className="mini-action"><Share2 size={15}/>{shared ? 'Link copied' : 'Share'}</button>
        <CompareControl id={property.id}/></div>
    </div>
    <header className="mt-8 mb-7"><div className="flex flex-wrap items-center gap-3"><p className="kicker">{property.kind.replaceAll('_', ' ')} / {property.purpose === 'sale' ? 'FOR SALE' : 'FOR RENT'}</p>
      {property.status !== 'published' && <span className={`status-chip status-${property.status}`}>{property.status} preview</span>}</div>
      <div className="mt-3 flex flex-wrap items-end justify-between gap-5"><div><h1 className="editorial-title max-w-4xl text-[clamp(2.1rem,4.5vw,3.7rem)]">{property.title}</h1>
        <p className="mt-3 flex items-center gap-2 text-sm text-muted"><MapPin size={16}/>{[property.address, area].filter(Boolean).join(' · ')}</p></div>
        <p className="text-sm tabular-nums text-muted">Listed {new Date(property.created_at).toLocaleDateString(language === 'ur' ? 'ur-PK' : 'en-PK', { year: 'numeric', month: 'long', day: 'numeric' })}</p></div>
    </header>

    <section className="relative grid h-[420px] gap-2 overflow-hidden rounded-[3px] bg-sand md:grid-cols-[1.6fr_.85fr] lg:h-[540px]" aria-label="Property photo gallery">
      <button type="button" onClick={() => { setActivePhoto(0); setGalleryOpen(true); }} disabled={photos.length === 0} className="group relative block h-full w-full overflow-hidden text-start">
        <PropertyImage property={property} thumbnail={false} photoIndex={0} className="h-full w-full transition-transform duration-500 group-hover:scale-[1.025]"/>
        {photos.length > 0 && <span className="absolute bottom-4 start-4 flex items-center gap-2 bg-white/95 px-3 py-2 text-xs font-medium"><Maximize2 size={15}/>View all photographs</span>}
      </button>
      <div className="hidden grid-rows-2 gap-2 md:grid">{[1, 2].map(index => <button type="button" key={index} onClick={() => { setActivePhoto(Math.min(index, photos.length - 1)); setGalleryOpen(true); }}
        disabled={photos.length < index + 1} className="relative h-full overflow-hidden bg-[#dedcd3] text-start"><PropertyImage property={property} photoIndex={index} thumbnail={false} className="h-full w-full transition-transform duration-500 hover:scale-[1.025]"/>
        {index === 2 && photos.length > 3 && <span className="absolute bottom-4 end-4 bg-ink/80 px-3 py-2 text-xs font-semibold text-white">+{photos.length - 3} more</span>}</button>)}</div>
    </section>

    <div className="mt-11 grid gap-12 lg:grid-cols-[minmax(0,1fr)_350px] xl:gap-20">
      <div className="min-w-0 space-y-10">
        <div className="grid gap-4 border-b border-line pb-8 sm:grid-cols-3"><div className="flex items-center gap-3"><Ruler size={22} strokeWidth={1.5} className="text-accent"/><div><p className="text-lg font-semibold tabular-nums">{Number(property.area_sqft).toLocaleString()}</p><span className="text-xs text-muted">Square feet</span></div></div>
          <div className="flex items-center gap-3"><BedDouble size={22} strokeWidth={1.5} className="text-accent"/><div><p className="text-lg font-semibold tabular-nums">{property.bedrooms}</p><span className="text-xs text-muted">Bedrooms</span></div></div>
          <div className="flex items-center gap-3"><Bath size={22} strokeWidth={1.5} className="text-accent"/><div><p className="text-lg font-semibold tabular-nums">{property.bathrooms}</p><span className="text-xs text-muted">Bathrooms</span></div></div></div>
        <section><p className="kicker">THE DETAILS</p><h2 className="studio-heading mt-3">About this property</h2>
          <p className="mt-5 whitespace-pre-line text-[15px] leading-8 text-[#606a5f]">{property.description || 'Contact the listing agent for further information.'}</p>
          {property.highlights.length > 0 && <div className="mt-6 grid gap-3 sm:grid-cols-2">{property.highlights.map((item, index) => <p key={`${index}:${item}`} className="flex items-start gap-2 text-sm"><Check size={17} className="mt-0.5 shrink-0 text-accent"/>{item}</p>)}</div>}
        </section>
        {(property.society || property.block || property.price_negotiable || property.ready_to_move || property.video_url) && <section className="border-t border-line pt-9">
          <p className="kicker">ESSENTIAL INFORMATION</p><h2 className="studio-heading mt-3">Property highlights</h2>
          <div className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
            {property.society && <p>Society / district: <strong>{property.society}</strong></p>}
            {property.block && <p>Phase / block: <strong>{property.block}</strong></p>}
            {property.ready_to_move && <p>Ready for possession</p>}
            {property.price_negotiable && <p>Asking price is negotiable</p>}
          </div>
          {property.video_url && <a href={property.video_url} target="_blank" rel="noopener noreferrer" className="link-text mt-4 inline-flex text-sm">View external video tour ↗</a>}
        </section>}
        {property.amenities.length > 0 && <section className="border-t border-line pt-9"><p className="kicker">AT A GLANCE</p><h2 className="studio-heading mt-3">Amenities & features</h2>
          <div className="mt-6 grid gap-3 sm:grid-cols-2">{property.amenities.map(item => <p key={item} className="flex items-center gap-3 border-b border-line pb-3 text-sm"><Check size={16} className="text-accent"/>{item}</p>)}</div></section>}
        {property.pg && <section className="border-t border-line pt-9"><p className="kicker">PAYING GUEST</p><h2 className="studio-heading mt-2">Shared living details</h2>
          <div className="mt-5 grid gap-4 text-sm sm:grid-cols-2"><p>Room arrangement: <strong className="capitalize">{property.pg.room_type}</strong></p><p>Available beds: <strong>{property.pg.available_beds} / {property.pg.total_beds}</strong></p>
            <p className="flex items-center gap-2"><Utensils size={15}/>Meals {property.pg.food_included ? 'included' : 'not included'}</p></div>
          {Object.entries(property.pg.rules).map(([key, value]) => <p key={key} className="mt-3 text-sm text-muted">{key.replaceAll('_', ' ')}: {String(value)}</p>)}</section>}
        {property.portion && <section className="border-t border-line pt-9"><p className="kicker">PART OF A LARGER PROPERTY</p><h2 className="studio-heading mt-2">Portion information</h2>
          <p className="mt-4 text-sm capitalize">{property.portion.portion_kind} portion {property.portion.floor_number != null ? `· Floor ${property.portion.floor_number}` : ''}</p>
          <p className="mt-3 flex items-center gap-2 text-sm text-muted"><Zap size={16}/>Independent utilities: {[property.portion.separate_electricity_meter && 'electricity', property.portion.separate_gas_meter && 'gas', property.portion.separate_water_meter && 'water'].filter(Boolean).join(', ') || 'Not specified'}</p></section>}
        {property.photos.some(photo => photo.category === 'floorplan') && <section className="border-t border-line pt-9"><p className="kicker">PROPERTY LAYOUT</p><h2 className="studio-heading mt-2">Floor plans</h2>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">{property.photos.filter(photo => photo.category === 'floorplan').map(photo => <div key={photo.id} className="border border-line p-2"><PropertyImage property={property} photoId={photo.id} thumbnail={false} className="h-72 w-full object-contain"/><p className="mt-2 text-xs text-muted">{photo.alt_text || 'Floor plan — advertiser supplied'}</p></div>)}</div>
        </section>}
        {mapUrl && <section className="border-t border-line pt-9"><p className="kicker">LOCATION</p><h2 className="studio-heading mt-2">Around the neighbourhood</h2>
          <a className="link-text mt-4 inline-flex items-center gap-2 text-sm" href={mapUrl} target="_blank" rel="noreferrer"><MapPin size={16}/>View approximate location on Google Maps <ArrowUpRight size={15}/></a></section>}
        <section className="border-t border-line pt-9"><p className="kicker">MARKET CONTEXT</p><h2 className="studio-heading mt-2">A little more perspective</h2>
          <div className="mt-5 studio-panel p-6"><div className="flex items-center gap-2 text-xs font-semibold text-accent"><Sparkles size={15}/>AI asking-price estimate</div>
            {valuation?.status === 'available' && valuation.estimate != null ? <><p className="mt-4 text-3xl font-semibold tabular-nums">{currency(valuation.estimate, valuation.currency, language)}</p>
              <p className="mt-3 text-xs leading-6 text-muted">Trained on {valuation.sample_count} advertised asking prices (not verified transactions). Holdout MAE: {valuation.holdout_mae != null ? currency(valuation.holdout_mae) : 'unavailable'}. This is not a professional valuation.</p></> :
              <p className="mt-3 text-sm leading-6 text-muted">{valuation?.reason || t('insufficient')}</p>}
            {property.purpose === 'rent' && <div className="mt-6 border-t border-line pt-5"><h3 className="text-sm font-semibold">Rental outlook</h3>
              {forecast?.status === 'available' ? <div className="mt-4 flex flex-wrap gap-2">{forecast.projected.map(item => <div key={item.month} className="border border-line p-3 text-xs"><p>{item.month}</p><strong className="mt-1 block tabular-nums">{currency(item.estimated_monthly_rent)}</strong></div>)}</div> : <p className="mt-3 text-sm text-muted">{forecast?.reason || t('insufficient')}</p>}</div>}
          </div></section>
      </div>
      <aside className="lg:sticky lg:top-28 lg:self-start">
        <div className="studio-panel p-6 sm:p-7"><p className="kicker">{property.purpose === 'rent' ? 'MONTHLY ASKING RENT' : 'ASKING PRICE'}</p>
          <p className="mt-3 text-3xl font-semibold tabular-nums tracking-tight text-ink">{currency(property.price, property.currency, language)}</p>
          <div className="mt-6 flex gap-2"><Button variant="outline" onClick={() => void save()} disabled={!user || saved} className="flex-1 !rounded-md"><Heart size={16} fill={saved ? 'currentColor' : 'none'}/>{saved ? 'Saved' : 'Save listing'}</Button>
            <Button variant="outline" onClick={() => void share()} className="!rounded-md"><Copy size={16}/></Button></div>
          {hasWhatsapp && <a className="mt-3 flex items-center justify-center gap-2 border border-ink bg-ink px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#375045]" href={`https://wa.me/${whatsapp}?text=${encodeURIComponent(`Hello, I am interested in listing DW-${property.id.slice(0, 8).toUpperCase()}: ${property.title}`)}`} target="_blank" rel="noreferrer"><ArrowUpRight size={16}/>Contact agent on WhatsApp</a>}
          {!user && <p className="mt-3 text-center text-xs text-muted"><Link to="/auth" className="link-text">Sign in</Link> to save or inquire</p>}
        </div>
        <form onSubmit={event => void sendInquiry(event)} className="studio-panel mt-4 space-y-4 p-6 sm:p-7">
          <div><p className="kicker">GET IN TOUCH</p><h2 className="mt-2 text-xl font-semibold">Arrange a viewing</h2><p className="mt-2 text-xs leading-5 text-muted">Your enquiry goes directly to the listing agency.</p></div>
          <label className="form-label">Your name<Input className="mt-2" name="name" defaultValue={user?.full_name ?? ''} minLength={2} required/></label>
          <label className="form-label">Email address<Input className="mt-2" name="email" type="email" defaultValue={user?.email ?? ''} required/></label>
          <label className="form-label">Phone (optional)<Input className="mt-2" name="phone" type="tel"/></label>
          <label className="form-label">Your message<textarea name="message" className="field mt-2 min-h-27" defaultValue="I'm interested in this property. Could we arrange a viewing?"/></label>
          {error && <p role="alert" className="error-note">{error}</p>}
          {sent && <p role="status" className="success-note"><Check size={16}/>Enquiry sent to the agency.</p>}
          <Button disabled={!user || sending || sent} type="submit" className="w-full !rounded-md">{sending ? 'Sending…' : sent ? 'Message sent' : 'Send enquiry'} <ArrowRight size={16}/></Button>
        </form>
        <form onSubmit={event => void requestViewing(event)} className="studio-panel mt-4 space-y-4 p-6 sm:p-7">
          <div><p className="kicker">VISIT IN PERSON</p><h2 className="mt-2 text-xl font-semibold">Request a viewing time</h2>
            <p className="mt-2 text-xs leading-5 text-muted">Suggest a time within the next 90 days. This is a request, not a confirmed booking.</p></div>
          <label className="form-label">Your name<Input className="mt-2" name="contact_name" defaultValue={user?.full_name ?? ''} minLength={2} maxLength={160} required/></label>
          <label className="form-label">Contact number<Input className="mt-2" name="contact_phone" type="tel" minLength={7} maxLength={40} required/></label>
          <label className="form-label">Preferred date and time<Input className="mt-2" name="preferred_at" type="datetime-local" required/></label>
          <label className="form-label">Message (optional)<textarea className="field mt-2 min-h-24" maxLength={1000} name="note" placeholder="Any accessibility needs or questions?"/></label>
          {viewingSent && <p role="status" className="success-note">Viewing request sent. The agency must confirm.</p>}
          <Button type="submit" className="w-full" disabled={!user || viewingBusy || viewingSent}>{viewingBusy ? 'Sending request…' : viewingSent ? 'Request sent' : 'Request appointment'} <ArrowRight size={15}/></Button>
        </form>
      </aside>
    </div>

    {galleryOpen && photos.length > 0 && <div role="dialog" aria-modal="true" aria-label="Property photo gallery" className="fixed inset-0 z-50 flex flex-col bg-[#151d19]/98 text-white">
      <div className="flex items-center justify-between p-5"><span className="text-xs font-semibold tabular-nums">{activePhoto + 1} / {photos.length}</span>
        <button type="button" className="rounded-full p-2 hover:bg-white/10" onClick={() => setGalleryOpen(false)} aria-label="Close gallery"><X size={24}/></button></div>
      <div className="flex min-h-0 flex-1 items-center justify-between gap-3 px-3 sm:px-10">
        <button type="button" aria-label="Previous photograph" onClick={() => setActivePhoto(value => (value + photos.length - 1) % photos.length)} className="rounded-full p-3 hover:bg-white/10"><ChevronLeft size={24}/></button>
        <div className="h-full max-h-[80vh] w-full max-w-5xl"><PropertyImage property={property} photoIndex={activePhoto} thumbnail={false} className="h-full w-full object-contain"/></div>
        <button type="button" aria-label="Next photograph" onClick={() => setActivePhoto(value => (value + 1) % photos.length)} className="rounded-full p-3 hover:bg-white/10"><ChevronRight size={24}/></button>
      </div>
      <div className="mx-auto max-w-xl p-5 text-center text-sm text-[#bec9be]">{photos[activePhoto]?.alt_text || property.title}</div>
    </div>}
  </main>;
}
