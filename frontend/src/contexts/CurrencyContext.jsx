import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';

const CurrencyContext = createContext(null);

const SUPPORTED_CURRENCIES = [
  { code: 'EUR', symbol: '\u20ac', name: 'Euro', flag: '\ud83c\uddea\ud83c\uddfa' },
  { code: 'GBP', symbol: '\u00a3', name: 'British Pound', flag: '\ud83c\uddec\ud83c\udde7' },
  { code: 'CHF', symbol: 'CHF', name: 'Swiss Franc', flag: '\ud83c\udde8\ud83c\udded' },
  { code: 'SEK', symbol: 'kr', name: 'Swedish Krona', flag: '\ud83c\uddf8\ud83c\uddea' },
  { code: 'DKK', symbol: 'kr', name: 'Danish Krone', flag: '\ud83c\udde9\ud83c\uddf0' },
  { code: 'NOK', symbol: 'kr', name: 'Norwegian Krone', flag: '\ud83c\uddf3\ud83c\uddf4' },
  { code: 'PLN', symbol: 'z\u0142', name: 'Polish Zloty', flag: '\ud83c\uddf5\ud83c\uddf1' },
  { code: 'CZK', symbol: 'K\u010d', name: 'Czech Koruna', flag: '\ud83c\udde8\ud83c\uddff' },
];

// Map browser locale → currency
const LOCALE_CURRENCY_MAP = {
  // Eurozone
  'de': 'EUR', 'fr': 'EUR', 'es': 'EUR', 'it': 'EUR', 'nl': 'EUR',
  'pt': 'EUR', 'el': 'EUR', 'fi': 'EUR', 'sk': 'EUR', 'sl': 'EUR',
  'et': 'EUR', 'lv': 'EUR', 'lt': 'EUR', 'mt': 'EUR', 'ga': 'EUR',
  'de-de': 'EUR', 'fr-fr': 'EUR', 'es-es': 'EUR', 'it-it': 'EUR',
  'nl-nl': 'EUR', 'pt-pt': 'EUR', 'de-at': 'EUR', 'fr-be': 'EUR',
  'nl-be': 'EUR', 'de-lu': 'EUR', 'fr-lu': 'EUR',
  // UK
  'en-gb': 'GBP',
  // Switzerland
  'de-ch': 'CHF', 'fr-ch': 'CHF', 'it-ch': 'CHF',
  // Nordics
  'sv': 'SEK', 'sv-se': 'SEK',
  'da': 'DKK', 'da-dk': 'DKK',
  'nb': 'NOK', 'nn': 'NOK', 'no': 'NOK', 'nb-no': 'NOK',
  // Eastern Europe
  'pl': 'PLN', 'pl-pl': 'PLN',
  'cs': 'CZK', 'cs-cz': 'CZK',
};

function detectCurrencyFromLocale() {
  const locale = (navigator.language || navigator.userLanguage || 'en').toLowerCase();
  // Try exact match first (e.g., "en-gb"), then language only (e.g., "en")
  return LOCALE_CURRENCY_MAP[locale] || LOCALE_CURRENCY_MAP[locale.split('-')[0]] || 'EUR';
}

export function CurrencyProvider({ children }) {
  const [currency, setCurrency] = useState(() => {
    const saved = localStorage.getItem('app_currency');
    return saved || detectCurrencyFromLocale();
  });

  useEffect(() => {
    localStorage.setItem('app_currency', currency);
  }, [currency]);

  // Format currency using the detected/selected currency
  const fc = useCallback((amount) => {
    const localeMap = {
      EUR: 'de-DE', GBP: 'en-GB', CHF: 'de-CH', SEK: 'sv-SE',
      DKK: 'da-DK', NOK: 'nb-NO', PLN: 'pl-PL', CZK: 'cs-CZ'
    };
    return new Intl.NumberFormat(localeMap[currency] || 'en-GB', {
      style: 'currency',
      currency: currency,
    }).format(amount);
  }, [currency]);

  // Get the currency symbol for chart axis labels
  const symbol = useMemo(() => {
    const c = SUPPORTED_CURRENCIES.find(s => s.code === currency);
    return c ? c.symbol : '\u20ac';
  }, [currency]);

  const value = useMemo(() => ({
    currency,
    setCurrency,
    fc,
    symbol,
    currencies: SUPPORTED_CURRENCIES
  }), [currency, setCurrency, fc, symbol]);

  return (
    <CurrencyContext.Provider value={value}>
      {children}
    </CurrencyContext.Provider>
  );
}

export function useCurrency() {
  const context = useContext(CurrencyContext);
  if (!context) {
    throw new Error('useCurrency must be used within a CurrencyProvider');
  }
  return context;
}
