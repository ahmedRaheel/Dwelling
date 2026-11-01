import { ArrowUpRight, Bath, BedDouble, MapPin, Ruler, Users } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Property } from '@/api/types';
import { PropertyImage } from '@/components/listings/PropertyImage';
import { CompareControl } from '@/components/CompareControl';
import { useLanguage } from '@/context/LanguageContext';
import { currency } from '@/lib/utils';

export function PropertyCard({ property, reason }: { property: Property; reason?: string }) {
  const { language, t } = useLanguage();
  return <article className="property-card group">
    <Link to={`/property/${property.id}`} className="block" aria-label={`View ${property.title}`}>
      <div className="relative aspect-[4/3] overflow-hidden bg-sand">
        <PropertyImage property={property} className="h-full w-full transition-transform duration-500 group-hover:scale-[1.025]"/>
        <div className="absolute start-4 top-4 flex gap-2"><span className="rounded-[2px] bg-white px-3 py-2 text-[11px] font-semibold tracking-wide text-ink">{property.purpose === 'sale' ? t('sale') : t('rent')}</span></div>
        {property.photos.filter(photo => photo.category === 'gallery').length > 1 && <span className="absolute bottom-4 end-4 rounded-[2px] bg-ink/85 px-2.5 py-1.5 text-xs tabular-nums text-white">01 / {property.photos.filter(photo => photo.category === 'gallery').length.toString().padStart(2, '0')}</span>}
      </div>
      <div className="pt-5"><div className="flex items-start justify-between gap-4"><div className="min-w-0"><p className="kicker">{property.kind.replaceAll('_', ' ')}</p>
        <h3 className="mt-2 line-clamp-2 text-[1.13rem] font-semibold leading-6 tracking-[-.02em] text-ink">{property.title}</h3></div><ArrowUpRight size={19} strokeWidth={1.5} className="shrink-0 text-accent transition-transform group-hover:translate-x-1 group-hover:-translate-y-1"/></div>
        <p className="mt-3 flex items-center gap-1.5 text-xs text-muted"><MapPin size={14}/>{[property.area_name, property.city].filter(Boolean).join(', ')}</p>
        <div className="mt-5 flex flex-wrap items-center gap-4 border-b border-line pb-4 text-xs text-muted"><span className="flex items-center gap-1.5"><Ruler size={15}/>{Number(property.area_sqft).toLocaleString()} sqft</span>
          {property.kind !== 'plot' && <span className="flex items-center gap-1.5"><BedDouble size={15}/>{property.bedrooms} beds</span>}
          {property.kind !== 'plot' && <span className="flex items-center gap-1.5"><Bath size={15}/>{property.bathrooms} baths</span>}
          {property.pg && <span className="flex items-center gap-1.5"><Users size={15}/>{property.pg.available_beds} beds free</span>}</div>
        <div className="mt-4 flex items-end justify-between gap-3"><div><p className="text-[11px] text-muted">{property.purpose === 'rent' ? 'Monthly asking rent' : 'Asking price'}</p><strong className="mt-1 block text-xl font-semibold tracking-tight tabular-nums text-ink">{currency(property.price, property.currency, language)}</strong></div>
          <span className="text-xs font-semibold text-accent">View details</span></div>
        {reason && <p className="mt-4 border-s-2 border-accent ps-3 text-xs text-muted">{reason}</p>}
      </div>
    </Link>
    <div className="mt-3 flex items-center justify-between border-t border-line pt-3"><CompareControl id={property.id}/>
      {property.ready_to_move && <span className="text-xs text-muted">Ready for possession</span>}
    </div>
  </article>;
}
