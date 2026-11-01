import { useMemo, useState } from 'react';
import { Calculator, Ruler, ShieldAlert } from 'lucide-react';

const units: { id: string; label: string; sqft: number }[] = [
  { id: 'sqft', label: 'Square feet', sqft: 1 },
  { id: 'sqm', label: 'Square metres', sqft: 10.7639104167 },
  { id: 'marla225', label: 'Marla (225 sq ft)', sqft: 225 },
  { id: 'marla250', label: 'Marla (250 sq ft)', sqft: 250 },
  { id: 'marla272', label: 'Marla (272.25 sq ft)', sqft: 272.25 },
  { id: 'kanal', label: 'Kanal (20 × 272.25 sq ft)', sqft: 5445 },
];

/** Mortgage amortization illustration only. No bank rates or offers are implied. */
export function BuyerTools() {
  const [price, setPrice] = useState(20000000);
  const [downPayment, setDownPayment] = useState(30);
  const [annualRate, setAnnualRate] = useState(15);
  const [years, setYears] = useState(20);
  const [area, setArea] = useState(120);
  const [unit, setUnit] = useState('sqft');
  const [target, setTarget] = useState('marla272');
  const loan = Math.max(0, price * (1 - downPayment / 100));
  const months = Math.max(1, years * 12);
  const monthlyRate = annualRate / 1200;
  const monthly = monthlyRate === 0 ? loan / months : loan * monthlyRate / (1 - Math.pow(1 + monthlyRate, -months));
  const converted = useMemo(() => {
    const from = units.find(option => option.id === unit)?.sqft ?? 1;
    const to = units.find(option => option.id === target)?.sqft ?? 1;
    return area * from / to;
  }, [area, unit, target]);
  return <main className="page-shell pb-24 pt-12">
    <p className="kicker">THE BUYER'S TOOLKIT</p><h1 className="editorial-title mt-3 text-[clamp(2.3rem,5vw,4rem)]">The numbers behind a move.</h1>
    <p className="mt-4 max-w-2xl text-sm leading-7 text-muted">Practical calculations for comparing properties. Transparent assumptions, no hidden lender recommendations.</p>
    <div className="mt-10 grid gap-6 lg:grid-cols-2">
      <section className="studio-panel p-7 sm:p-9"><div className="flex items-center gap-2"><Calculator size={19} className="text-accent"/><h2 className="studio-heading">Home financing estimate</h2></div>
        <p className="mt-3 text-xs leading-6 text-muted">Illustrative fixed-rate amortization, not a bank quote or eligibility decision.</p>
        <div className="mt-7 grid gap-5 sm:grid-cols-2">
          <label className="form-label">Property price (PKR)<input className="field mt-2" type="number" min="1" value={price} onChange={event => setPrice(Math.max(1, Number(event.target.value)))}/></label>
          <label className="form-label">Down payment (%)<input className="field mt-2" type="number" min="0" max="100" value={downPayment} onChange={event => setDownPayment(Math.min(100, Math.max(0, Number(event.target.value))))}/></label>
          <label className="form-label">Annual rate (%)<input className="field mt-2" type="number" min="0" max="100" step="0.1" value={annualRate} onChange={event => setAnnualRate(Math.min(100, Math.max(0, Number(event.target.value))))}/></label>
          <label className="form-label">Term (years)<input className="field mt-2" type="number" min="1" max="40" value={years} onChange={event => setYears(Math.min(40, Math.max(1, Number(event.target.value))))}/></label>
        </div>
        <div className="mt-8 border-t border-line pt-6"><p className="kicker">ILLUSTRATIVE MONTHLY PAYMENT</p><p className="mt-3 text-3xl font-semibold tabular-nums">PKR {Math.round(monthly).toLocaleString('en-PK')}</p><p className="mt-3 text-sm text-muted">Loan principal PKR {Math.round(loan).toLocaleString('en-PK')} · Interest PKR {Math.round(monthly * months - loan).toLocaleString('en-PK')} over {years} years.</p></div>
      </section>
      <section className="studio-panel p-7 sm:p-9"><div className="flex items-center gap-2"><Ruler size={19} className="text-accent"/><h2 className="studio-heading">Land area converter</h2></div>
        <p className="mt-3 text-xs leading-6 text-muted">Pakistani marla sizes vary between societies and regions. Choose the convention shown on your property documents.</p>
        <div className="mt-7 grid gap-5 sm:grid-cols-2">
          <label className="form-label">Area<input className="field mt-2" type="number" min="0" step="any" value={area} onChange={event => setArea(Math.max(0, Number(event.target.value)))}/></label>
          <label className="form-label">Original unit<select className="field mt-2" value={unit} onChange={event => setUnit(event.target.value)}>{units.map(option => <option key={option.id} value={option.id}>{option.label}</option>)}</select></label>
          <label className="form-label sm:col-span-2">Convert to<select className="field mt-2" value={target} onChange={event => setTarget(event.target.value)}>{units.map(option => <option key={option.id} value={option.id}>{option.label}</option>)}</select></label>
        </div>
        <div className="mt-8 border-t border-line pt-6"><p className="kicker">CONVERTED AREA</p><p className="mt-3 text-3xl font-semibold tabular-nums">{converted.toLocaleString('en-PK', { maximumFractionDigits: 3 })}</p><p className="mt-3 text-xs text-muted">{units.find(option => option.id === target)?.label}</p></div>
      </section>
    </div>
    <p className="mt-6 flex items-start gap-2 text-xs leading-6 text-muted"><ShieldAlert size={17} className="mt-0.5 shrink-0"/>Rates, taxes, bank fees, insurance, floating-rate changes, eligibility, and local transfer costs are not included. Confirm measurements and financing terms with qualified professionals.</p>
  </main>;
}
