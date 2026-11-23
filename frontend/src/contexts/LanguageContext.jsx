import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import translations from '../translations';

const LanguageContext = createContext(null);

const SUPPORTED_LANGUAGES = [
  { code: 'en', label: 'English', flag: '🇬🇧' },
  { code: 'fr', label: 'Français', flag: '🇫🇷' },
  { code: 'de', label: 'Deutsch', flag: '🇩🇪' },
  { code: 'nl', label: 'Nederlands', flag: '🇳🇱' },
  { code: 'es', label: 'Español', flag: '🇪🇸' },
];

function detectBrowserLanguage() {
  const browserLang = navigator.language || navigator.userLanguage || 'en';
  const shortCode = browserLang.split('-')[0].toLowerCase();
  const supported = SUPPORTED_LANGUAGES.map(l => l.code);
  return supported.includes(shortCode) ? shortCode : 'en';
}

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => {
    const saved = localStorage.getItem('app_language');
    return saved || detectBrowserLanguage();
  });

  useEffect(() => {
    localStorage.setItem('app_language', language);
  }, [language]);

  const t = useCallback((key) => {
    const langData = translations[language] || translations.en;
    return langData[key] || translations.en[key] || key;
  }, [language]);

  const value = useMemo(() => ({
    language,
    setLanguage,
    t,
    languages: SUPPORTED_LANGUAGES
  }), [language, setLanguage, t]);

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}
