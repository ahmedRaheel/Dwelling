import { Globe2 } from 'lucide-react';
import { useLanguage } from '@/context/LanguageContext';
import { Button } from './ui/button';
export function LanguageToggle() {
  const { language, setLanguage } = useLanguage();
  return <Button size="sm" variant="ghost" aria-label="Switch between English and Urdu" onClick={() => setLanguage(language === 'en' ? 'ur' : 'en')}>
    <Globe2 size={15} /><span className="latin-num">{language === 'en' ? 'اردو' : 'English'}</span>
  </Button>;
}
