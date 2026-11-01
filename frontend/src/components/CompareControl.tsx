import { useEffect, useState } from 'react';
import { ArrowLeftRight, Check } from 'lucide-react';
import { Link } from 'react-router-dom';
import { comparisonIds, COMPARE_EVENT, toggleComparison } from '@/lib/compare';

export function CompareControl({ id, compact = false }: { id: string; compact?: boolean }) {
  const [ids, setIds] = useState<string[]>(comparisonIds);
  const [message, setMessage] = useState('');
  useEffect(() => {
    const refresh = () => setIds(comparisonIds());
    window.addEventListener(COMPARE_EVENT, refresh);
    return () => window.removeEventListener(COMPARE_EVENT, refresh);
  }, []);
  const selected = ids.includes(id);

  return <span className="inline-flex items-center gap-2">
    <button type="button" aria-pressed={selected} aria-label={selected ? 'Remove from comparison' : 'Add to comparison'}
      onClick={() => { try { toggleComparison(id); setMessage(''); } catch (error) { setMessage((error as Error).message); } }}
      className="mini-action"><ArrowLeftRight size={14}/>{!compact && (selected ? 'Remove' : 'Compare')}{selected && <Check size={13}/>}</button>
    {ids.length >= 2 && <Link to="/compare" className="text-xs font-semibold text-accent">Compare {ids.length}</Link>}
    {message && <span role="alert" className="text-xs text-[#a34e3d]">{message}</span>}
  </span>;
}
