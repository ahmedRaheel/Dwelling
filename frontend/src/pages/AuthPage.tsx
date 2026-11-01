import { useState, type FormEvent } from 'react';
import { ArrowRight, KeyRound, ShieldCheck } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/context/AuthContext';
import { useLanguage } from '@/context/LanguageContext';
import { errorMessage } from '@/lib/utils';

type Mode = 'login' | 'customer' | 'agency';
const modes: { id: Mode; title: string }[] = [
  { id: 'login', title: 'Sign in' },
  { id: 'customer', title: 'Home seeker' },
  { id: 'agency', title: 'Broker / owner' },
];

export function AuthPage() {
  const [mode, setMode] = useState<Mode>('login');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const { login, registerCustomer, registerAgency, user } = useAuth();
  const { language } = useLanguage();
  const navigate = useNavigate();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setPending(true);
    const form = new FormData(event.currentTarget);
    const value = (name: string) => String(form.get(name) ?? '').trim();
    try {
      if (mode === 'login') await login({ tenant_slug: value('tenant_slug'), email: value('email'), password: value('password') });
      if (mode === 'customer') await registerCustomer({ tenant_slug: value('tenant_slug'), full_name: value('full_name'), email: value('email'), password: value('password') });
      if (mode === 'agency') await registerAgency({ agency_name: value('agency_name'), slug: value('slug'), full_name: value('full_name'), email: value('email'), password: value('password') });
      navigate('/');
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setPending(false); }
  }

  if (user) return <main className="page-shell py-24 text-center"><h1 className="editorial-title text-4xl">You're already signed in.</h1>
    <Button className="mt-6" asChild><Link to={user.role === 'customer' ? '/customer' : '/broker'}>Go to your workspace <ArrowRight size={16}/></Link></Button></main>;

  return <main className="page-shell grid min-h-[80vh] gap-12 py-16 lg:grid-cols-[.92fr_1.08fr] lg:items-center lg:gap-24">
    <section><p className="kicker flex items-center gap-3"><span className="h-px w-8 bg-accent"/>A MORE PERSONAL WAY TO FIND PROPERTY</p>
      <h1 className="editorial-title mt-7 text-[clamp(3rem,5vw,5.2rem)]">The next chapter <em className="text-accent">starts here.</em></h1>
      <p className="mt-6 max-w-md text-[15px] leading-8 text-muted">{language === 'ur' ? 'اپنی پسندیدہ جائیدادیں محفوظ کریں، ایجنٹس سے رابطہ کریں یا اپنے کاروبار کے لیے بہترین اشتہارات بنائیں۔' : 'Build your property shortlist, speak to agents, or create well-presented advertisements for your real estate business.'}</p>
      <div className="mt-10 flex items-center gap-3 border-t border-line pt-6 text-sm text-muted"><ShieldCheck size={22} strokeWidth={1.5} className="text-accent"/>Agency workspaces are isolated at the database level.</div>
      <div className="mt-10 hidden max-w-sm border-s-2 border-accent ps-6 lg:block"><p className="font-editorial text-2xl italic leading-8">“The best property decisions begin with clear information.”</p><p className="kicker mt-4">THE DWELLING APPROACH</p></div>
    </section>
    <div className="studio-panel w-full p-6 sm:p-9 lg:max-w-lg lg:justify-self-end">
      <div className="mb-8 flex flex-wrap gap-2 border-b border-line pb-4" role="tablist" aria-label="Account type">{modes.map(item => <button key={item.id} type="button" role="tab" aria-selected={mode === item.id}
        onClick={() => { setMode(item.id); setError(''); }} className={`px-3 py-2 text-xs font-semibold ${mode === item.id ? 'bg-ink text-white' : 'text-muted hover:text-ink'}`}>{item.title}</button>)}</div>
      <div className="mb-7"><p className="kicker">{mode === 'login' ? 'WELCOME BACK' : 'JOIN DWELLING'}</p>
        <h2 className="studio-heading mt-3">{mode === 'agency' ? 'Open a property workspace.' : mode === 'customer' ? 'Find your place.' : 'Sign in to continue.'}</h2>
        <p className="mt-2 text-xs text-muted">{mode === 'agency' ? 'For property owners, brokers and agency teams.' : 'Sign in with the agency workspace where your account was registered.'}</p></div>
      <form className="space-y-4" onSubmit={event => void submit(event)}>
        {mode === 'agency' && <><label className="form-label">Agency or business name<Input className="mt-2" name="agency_name" required minLength={2} placeholder="Harbour Realty"/></label>
          <label className="form-label">Workspace slug<Input className="mt-2" name="slug" pattern="[a-z0-9][a-z0-9-]{2,49}" required placeholder="harbour-realty"/></label></>}
        {mode !== 'agency' && <label className="form-label">Workspace slug<Input className="mt-2" name="tenant_slug" required placeholder="harbour-realty"/></label>}
        {mode !== 'login' && <label className="form-label">Full name<Input className="mt-2" name="full_name" minLength={2} required placeholder="Your name"/></label>}
        <label className="form-label">Email address<Input className="mt-2" name="email" autoComplete="email" type="email" required placeholder="you@example.com"/></label>
        <label className="form-label">Password<Input className="mt-2" name="password" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required minLength={mode === 'login' ? 1 : 12} placeholder={mode === 'login' ? 'Your password' : 'At least 12 characters'}/></label>
        {error && <p role="alert" className="error-note">{error}</p>}
        <Button type="submit" disabled={pending} className="mt-2 w-full">{pending ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'} <ArrowRight size={16}/></Button>
      </form>
      <p className="mt-7 flex items-center justify-center gap-2 text-xs text-muted"><KeyRound size={14}/>Your information stays within your workspace</p>
    </div>
  </main>;
}
