import { useState, type FormEvent } from 'react';
import { ArrowRight, Building2, House, KeyRound, ShieldCheck, UserRound, Users } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/context/AuthContext';
import { errorMessage } from '@/lib/utils';

type AccountType = 'customer' | 'owner' | 'broker' | 'dealer' | 'agency';
type Mode = 'sign-in' | 'create-account';
const accountTypes: { id: AccountType; label: string; description: string; icon: typeof House }[] = [
  { id: 'customer', label: 'Home seeker', description: 'Discover, save and arrange viewings', icon: House },
  { id: 'owner', label: 'Property owner', description: 'Advertise property you own', icon: UserRound },
  { id: 'broker', label: 'Broker', description: 'Manage client properties and enquiries', icon: KeyRound },
  { id: 'dealer', label: 'Property dealer', description: 'Publish and manage your portfolio', icon: Building2 },
  { id: 'agency', label: 'Real estate agency', description: 'Create a workspace for your team', icon: Users },
];

export function AuthPage() {
  const [mode, setMode] = useState<Mode>('sign-in');
  const [accountType, setAccountType] = useState<AccountType>('customer');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [workspace, setWorkspace] = useState(localStorage.getItem('dwelling_workspace_slug') || '');
  const { login, registerCustomer, registerAgency, user } = useAuth();
  const navigate = useNavigate();
  const isProfessional = accountType !== 'customer';

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError('');
    const fields = new FormData(event.currentTarget);
    const value = (name: string) => String(fields.get(name) ?? '').trim();
    if (mode === 'create-account' && value('password') !== value('confirm_password')) {
      setError('Passwords do not match.');
      setPending(false);
      return;
    }
    try {
      if (mode === 'sign-in') {
        await login({ tenant_slug: value('tenant_slug'), email: value('email'), password: value('password') });
      } else if (accountType === 'customer') {
        await registerCustomer({ full_name: value('full_name'), email: value('email'), password: value('password') });
      } else {
        await registerAgency({
          agency_name: value('agency_name'), slug: value('slug'), account_type: accountType,
          full_name: value('full_name'), email: value('email'), password: value('password'),
        });
      }
      navigate(mode === 'create-account' && isProfessional ? '/broker' : mode === 'create-account' ? '/customer' : '/', { replace: true });
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  if (user) return <main className="page-shell py-24 text-center">
    <h1 className="editorial-title text-4xl">Welcome back.</h1>
    <p className="mt-4 text-sm text-muted">Your workspace is ready.</p>
    <Button className="mt-6" asChild><Link to={user.role === 'customer' ? '/customer' : '/broker'}>Go to workspace <ArrowRight size={16}/></Link></Button>
  </main>;

  return <main className="page-shell grid min-h-[80vh] gap-10 py-12 lg:grid-cols-[.9fr_1.1fr] lg:items-start lg:gap-20 lg:py-20">
    <section className="lg:sticky lg:top-32">
      <p className="kicker">YOUR PROPERTY JOURNEY, SIMPLIFIED</p>
      <h1 className="editorial-title mt-6 max-w-xl text-[clamp(3rem,5vw,5.4rem)]">A place for every <em className="text-accent">next move.</em></h1>
      <p className="mt-7 max-w-md text-[15px] leading-8 text-muted">Find a home, showcase a property or manage your real estate business. Everything starts with a workspace built around you.</p>
      <div className="mt-10 max-w-md space-y-5 border-t border-line pt-7 text-sm text-muted">
        <div className="flex items-start gap-3"><ShieldCheck size={20} className="mt-0.5 shrink-0 text-accent"/>Your unpublished listings stay private until you choose to publish.</div>
        <div className="flex items-start gap-3"><House size={20} className="mt-0.5 shrink-0 text-accent"/>Add genuine photography and video to tell the whole property story.</div>
      </div>
    </section>
    <section className="studio-panel w-full p-6 sm:p-9">
      <div className="flex gap-8 border-b border-line pb-4 text-sm font-semibold" role="tablist" aria-label="Account action">
        <button type="button" role="tab" aria-selected={mode === 'sign-in'} onClick={() => { setMode('sign-in'); setError(''); }} className={mode === 'sign-in' ? 'auth-tab-active' : 'auth-tab'}>Sign in</button>
        <button type="button" role="tab" aria-selected={mode === 'create-account'} onClick={() => { setMode('create-account'); setError(''); }} className={mode === 'create-account' ? 'auth-tab-active' : 'auth-tab'}>Create account</button>
      </div>
      <div className="mt-8 mb-7"><p className="kicker">{mode === 'sign-in' ? 'WELCOME BACK' : 'GET STARTED'}</p>
        <h2 className="studio-heading mt-3">{mode === 'sign-in' ? 'Sign in to Dwelling.' : 'How will you use Dwelling?'}</h2>
      </div>
      {mode === 'create-account' && <div className="mb-8 grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label="Account type">
        {accountTypes.map(item => { const Icon = item.icon; return <button key={item.id} type="button" role="radio" aria-checked={accountType === item.id}
          onClick={() => setAccountType(item.id)} className={`account-choice ${accountType === item.id ? 'account-choice-active' : ''}`}>
          <Icon size={20} strokeWidth={1.7}/><span className="block font-semibold">{item.label}</span><span className="block text-[11px] leading-5 text-muted">{item.description}</span>
        </button>; })}
      </div>}
      <form className="space-y-4" onSubmit={event => void submit(event)}>
        {mode === 'create-account' && isProfessional && <>
          <label className="form-label">{accountType === 'agency' ? 'Agency name' : accountType === 'owner' ? 'Your listing business name' : 'Trading / business name'}
            <Input className="mt-2" name="agency_name" required minLength={2} maxLength={160} placeholder="e.g. Riverside Properties"/></label>
          <label className="form-label">Workspace address <span className="text-muted font-normal">(used when signing in)</span>
            <Input className="mt-2" name="slug" pattern="[a-z0-9][a-z0-9-]{2,49}" required placeholder="riverside-properties"/>
          </label>
        </>}
        {mode === 'sign-in' && <label className="form-label">Workspace address
          <Input className="mt-2" name="tenant_slug" value={workspace} onChange={event => setWorkspace(event.target.value)} required placeholder="your-workspace"/>
          <span className="mt-1 block text-xs font-normal text-muted">Your workspace is saved on this device after registration. Keep it for signing in elsewhere.</span>
        </label>}
        {mode === 'create-account' && <label className="form-label">Your full name<Input className="mt-2" name="full_name" required minLength={2} maxLength={160} autoComplete="name" placeholder="First and last name"/></label>}
        <label className="form-label">Email address<Input className="mt-2" name="email" type="email" autoComplete="email" required placeholder="name@example.com"/></label>
        <label className="form-label">Password<Input className="mt-2" name="password" type="password" required minLength={mode === 'sign-in' ? 1 : 12} autoComplete={mode === 'sign-in' ? 'current-password' : 'new-password'} placeholder={mode === 'sign-in' ? 'Your password' : '12 characters minimum'}/></label>
        {mode === 'create-account' && <label className="form-label">Confirm password<Input className="mt-2" name="confirm_password" type="password" autoComplete="new-password" minLength={12} required placeholder="Enter password again"/></label>}
        {error && <p className="error-note" role="alert">{error}</p>}
        <Button type="submit" className="mt-2 w-full" disabled={pending}>{pending ? 'Please wait…' : mode === 'sign-in' ? 'Sign in' : 'Create account'} <ArrowRight size={16}/></Button>
      </form>
      <p className="mt-7 text-center text-xs text-muted">{mode === 'create-account' ? 'Your advertisements remain drafts until published.' : 'New to Dwelling?'}
        {mode === 'sign-in' && <button className="ms-2 font-semibold text-accent hover:underline" type="button" onClick={() => setMode('create-account')}>Create an account</button>}</p>
    </section>
  </main>;
}
