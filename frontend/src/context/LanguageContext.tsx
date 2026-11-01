import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

type Language = 'en' | 'ur';
const dict = {
  en: {
    marketplace: 'Explore properties', broker: 'Broker workspace', customer: 'My dashboard',
    signIn: 'Sign in', signOut: 'Sign out', getStarted: 'Get started',
    heroEyebrow: 'INTELLIGENT PROPERTY DISCOVERY',
    heroTitle: 'Find a place that', heroAccent: 'feels like yours.',
    heroDescription: 'From a first apartment to a new business address. Explore verified listings, useful insights, and thoughtful matches.',
    search: 'Search properties', city: 'City or location', propertyType: 'Property type',
    allTypes: 'All property types', allPurposes: 'Sale & rent', sale: 'Buy', rent: 'Rent',
    price: 'Price', area: 'Area', beds: 'Beds', baths: 'Baths', viewDetails: 'View listing',
    explore: 'Explore the collection', listingResults: 'Available listings',
    inquiry: 'Send inquiry', message: 'Message', contactName: 'Your name',
    contactEmail: 'Email address', contactPhone: 'Phone number', send: 'Send message',
    valuation: 'AI asking-price estimate', forecast: 'Rental outlook',
    loginRequired: 'Sign in to continue', save: 'Save property',
    recommendations: 'Recommended for you', preferences: 'My preferences',
    leadMatches: 'AI lead matches', listings: 'My listings', leads: 'Leads',
    insights: 'Market insights', addListing: 'Add listing', noResults: 'No listings found yet.',
    insufficient: 'Not enough verified market data yet. No estimate will be invented.',
    monthly: '/ month', loading: 'Loading…',
  },
  ur: {
    marketplace: 'جائیدادیں تلاش کریں', broker: 'بروکر ورک اسپیس', customer: 'میرا ڈیش بورڈ',
    signIn: 'سائن اِن', signOut: 'سائن آؤٹ', getStarted: 'شروع کریں',
    heroEyebrow: 'ذہین جائیداد کی تلاش', heroTitle: 'ایسی جگہ تلاش کریں', heroAccent: 'جو آپ کی ہو۔',
    heroDescription: 'اپارٹمنٹ، گھر، پلاٹ، پورشن یا کاروباری جگہ — موزوں پراپرٹی، مفید معلومات اور ذہین سفارشات ایک ہی جگہ۔',
    search: 'جائیداد تلاش کریں', city: 'شہر یا علاقہ', propertyType: 'جائیداد کی قسم',
    allTypes: 'تمام اقسام', allPurposes: 'خرید و کرایہ', sale: 'خریدیں', rent: 'کرایہ',
    price: 'قیمت', area: 'رقبہ', beds: 'کمرے', baths: 'باتھ روم', viewDetails: 'تفصیل دیکھیں',
    explore: 'موجودہ جائیدادیں', listingResults: 'دستیاب جائیدادیں',
    inquiry: 'رابطہ کریں', message: 'پیغام', contactName: 'آپ کا نام',
    contactEmail: 'ای میل', contactPhone: 'فون نمبر', send: 'پیغام بھیجیں',
    valuation: 'اے آئی کی متوقع قیمت', forecast: 'مستقبل کے کرایے کا اندازہ',
    loginRequired: 'آگے بڑھنے کے لیے سائن اِن کریں', save: 'محفوظ کریں',
    recommendations: 'آپ کے لیے سفارشات', preferences: 'میری ترجیحات',
    leadMatches: 'ممکنہ خریداروں کا ملاپ', listings: 'میری جائیدادیں', leads: 'رابطے',
    insights: 'مارکیٹ کی معلومات', addListing: 'جائیداد شامل کریں', noResults: 'فی الحال کوئی جائیداد نہیں ملی۔',
    insufficient: 'مصدقہ معلومات ناکافی ہیں، اس لیے فرضی تخمینہ نہیں دیا جائے گا۔',
    monthly: '/ ماہ', loading: 'لوڈ ہو رہا ہے…',
  },
} as const;
type Key = keyof typeof dict.en;
type LanguageContextValue = { language: Language; setLanguage: (language: Language) => void; t: (key: Key) => string };
const Context = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(() => localStorage.getItem('proptech_lang') === 'ur' ? 'ur' : 'en');
  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = language === 'ur' ? 'rtl' : 'ltr';
    localStorage.setItem('proptech_lang', language);
  }, [language]);
  const value = useMemo(() => ({ language, setLanguage, t: (key: Key) => dict[language][key] }), [language]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useLanguage() {
  const context = useContext(Context);
  if (!context) throw new Error('LanguageProvider missing');
  return context;
}
