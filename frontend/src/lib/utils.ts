import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }
export function currency(amount: string | number, code = 'PKR', locale = 'en-PK') {
  return new Intl.NumberFormat(locale === 'ur' ? 'ur-PK' : 'en-PK', {
    style: 'currency', currency: code, maximumFractionDigits: 0,
  }).format(Number(amount));
}
export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong';
}
