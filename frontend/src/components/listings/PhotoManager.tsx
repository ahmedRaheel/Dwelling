import { useRef, useState } from 'react';
import { ArrowDown, ArrowUp, Camera, Check, ImagePlus, LoaderCircle, Star, Trash2, Upload } from 'lucide-react';
import { api } from '@/api/client';
import type { Property, PropertyPhoto } from '@/api/types';
import { errorMessage } from '@/lib/utils';
import { PropertyImage } from './PropertyImage';

type Props = { property: Property; onChanged: () => Promise<void> };
const LIMIT = 24;
const MAX_BYTES = 12 * 1024 * 1024;

export function PhotoManager({ property, onChanged }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const cameraInput = useRef<HTMLInputElement>(null);
  const floorplanInput = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState('');
  const [editingAlt, setEditingAlt] = useState<string | null>(null);
  const [altDraft, setAltDraft] = useState('');
  const pictures = [...property.photos].sort((a, b) => a.position - b.position);
  const base = `/listings/${property.id}/photos`;

  async function upload(files: FileList | null, category: 'gallery' | 'floorplan' = 'gallery') {
    if (!files?.length) return;
    const selected = Array.from(files);
    if (selected.length + pictures.length > LIMIT) {
      setError(`A listing can include up to ${LIMIT} photographs.`);
      return;
    }
    const invalid = selected.find(file => !['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > MAX_BYTES);
    if (invalid) { setError('Use JPEG, PNG or WebP files up to 12 MB each.'); return; }

    setError(''); setBusy(true);
    try {
      for (const [index, file] of selected.entries()) {
        setProgress(`Uploading ${index + 1} of ${selected.length}: ${file.name}`);
        const body = new FormData();
        body.append('file', file);
        body.append('category', category);
        body.append('alt_text', file.name.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' '));
        await api<PropertyPhoto>(base, { method: 'POST', body });
      }
      await onChanged();
    } catch (cause) { setError(errorMessage(cause)); await onChanged(); }
    finally { setBusy(false); setProgress(''); if (input.current) input.current.value = ''; }
  }

  async function changePhoto(photo: PropertyPhoto, action: 'cover' | 'remove' | 'alt') {
    if (action === 'remove' && !window.confirm('Remove this photograph from the listing?')) return;
    setBusy(true); setError('');
    try {
      if (action === 'remove') await api(`${base}/${photo.id}`, { method: 'DELETE' });
      else await api(`${base}/${photo.id}`, { method: 'PATCH', body: JSON.stringify(
        action === 'cover' ? { is_cover: true } : { alt_text: altDraft },
      ) });
      if (action === 'alt') setEditingAlt(null);
      await onChanged();
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  }

  async function move(photo: PropertyPhoto, delta: number) {
    const reordered = pictures.map(item => item.id);
    const index = reordered.indexOf(photo.id);
    const target = index + delta;
    if (target < 0 || target >= reordered.length) return;
    [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
    setBusy(true); setError('');
    try {
      await api(`${base}/order`, { method: 'PUT', body: JSON.stringify({ photo_ids: reordered }) });
      await onChanged();
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  }

  return <section className="space-y-6">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div><p className="kicker">Photography</p><h2 className="mt-2 text-2xl font-semibold tracking-tight">Let the property speak for itself.</h2>
        <p className="mt-2 text-sm text-muted">Add the exterior, living spaces, kitchen, bedrooms and a floor plan. Real photos build trust.</p></div>
      <p className="text-sm font-medium tabular-nums text-muted">{pictures.length} / {LIMIT} images</p>
    </div>
    <input ref={input} type="file" multiple accept="image/jpeg,image/png,image/webp" className="sr-only" onChange={event => void upload(event.target.files)}/>
    <input ref={floorplanInput} type="file" multiple accept="image/jpeg,image/png,image/webp" className="sr-only" onChange={event => void upload(event.target.files, 'floorplan')}/>
    <input ref={cameraInput} type="file" accept="image/jpeg,image/png,image/webp" capture="environment" className="sr-only" onChange={event => void upload(event.target.files)}/>
    <div role="group" aria-label="Property photo upload area"
      onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); if (!busy) void upload(event.dataTransfer.files); }}
      className="upload-target flex w-full flex-col items-center justify-center gap-3 rounded-lg px-6 py-10 text-center transition-colors">
      <span className="rounded-full bg-[#f0ede4] p-4 text-ink"><ImagePlus size={25} strokeWidth={1.5}/></span>
      <span className="text-base font-semibold">Choose property photographs</span>
      <span className="text-xs text-muted">JPEG, PNG, WebP · 12 MB each · automatically optimized</span>
      <div className="flex flex-wrap justify-center gap-3">
        <button type="button" disabled={busy || pictures.length >= LIMIT} onClick={() => input.current?.click()} className="mini-action !border-accent !text-accent"><Upload size={15}/>Browse / drag files</button>
        <button type="button" disabled={busy || pictures.length >= LIMIT} onClick={() => cameraInput.current?.click()} className="mini-action"><Camera size={15}/>Use camera</button>
        <button type="button" disabled={busy || pictures.length >= LIMIT} onClick={() => floorplanInput.current?.click()} className="mini-action">Add floor plan image</button>
      </div>
    </div>
    {progress && <p role="status" className="inline-flex items-center gap-2 text-sm text-muted"><LoaderCircle size={16} className="animate-spin"/>{progress}</p>}
    {error && <p role="alert" className="error-note">{error}</p>}
    {pictures.length > 0 && <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {pictures.map((photo, index) => <div key={photo.id} className="overflow-hidden rounded-lg border border-line bg-white">
        <div className="relative aspect-[5/3] overflow-hidden bg-[#e6e5dd]">
          <PropertyImage property={property} photoId={photo.id} className="h-full w-full object-cover"/>
          {photo.category === 'floorplan' && <span className="absolute start-3 top-3 bg-white px-2 py-1 text-xs font-medium">Floor plan</span>}
          {photo.is_cover && <span className="absolute start-3 top-3 inline-flex items-center gap-1 rounded bg-ink px-2.5 py-1 text-xs font-medium text-white"><Star size={12} fill="currentColor"/>Cover</span>}
        </div>
        <div className="space-y-3 p-3">
          {editingAlt === photo.id ? <div className="flex gap-2"><input className="field min-w-0 flex-1" maxLength={180} aria-label="Image description" value={altDraft} onChange={e => setAltDraft(e.target.value)}/>
            <button type="button" className="icon-action" disabled={busy} aria-label="Save description" onClick={() => void changePhoto(photo, 'alt')}><Check size={17}/></button></div> :
            <button className="line-clamp-1 w-full text-start text-xs text-muted hover:text-ink" onClick={() => { setEditingAlt(photo.id); setAltDraft(photo.alt_text); }} type="button">{photo.alt_text || 'Add accessible description'}</button>}
          <div className="flex items-center gap-1">
            <button type="button" className="icon-action" disabled={busy || index === 0} onClick={() => void move(photo, -1)} aria-label="Move earlier"><ArrowUp size={16}/></button>
            <button type="button" className="icon-action" disabled={busy || index === pictures.length - 1} onClick={() => void move(photo, 1)} aria-label="Move later"><ArrowDown size={16}/></button>
            {!photo.is_cover && photo.category === 'gallery' && <button type="button" className="ms-auto inline-flex items-center gap-1 rounded px-2 py-2 text-xs font-medium hover:bg-stone-100" disabled={busy} onClick={() => void changePhoto(photo, 'cover')}><Camera size={14}/>Make cover</button>}
            <button type="button" className="icon-action ms-auto text-[#a64f3c]" disabled={busy} onClick={() => void changePhoto(photo, 'remove')} aria-label="Delete image"><Trash2 size={16}/></button>
          </div>
        </div>
      </div>)}
    </div>}
    <p className="text-xs leading-5 text-muted"><Camera size={13} className="me-1 inline"/>For privacy, photo metadata is removed during upload. Make sure you own or have permission to publish every image.</p>
  </section>;
}
