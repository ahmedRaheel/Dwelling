import { useEffect, useState } from 'react';
import { ArrowLeftRight, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '@/api/client';
import type { Property } from '@/api/types';
import { PropertyImage } from '@/components/listings/PropertyImage';
import { CompareControl } from '@/components/CompareControl';
import { comparisonIds, COMPARE_EVENT } from '@/lib/compare';
import { currency, errorMessage } from '@/lib/utils';

export function PropertyCompare() {
  const [ids, setIds] = useState(comparisonIds);
  const [properties, setProperties] = useState<Property[]>([]);
  const [error, setError] = useState('');
  useEffect(() => {
    const listen = () => setIds(comparisonIds());
    window.addEventListener(COMPARE_EVENT, listen);
    return () => window.removeEventListener(COMPARE_EVENT, listen);
  }, []);
  useEffect(() => {
    if (ids.length < 2) { setProperties([]); return; }
    let active = true;
    const query = new URLSearchParams();
    ids.forEach(id => query.append('ids', id));
    void api<Property[]>(`/discovery/compare?${query}`).then(items => { if (active) { setProperties(items); setError(''); } })
      .catch(cause => { if (active) setError(errorMessage(cause)); });
    return () => { active = false; };
  }, [ids]);
  const traits: { label: string; value: (property: Property) => string }[] = [
    { label: 'Price', value: item => currency(item.price, item.currency) },
    { label: 'Purpose', value: item => item.purpose === 'sale' ? 'For sale' : 'For rent' },
    { label: 'Type', value: item => item.kind.replaceAll('_', ' ') },
    { label: 'Location', value: item => [item.society, item.block, item.area_name, item.city].filter(Boolean).join(', ') },
    { label: 'Floor area', value: item => `${Number(item.area_sqft).toLocaleString()} sq ft` },
    { label: 'Bedrooms', value: item => String(item.bedrooms) },
    { label: 'Bathrooms', value: item => String(item.bathrooms) },
    { label: 'Possession', value: item => item.ready_to_move ? 'Ready' : 'Ask agent' },
    { label: 'Price flexibility', value: item => item.price_negotiable ? 'Negotiable' : 'Not advertised' },
    { label: 'Amenities', value: item => item.amenities.join(', ') || 'Not specified' },
  ];
  return <main className="page-shell pb-24 pt-12">
    <p className="kicker">THE DECISION DESK</p><h1 className="editorial-title mt-3 text-5xl">Compare with clarity.</h1>
    <p className="mt-3 max-w-xl text-sm leading-6 text-muted">A side-by-side look at up to four properties. Details come directly from their published advertisements.</p>
    {error && <p className="error-note mt-6" role="alert">{error}</p>}
    {properties.length < 2 ? <div className="empty-space mt-10"><ArrowLeftRight size={32}/><p className="mt-3 text-sm">Select at least two properties from the marketplace.</p><Link to="/" className="link-text mt-4 inline-flex gap-1 text-sm">Browse properties <ArrowRight size={15}/></Link></div> :
      <div className="mt-9 overflow-x-auto border border-line bg-white"><table className="w-full min-w-[800px] border-collapse text-start text-sm">
        <thead><tr><th className="w-36 border-b border-line p-4 text-start text-xs text-muted">Property</th>{properties.map(item => <th key={item.id} className="min-w-[195px] border-b border-s border-line p-4 text-start align-top font-normal">
          <Link to={`/property/${item.id}`}><PropertyImage property={item} className="h-32 w-full object-cover"/><strong className="mt-3 block line-clamp-2 text-sm">{item.title}</strong></Link><div className="mt-2"><CompareControl id={item.id} compact/></div>
        </th>)}</tr></thead>
        <tbody>{traits.map(trait => <tr key={trait.label}><th className="border-b border-line bg-[#f6f3ed] p-4 text-start text-xs font-medium text-muted">{trait.label}</th>{properties.map(item => <td key={item.id} className="border-b border-s border-line p-4 align-top">{trait.value(item)}</td>)}</tr>)}</tbody>
      </table></div>}
    <p className="mt-5 text-xs text-muted">Property information and asking prices are advertiser-submitted, not independently verified.</p>
  </main>;
}
