export const SITE = {
  name: 'DataTales',
  url: 'https://datatales.co.uk',
  tagline: 'UK public data, turned into clear, verified stories.',
  description:
    'DataTales turns UK public datasets into short, clear stories. Every number is computed from the source data and checked before publishing.',
  author: 'Ammar Asif',
  /** Shown on /contact. Leave empty until the address is confirmed. */
  email: '',
  logo: '/images/logo.png',
  defaultOgImage: '/images/og-default.png',
  locale: 'en_GB',
  /** Google Analytics 4. Loaded only after the visitor accepts (AnalyticsConsent.astro). */
  gaId: 'G-T613P7KVNQ',
} as const;
