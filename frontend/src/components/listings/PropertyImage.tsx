import { useEffect, useState } from 'react';
import { Image as ImageIcon } from 'lucide-react';
import { apiBlob, photoPath } from '@/api/client';
import type { Property } from '@/api/types';
import { cn } from '@/lib/utils';

type Props = {
  property: Property;
  className?: string;
  alt?: string;
  photoIndex?: number;
  photoId?: string;
  thumbnail?: boolean;
};

/** Draft images need a bearer token; published images can be served directly. */
export function PropertyImage({ property, className, alt, photoIndex = 0, photoId, thumbnail = true }: Props) {
  const ordered = [...(property.photos ?? [])].sort((a, b) => a.position - b.position);
  const gallery = ordered.filter(photo => photo.category === 'gallery');
  const cover = gallery.find(photo => photo.is_cover);
  const photos = cover ? [cover, ...gallery.filter(photo => photo.id !== cover.id)] : gallery;
  const selected = photoId ? ordered.find(photo => photo.id === photoId) : photos[photoIndex];
  const selectedUrl = selected ? (thumbnail ? selected.thumbnail_url : selected.url) : property.photo_url;
  const [url, setUrl] = useState<string | null>(property.status === 'published' ? selectedUrl ?? null : null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
    if (!selectedUrl) { setUrl(null); return; }
    if (property.status === 'published' || !selected) { setUrl(selectedUrl); return; }
    let current = true;
    let objectUrl: string | null = null;
    setUrl(null);
    void apiBlob(photoPath(selectedUrl)).then(blob => {
      if (current) { objectUrl = URL.createObjectURL(blob); setUrl(objectUrl); }
    }).catch(() => { if (current) setFailed(true); });
    return () => { current = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [selectedUrl, property.status, selected?.id]);

  if (!url || failed) {
    return <div className={cn('image-fallback flex items-center justify-center', className)} aria-label="No property photo">
      <div className="text-center"><ImageIcon size={27} strokeWidth={1.25} className="mx-auto opacity-50"/><span className="mt-2 block text-[11px] tracking-wide opacity-60">Photographs coming soon</span></div>
    </div>;
  }
  return <img src={url} alt={alt ?? selected?.alt_text ?? property.title} loading="lazy" onError={() => setFailed(true)} className={cn('h-full w-full object-cover', className)} />;
}
