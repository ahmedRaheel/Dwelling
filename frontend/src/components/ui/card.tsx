import type { ComponentProps } from 'react';
import { cn } from '@/lib/utils';
export function Card({ className, ...props }: ComponentProps<'div'>) {
  return <div data-slot="card" className={cn('surface', className)} {...props} />;
}
export function CardHeader({ className, ...props }: ComponentProps<'div'>) {
  return <div data-slot="card-header" className={cn('p-5 pb-3', className)} {...props} />;
}
export function CardContent({ className, ...props }: ComponentProps<'div'>) {
  return <div data-slot="card-content" className={cn('p-5 pt-0', className)} {...props} />;
}
export function CardTitle({ className, ...props }: ComponentProps<'h3'>) {
  return <h3 data-slot="card-title" className={cn('text-lg font-semibold tracking-tight', className)} {...props} />;
}
