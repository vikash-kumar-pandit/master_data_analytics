/**
 * String manipulation utilities
 */

export const stringUtils = {
  /**
   * Capitalize first letter of string
   */
  capitalize: (str) => str.charAt(0).toUpperCase() + str.slice(1),

  /**
   * Convert to title case
   */
  toTitleCase: (str) =>
    str.replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase()),

  /**
   * Convert to camelCase
   */
  toCamelCase: (str) =>
    str
      .replace(/(?:^\w|[A-Z]|\b\w)/g, (word, index) =>
        index === 0 ? word.toLowerCase() : word.toUpperCase()
      )
      .replace(/\s+/g, ''),

  /**
   * Convert to snake_case
   */
  toSnakeCase: (str) =>
    str
      .replace(/([a-z])([A-Z])/g, '$1_$2')
      .replace(/[\s-]+/g, '_')
      .toLowerCase(),

  /**
   * Generate slug from string
   */
  toSlug: (str) =>
    str
      .toLowerCase()
      .replace(/[^\w\s-]/g, '')
      .replace(/[\s_]+/g, '-')
      .replace(/^-+|-+$/g, ''),

  /**
   * Truncate string
   */
  truncate: (str, length, suffix = '...') =>
    str.length > length ? str.substring(0, length - suffix.length) + suffix : str,

  /**
   * Reverse string
   */
  reverse: (str) => str.split('').reverse().join(''),

  /**
   * Repeat string
   */
  repeat: (str, count) => str.repeat(count),

  /**
   * Count occurrences
   */
  countOccurrences: (str, substr) => str.split(substr).length - 1,

  /**
   * Remove special characters
   */
  removeSpecialChars: (str) => str.replace(/[^a-zA-Z0-9\s]/g, ''),
};

/**
 * Array manipulation utilities
 */
export const arrayUtils = {
  /**
   * Remove duplicates
   */
  unique: (arr) => [...new Set(arr)],

  /**
   * Flatten nested array
   */
  flatten: (arr) => arr.flat(Infinity),

  /**
   * Group by key
   */
  groupBy: (arr, key) =>
    arr.reduce((acc, item) => {
      (acc[item[key]] = acc[item[key]] || []).push(item);
      return acc;
    }, {}),

  /**
   * Sort by key
   */
  sortBy: (arr, key, order = 'asc') =>
    [...arr].sort((a, b) => {
      if (order === 'asc') return a[key] > b[key] ? 1 : -1;
      return a[key] < b[key] ? 1 : -1;
    }),

  /**
   * Find differences
   */
  diff: (arr1, arr2) => arr1.filter((x) => !arr2.includes(x)),

  /**
   * Find intersection
   */
  intersect: (arr1, arr2) => arr1.filter((x) => arr2.includes(x)),

  /**
   * Chunk array
   */
  chunk: (arr, size) => {
    const chunks = [];
    for (let i = 0; i < arr.length; i += size) {
      chunks.push(arr.slice(i, i + size));
    }
    return chunks;
  },

  /**
   * Shuffle array
   */
  shuffle: (arr) => {
    const shuffled = [...arr];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  },

  /**
   * Sum array
   */
  sum: (arr) => arr.reduce((acc, val) => acc + val, 0),

  /**
   * Average
   */
  average: (arr) => arr.length ? arrayUtils.sum(arr) / arr.length : 0,

  /**
   * Max value
   */
  max: (arr) => Math.max(...arr),

  /**
   * Min value
   */
  min: (arr) => Math.min(...arr),
};

/**
 * Object manipulation utilities
 */
export const objectUtils = {
  /**
   * Deep clone
   */
  deepClone: (obj) => JSON.parse(JSON.stringify(obj)),

  /**
   * Deep merge
   */
  deepMerge: (obj1, obj2) => {
    const result = { ...obj1 };
    for (const key in obj2) {
      if (typeof obj2[key] === 'object' && !Array.isArray(obj2[key])) {
        result[key] = objectUtils.deepMerge(result[key] || {}, obj2[key]);
      } else {
        result[key] = obj2[key];
      }
    }
    return result;
  },

  /**
   * Pick specific keys
   */
  pick: (obj, keys) =>
    keys.reduce((acc, key) => {
      if (key in obj) acc[key] = obj[key];
      return acc;
    }, {}),

  /**
   * Omit specific keys
   */
  omit: (obj, keys) =>
    Object.keys(obj).reduce((acc, key) => {
      if (!keys.includes(key)) acc[key] = obj[key];
      return acc;
    }, {}),

  /**
   * Invert keys and values
   */
  invert: (obj) =>
    Object.entries(obj).reduce((acc, [key, val]) => {
      acc[val] = key;
      return acc;
    }, {}),

  /**
   * Transform values
   */
  mapValues: (obj, fn) =>
    Object.entries(obj).reduce((acc, [key, val]) => {
      acc[key] = fn(val, key);
      return acc;
    }, {}),

  /**
   * Check if empty
   */
  isEmpty: (obj) => Object.keys(obj).length === 0,

  /**
   * Get nested value
   */
  getIn: (obj, path) => {
    return path.split('.').reduce((acc, key) => acc?.[key], obj);
  },

  /**
   * Set nested value
   */
  setIn: (obj, path, value) => {
    const keys = path.split('.');
    const lastKey = keys.pop();
    const target = keys.reduce((acc, key) => {
      acc[key] = acc[key] || {};
      return acc[key];
    }, obj);
    target[lastKey] = value;
    return obj;
  },
};

/**
 * Date manipulation utilities
 */
export const dateUtils = {
  /**
   * Format date
   */
  format: (date, format = 'YYYY-MM-DD') => {
    const d = new Date(date);
    const replacements = {
      'YYYY': d.getFullYear(),
      'MM': String(d.getMonth() + 1).padStart(2, '0'),
      'DD': String(d.getDate()).padStart(2, '0'),
      'HH': String(d.getHours()).padStart(2, '0'),
      'mm': String(d.getMinutes()).padStart(2, '0'),
      'ss': String(d.getSeconds()).padStart(2, '0'),
    };
    return format.replace(/YYYY|MM|DD|HH|mm|ss/g, (match) => replacements[match]);
  },

  /**
   * Add days
   */
  addDays: (date, days) => {
    const d = new Date(date);
    d.setDate(d.getDate() + days);
    return d;
  },

  /**
   * Difference in days
   */
  diffDays: (date1, date2) => {
    const d1 = new Date(date1);
    const d2 = new Date(date2);
    return Math.floor((d2 - d1) / (1000 * 60 * 60 * 24));
  },

  /**
   * Is date between
   */
  isBetween: (date, start, end) => {
    const d = new Date(date);
    return d >= new Date(start) && d <= new Date(end);
  },

  /**
   * Start of day
   */
  startOfDay: (date) => {
    const d = new Date(date);
    d.setHours(0, 0, 0, 0);
    return d;
  },

  /**
   * End of day
   */
  endOfDay: (date) => {
    const d = new Date(date);
    d.setHours(23, 59, 59, 999);
    return d;
  },
};

/**
 * Validation utilities
 */
export const validationUtils = {
  /**
   * Is email valid
   */
  isEmail: (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email),

  /**
   * Is URL valid
   */
  isUrl: (url) => {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  },

  /**
   * Is strong password
   */
  isStrongPassword: (password) =>
    /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/.test(password),

  /**
   * Is phone valid
   */
  isPhone: (phone) => /^[+]?[(]?[0-9]{3}[)]?[-\s.]?[0-9]{3}[-\s.]?[0-9]{4,6}$/.test(phone),

  /**
   * Is credit card valid
   */
  isCreditCard: (card) => /^[0-9]{13,19}$/.test(card.replace(/\s/g, '')),
};

/**
 * Format utilities
 */
export const formatUtils = {
  /**
   * Format currency
   */
  currency: (value, currency = 'USD') =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(value),

  /**
   * Format percentage
   */
  percentage: (value, decimals = 2) => `${(value * 100).toFixed(decimals)}%`,

  /**
   * Format file size
   */
  fileSize: (bytes) => {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  },

  /**
   * Format number
   */
  number: (value, decimals = 0) =>
    new Intl.NumberFormat('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value),

  /**
   * Format compact number
   */
  compactNumber: (value) => {
    const suffixes = ['', 'K', 'M', 'B', 'T'];
    const absValue = Math.abs(value);
    let suffixIndex = 0;
    let result = absValue;

    while (result >= 1000 && suffixIndex < suffixes.length - 1) {
      result /= 1000;
      suffixIndex++;
    }

    return (
      (value < 0 ? '-' : '') +
      (result % 1 === 0 ? result : result.toFixed(1)) +
      suffixes[suffixIndex]
    );
  },

  /**
   * Format time
   */
  time: (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours.toString().padStart(2, '0')}:${minutes
      .toString()
      .padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  },
};

/**
 * Environment utilities
 */
export const envUtils = {
  /**
   * Is development
   */
  isDev: () => process.env.NODE_ENV === 'development',

  /**
   * Is production
   */
  isProd: () => process.env.NODE_ENV === 'production',

  /**
   * Is test
   */
  isTest: () => process.env.NODE_ENV === 'test',

  /**
   * Get env variable
   */
  get: (key, defaultValue) => process.env[`VITE_${key}`] || defaultValue,
};

/**
 * Browser utilities
 */
export const browserUtils = {
  /**
   * Get browser info
   */
  getBrowserInfo: () => {
    const ua = navigator.userAgent;
    if (ua.indexOf('Firefox') > -1) return { name: 'Firefox', version: ua.match(/Firefox\/([\d.]+)/)?.[1] };
    if (ua.indexOf('Chrome') > -1) return { name: 'Chrome', version: ua.match(/Chrome\/([\d.]+)/)?.[1] };
    if (ua.indexOf('Safari') > -1) return { name: 'Safari', version: ua.match(/Version\/([\d.]+)/)?.[1] };
    if (ua.indexOf('Edge') > -1) return { name: 'Edge', version: ua.match(/Edg\/([\d.]+)/)?.[1] };
    return { name: 'Unknown', version: 'Unknown' };
  },

  /**
   * Get device type
   */
  getDeviceType: () => {
    const ua = navigator.userAgent.toLowerCase();
    if (/mobile|android|iphone|kindle|blackberry|windows phone/.test(ua)) {
      return 'mobile';
    }
    if (/ipad|tablet/.test(ua)) {
      return 'tablet';
    }
    return 'desktop';
  },

  /**
   * Copy to clipboard
   */
  copyToClipboard: (text) => navigator.clipboard.writeText(text),

  /**
   * Get scroll position
   */
  getScrollPosition: () => ({
    x: window.scrollX,
    y: window.scrollY,
  }),

  /**
   * Scroll to top
   */
  scrollToTop: () => window.scrollTo({ top: 0, behavior: 'smooth' }),

  /**
   * Is element in viewport
   */
  isInViewport: (element) => {
    const rect = element.getBoundingClientRect();
    return (
      rect.top >= 0 &&
      rect.left >= 0 &&
      rect.bottom <= window.innerHeight &&
      rect.right <= window.innerWidth
    );
  },
};

/**
 * HTTP utilities
 */
export const httpUtils = {
  /**
   * Build query string
   */
  buildQueryString: (params) =>
    Object.entries(params)
      .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
      .join('&'),

  /**
   * Parse query string
   */
  parseQueryString: (qs) => {
    const params = {};
    new URLSearchParams(qs).forEach((value, key) => {
      params[key] = value;
    });
    return params;
  },

  /**
   * Build URL
   */
  buildUrl: (base, params) =>
    params ? `${base}?${httpUtils.buildQueryString(params)}` : base,
};
