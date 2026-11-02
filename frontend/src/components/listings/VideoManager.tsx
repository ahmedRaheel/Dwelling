import { useCallback, useEffect, useRef, useState } from 'react';
import { Film, LoaderCircle, Trash2, UploadCloud } from 'lucide-react';
import { api, apiBlob } from '@/api/client';
import type { Property } from '@/api/types';
import { errorMessage } from '@/lib/utils';

type VideoInfo = { available: boolean; byte_size: number | null; url: string | null };

export function VideoManager({ property }: { property: Property }) {
  const filePicker = useRef<HTMLInputElement>(null);
  const [info, setInfo] = useState<VideoInfo | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const path = `/listings/${property.id}/video`;

  const reload = useCallback(async () => {
    setInfo(await api<VideoInfo>(path));
  }, [path]);

  useEffect(() => { void reload().catch(cause => setError(errorMessage(cause))); }, [reload]);
  useEffect(() => {
    if (!info?.available || !info.url) { setPreview(null); return; }
    if (property.status === 'published') {
      setPreview(info.url);
      return;
    }
    let active = true;
    let url: string | undefined;
    void apiBlob(path + '/file').then(data => {
      url = URL.createObjectURL(data);
      if (active) setPreview(url);
      else URL.revokeObjectURL(url);
    }).catch(cause => { if (active) setError(errorMessage(cause)); });
    return () => { active = false; if (url) URL.revokeObjectURL(url); };
  }, [info?.available, info?.url, property.status, path]);

  async function upload(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    if (!['video/mp4', 'video/webm'].includes(file.type) || file.size > 80 * 1024 * 1024) {
      setError('Use an MP4 or WebM video of 80 MB or less.');
      return;
    }
    setBusy(true); setError('');
    try {
      const body = new FormData();
      body.set('file', file);
      await api(path, { method: 'PUT', body });
      await reload();
    } catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); if (filePicker.current) filePicker.current.value = ''; }
  }

  async function remove() {
    if (!window.confirm('Remove this property video?')) return;
    setBusy(true); setError('');
    try { await api(path, { method: 'DELETE' }); await reload(); }
    catch (cause) { setError(errorMessage(cause)); }
    finally { setBusy(false); }
  }

  return <section className="mt-10 border-t border-line pt-8">
    <div className="mb-5 flex items-start justify-between gap-4">
      <div><p className="kicker">VIDEO TOUR</p>
        <h3 className="mt-2 text-xl font-semibold tracking-tight">Show how the property feels.</h3>
        <p className="mt-2 text-sm text-muted">One MP4 or WebM video, up to 80 MB. Private until your advertisement is published.</p>
      </div><Film size={24} className="shrink-0 text-accent" strokeWidth={1.5}/>
    </div>
    {preview && <video controls playsInline preload="metadata" className="mb-5 aspect-video w-full rounded-md bg-ink" src={preview} aria-label="Property video tour"/>}
    <input ref={filePicker} type="file" accept="video/mp4,video/webm" className="sr-only" onChange={event => void upload(event.target.files)}/>
    <div className="flex flex-wrap items-center gap-3">
      <button type="button" className="mini-action" disabled={busy} onClick={() => filePicker.current?.click()}>
        {busy ? <LoaderCircle size={16} className="animate-spin"/> : <UploadCloud size={16}/>}
        {info?.available ? 'Replace video' : 'Upload property video'}
      </button>
      {info?.available && <button type="button" className="mini-action text-[#a64f3c]" disabled={busy} onClick={() => void remove()}><Trash2 size={15}/>Remove</button>}
      {info?.byte_size && <span className="text-xs text-muted">{(info.byte_size / 1024 / 1024).toFixed(1)} MB</span>}
    </div>
    {error && <p className="error-note mt-4" role="alert">{error}</p>}
  </section>;
}
