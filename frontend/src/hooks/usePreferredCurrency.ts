import { useCallback, useEffect, useState } from 'react'

const KEY = 'marketpulse.currency'

export function usePreferredCurrency(defaultCurrency = 'USD') {
  const [currency, setCurrency] = useState<string>(() => localStorage.getItem(KEY) ?? defaultCurrency)
  useEffect(() => {
    localStorage.setItem(KEY, currency)
  }, [currency])
  return { currency, setCurrency: useCallback((c: string) => setCurrency(c.toUpperCase()), []) }
}
