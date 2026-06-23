# Utilities Documentation

Complete reference for all utility functions in the Big Data Analytics Platform.

## Table of Contents

- [String Utils](#string-utils)
- [Array Utils](#array-utils)
- [Object Utils](#object-utils)
- [Date Utils](#date-utils)
- [Validation Utils](#validation-utils)
- [Format Utils](#format-utils)
- [Environment Utils](#environment-utils)
- [Browser Utils](#browser-utils)
- [HTTP Utils](#http-utils)

## String Utils

String manipulation and transformation functions.

### capitalize

Capitalize first letter of string.

```jsx
import { stringUtils } from '@/utils';

stringUtils.capitalize('hello') // 'Hello'
stringUtils.capitalize('WORLD') // 'WORLD'
```

### toTitleCase

Convert to title case (first letter of each word capitalized).

```jsx
stringUtils.toTitleCase('hello world') // 'Hello World'
stringUtils.toTitleCase('REACT JS') // 'React Js'
```

### toCamelCase

Convert to camelCase.

```jsx
stringUtils.toCamelCase('hello-world') // 'helloWorld'
stringUtils.toCamelCase('hello_world') // 'helloWorld'
stringUtils.toCamelCase('hello world') // 'helloWorld'
```

### toSnakeCase

Convert to snake_case.

```jsx
stringUtils.toSnakeCase('helloWorld') // 'hello_world'
stringUtils.toSnakeCase('hello-world') // 'hello_world'
stringUtils.toSnakeCase('hello world') // 'hello_world'
```

### toSlug

Generate URL-friendly slug.

```jsx
stringUtils.toSlug('Hello World!') // 'hello-world'
stringUtils.toSlug('React JS Guide') // 'react-js-guide'
stringUtils.toSlug('Test@#$%^') // 'test'
```

### truncate

Truncate string to specified length.

```jsx
stringUtils.truncate('Hello World', 8) // 'Hello...'
stringUtils.truncate('Short', 10) // 'Short'
stringUtils.truncate('Very long text', 5, '...') // 'Ve...'
```

### reverse

Reverse string.

```jsx
stringUtils.reverse('hello') // 'olleh'
stringUtils.reverse('12345') // '54321'
```

### repeat

Repeat string multiple times.

```jsx
stringUtils.repeat('ha', 3) // 'hahaha'
stringUtils.repeat('*', 5) // '*****'
```

### countOccurrences

Count occurrences of substring.

```jsx
stringUtils.countOccurrences('hello world', 'o') // 2
stringUtils.countOccurrences('banana', 'na') // 2
```

### removeSpecialChars

Remove special characters.

```jsx
stringUtils.removeSpecialChars('hello@world#123') // 'helloworld123'
stringUtils.removeSpecialChars('Test!@#$%') // 'Test'
```

## Array Utils

Array manipulation and transformation functions.

### unique

Remove duplicate elements.

```jsx
arrayUtils.unique([1, 2, 2, 3, 3, 3]) // [1, 2, 3]
arrayUtils.unique(['a', 'b', 'a']) // ['a', 'b']
```

### flatten

Flatten nested arrays.

```jsx
arrayUtils.flatten([[1, 2], [3, 4]]) // [1, 2, 3, 4]
arrayUtils.flatten([1, [2, [3, [4]]]]) // [1, 2, 3, 4]
```

### groupBy

Group array elements by key.

```jsx
const users = [
  { name: 'John', role: 'admin' },
  { name: 'Jane', role: 'user' },
  { name: 'Bob', role: 'admin' }
];

arrayUtils.groupBy(users, 'role')
// {
//   admin: [{name: 'John'...}, {name: 'Bob'...}],
//   user: [{name: 'Jane'...}]
// }
```

### sortBy

Sort array by key.

```jsx
const users = [
  { name: 'Charlie', age: 30 },
  { name: 'Alice', age: 25 },
  { name: 'Bob', age: 28 }
];

arrayUtils.sortBy(users, 'age') // Sort ascending
arrayUtils.sortBy(users, 'age', 'desc') // Sort descending
```

### diff

Find differences between arrays.

```jsx
arrayUtils.diff([1, 2, 3], [2, 3, 4]) // [1]
arrayUtils.diff(['a', 'b', 'c'], ['b', 'd']) // ['a', 'c']
```

### intersect

Find common elements.

```jsx
arrayUtils.intersect([1, 2, 3], [2, 3, 4]) // [2, 3]
arrayUtils.intersect(['a', 'b'], ['b', 'c']) // ['b']
```

### chunk

Split array into chunks.

```jsx
arrayUtils.chunk([1, 2, 3, 4, 5], 2) // [[1, 2], [3, 4], [5]]
arrayUtils.chunk('abcdef'.split(''), 2) // [['a', 'b'], ['c', 'd'], ['e', 'f']]
```

### shuffle

Shuffle array randomly.

```jsx
arrayUtils.shuffle([1, 2, 3, 4, 5]) // [3, 1, 4, 5, 2] (random order)
```

### sum

Calculate sum of array.

```jsx
arrayUtils.sum([1, 2, 3, 4]) // 10
arrayUtils.sum([0.5, 0.5, 1]) // 2
```

### average

Calculate average of array.

```jsx
arrayUtils.average([1, 2, 3, 4]) // 2.5
arrayUtils.average([10, 20, 30]) // 20
```

### max

Find maximum value.

```jsx
arrayUtils.max([1, 5, 3, 2]) // 5
arrayUtils.max([10, 20, 15]) // 20
```

### min

Find minimum value.

```jsx
arrayUtils.min([5, 2, 8, 1]) // 1
arrayUtils.min([100, 50, 75]) // 50
```

## Object Utils

Object manipulation and transformation functions.

### deepClone

Create deep copy of object.

```jsx
const original = { name: 'John', nested: { age: 30 } };
const cloned = objectUtils.deepClone(original);
cloned.nested.age = 25;

console.log(original.nested.age) // 30
console.log(cloned.nested.age) // 25
```

### deepMerge

Recursively merge objects.

```jsx
const obj1 = { a: 1, b: { c: 2 } };
const obj2 = { b: { d: 3 }, e: 4 };

objectUtils.deepMerge(obj1, obj2)
// { a: 1, b: { c: 2, d: 3 }, e: 4 }
```

### pick

Select specific keys from object.

```jsx
const user = { name: 'John', age: 30, email: 'john@example.com' };

objectUtils.pick(user, ['name', 'email'])
// { name: 'John', email: 'john@example.com' }
```

### omit

Exclude specific keys from object.

```jsx
const user = { name: 'John', password: 'secret', email: 'john@example.com' };

objectUtils.omit(user, ['password'])
// { name: 'John', email: 'john@example.com' }
```

### invert

Swap keys and values.

```jsx
const roles = { admin: 1, user: 2, guest: 3 };

objectUtils.invert(roles)
// { 1: 'admin', 2: 'user', 3: 'guest' }
```

### mapValues

Transform all values.

```jsx
const numbers = { a: 1, b: 2, c: 3 };

objectUtils.mapValues(numbers, (val) => val * 2)
// { a: 2, b: 4, c: 6 }
```

### isEmpty

Check if object is empty.

```jsx
objectUtils.isEmpty({}) // true
objectUtils.isEmpty({ name: 'John' }) // false
```

### getIn

Get nested value.

```jsx
const user = { name: 'John', address: { city: 'NYC' } };

objectUtils.getIn(user, 'address.city') // 'NYC'
objectUtils.getIn(user, 'address.zip') // undefined
```

### setIn

Set nested value.

```jsx
const user = { name: 'John' };

objectUtils.setIn(user, 'address.city', 'NYC')
// { name: 'John', address: { city: 'NYC' } }
```

## Date Utils

Date manipulation and formatting functions.

### format

Format date to string.

```jsx
const date = new Date('2024-01-15');

dateUtils.format(date) // '2024-01-15'
dateUtils.format(date, 'DD/MM/YYYY') // '15/01/2024'
dateUtils.format(date, 'YYYY-MM-DD HH:mm') // '2024-01-15 00:00'
```

### addDays

Add days to date.

```jsx
const date = new Date('2024-01-15');

dateUtils.addDays(date, 5) // 2024-01-20
dateUtils.addDays(date, -2) // 2024-01-13
```

### diffDays

Calculate difference in days.

```jsx
const date1 = new Date('2024-01-10');
const date2 = new Date('2024-01-15');

dateUtils.diffDays(date1, date2) // 5
dateUtils.diffDays(date2, date1) // -5
```

### isBetween

Check if date is between two dates.

```jsx
const date = new Date('2024-01-15');
const start = new Date('2024-01-01');
const end = new Date('2024-01-31');

dateUtils.isBetween(date, start, end) // true
```

### startOfDay

Get start of day.

```jsx
const date = new Date('2024-01-15T14:30:45');

dateUtils.startOfDay(date) // 2024-01-15T00:00:00
```

### endOfDay

Get end of day.

```jsx
const date = new Date('2024-01-15T10:30:00');

dateUtils.endOfDay(date) // 2024-01-15T23:59:59
```

## Validation Utils

Validation functions for common formats.

### isEmail

Check if valid email format.

```jsx
validationUtils.isEmail('user@example.com') // true
validationUtils.isEmail('invalid.email') // false
```

### isUrl

Check if valid URL.

```jsx
validationUtils.isUrl('https://example.com') // true
validationUtils.isUrl('not a url') // false
```

### isStrongPassword

Check if password is strong.

Requires: uppercase, lowercase, number, special char, 8+ chars

```jsx
validationUtils.isStrongPassword('Pass123!@#') // true
validationUtils.isStrongPassword('password') // false
```

### isPhone

Check if valid phone number.

```jsx
validationUtils.isPhone('+1 (555) 123-4567') // true
validationUtils.isPhone('1234567') // false
```

### isCreditCard

Check if valid credit card format.

```jsx
validationUtils.isCreditCard('4532 1234 5678 9010') // true
validationUtils.isCreditCard('1234') // false
```

## Format Utils

Format values for display.

### currency

Format as currency.

```jsx
formatUtils.currency(1000) // '$1,000.00'
formatUtils.currency(1000, 'EUR') // '€1,000.00'
```

### percentage

Format as percentage.

```jsx
formatUtils.percentage(0.85) // '85%'
formatUtils.percentage(0.333, 3) // '33.3%'
```

### fileSize

Format file size.

```jsx
formatUtils.fileSize(1024) // '1 KB'
formatUtils.fileSize(1024000) // '1000 KB'
formatUtils.fileSize(1048576) // '1 MB'
```

### number

Format number with decimals.

```jsx
formatUtils.number(1234.567, 2) // '1,234.57'
formatUtils.number(1000) // '1,000'
```

### compactNumber

Format large number compactly.

```jsx
formatUtils.compactNumber(1000) // '1K'
formatUtils.compactNumber(1000000) // '1M'
formatUtils.compactNumber(1500000) // '1.5M'
```

### time

Format seconds as time.

```jsx
formatUtils.time(3661) // '01:01:01'
formatUtils.time(120) // '00:02:00'
```

## Environment Utils

Environment and build-time utilities.

### isDev

Check if in development mode.

```jsx
if (envUtils.isDev()) {
  console.log('Development mode');
}
```

### isProd

Check if in production mode.

```jsx
if (envUtils.isProd()) {
  // Production code
}
```

### isTest

Check if in test mode.

```jsx
if (envUtils.isTest()) {
  // Test code
}
```

### get

Get environment variable.

```jsx
const apiUrl = envUtils.get('API_URL', 'http://localhost:3000');
```

## Browser Utils

Browser-related utilities.

### getBrowserInfo

Get browser information.

```jsx
const browser = browserUtils.getBrowserInfo();
// { name: 'Chrome', version: '120.0.6099.129' }
```

### getDeviceType

Get device type.

```jsx
const device = browserUtils.getDeviceType();
// 'mobile' | 'tablet' | 'desktop'
```

### copyToClipboard

Copy text to clipboard.

```jsx
browserUtils.copyToClipboard('Text to copy');
```

### getScrollPosition

Get current scroll position.

```jsx
const { x, y } = browserUtils.getScrollPosition();
```

### scrollToTop

Scroll to top of page.

```jsx
browserUtils.scrollToTop();
```

### isInViewport

Check if element is in viewport.

```jsx
const element = document.getElementById('my-element');

if (browserUtils.isInViewport(element)) {
  // Element is visible
}
```

## HTTP Utils

HTTP and URL utilities.

### buildQueryString

Build query string from object.

```jsx
httpUtils.buildQueryString({ page: 1, limit: 10 })
// 'page=1&limit=10'
```

### parseQueryString

Parse query string to object.

```jsx
httpUtils.parseQueryString('page=1&limit=10')
// { page: '1', limit: '10' }
```

### buildUrl

Build URL with query parameters.

```jsx
httpUtils.buildUrl('/api/users', { page: 1, limit: 10 })
// '/api/users?page=1&limit=10'
```

## Usage Example

```jsx
import {
  stringUtils,
  arrayUtils,
  objectUtils,
  dateUtils,
  validationUtils,
  formatUtils,
  browserUtils,
  httpUtils
} from '@/utils';

// String manipulation
const slug = stringUtils.toSlug('Hello World!');

// Array operations
const unique = arrayUtils.unique([1, 2, 2, 3]);
const grouped = arrayUtils.groupBy(users, 'role');

// Object operations
const cloned = objectUtils.deepClone(original);
const merged = objectUtils.deepMerge(obj1, obj2);

// Date operations
const formatted = dateUtils.format(new Date(), 'YYYY-MM-DD');
const future = dateUtils.addDays(new Date(), 7);

// Validation
if (validationUtils.isEmail(email)) {
  // Valid email
}

// Formatting
const price = formatUtils.currency(99.99);
const size = formatUtils.fileSize(5242880);

// Browser operations
browserUtils.scrollToTop();
browserUtils.copyToClipboard(text);

// HTTP operations
const url = httpUtils.buildUrl('/api/users', { page: 1 });
```
