# UI Components Documentation

Complete guide to all UI components in the Big Data Analytics Platform.

## Table of Contents

- [Core Components](#core-components)
- [Layout Components](#layout-components)
- [Data Components](#data-components)
- [Context & Providers](#context--providers)
- [Hooks](#hooks)
- [Utilities](#utilities)

## Core Components

### Alert

Display alert messages with different severity levels.

**Props:**
- `type`: 'info' | 'success' | 'warning' | 'error' (default: 'info')
- `title`: string (optional)
- `children`: React.ReactNode
- `icon`: React.ComponentType (optional)
- `onClose`: () => void (optional)

**Examples:**
```jsx
// Info Alert
<Alert type="info" title="Information">
  This is an informational message
</Alert>

// Success Alert with close button
<Alert type="success" title="Success" onClose={handleClose}>
  Operation completed successfully
</Alert>

// Error Alert
<Alert type="error">
  An error occurred while processing
</Alert>

// Custom Icon
import { AlertTriangle } from 'lucide-react';
<Alert type="warning" icon={AlertTriangle}>
  Warning message
</Alert>
```

### Badge

Compact label for categorization and status.

**Props:**
- `children`: React.ReactNode
- `variant`: 'default' | 'secondary' | 'accent' | 'neutral' | 'outline' (default: 'default')
- `className`: string (optional)

**Examples:**
```jsx
<Badge>Default</Badge>
<Badge variant="secondary">Secondary</Badge>
<Badge variant="accent">Featured</Badge>
<Badge variant="outline">Outlined</Badge>
<Badge variant="neutral" className="text-xs">Small Badge</Badge>
```

### Button

Flexible button component with multiple variants and sizes.

**Props:**
- `children`: React.ReactNode
- `variant`: 'primary' | 'secondary' | 'accent' | 'outline' | 'ghost' (default: 'primary')
- `size`: 'sm' | 'md' | 'lg' | 'xl' (default: 'md')
- `disabled`: boolean (default: false)
- `loading`: boolean (default: false)
- `icon`: React.ComponentType (optional)
- `className`: string (optional)
- All HTML button attributes

**Examples:**
```jsx
// Primary Button
<Button onClick={handleClick}>Click Me</Button>

// With Icon
import { Plus } from 'lucide-react';
<Button icon={Plus} variant="primary" size="lg">
  Create New
</Button>

// Loading State
<Button loading variant="secondary">
  Saving...
</Button>

// Different Variants
<Button variant="primary">Primary</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="outline">Outline</Button>
<Button variant="ghost">Ghost</Button>

// Different Sizes
<Button size="sm">Small</Button>
<Button size="md">Medium</Button>
<Button size="lg">Large</Button>
```

### Card

Container for grouped content with optional hover effect.

**Props:**
- `children`: React.ReactNode
- `className`: string (optional)
- `hover`: boolean (default: false)

**Examples:**
```jsx
// Basic Card
<Card>
  <h3>Card Title</h3>
  <p>Card content here</p>
</Card>

// Card with Hover Effect
<Card hover className="p-6 cursor-pointer">
  <h3>Clickable Card</h3>
  <p>Hover to see the effect</p>
</Card>

// Nested Cards
<Card className="p-6">
  <Card className="p-4 mb-4">
    Inner Card
  </Card>
</Card>
```

### Input

Text input field with validation support.

**Props:**
- `label`: string (optional)
- `error`: string (optional)
- `icon`: React.ComponentType (optional)
- `className`: string (optional)
- All HTML input attributes

**Examples:**
```jsx
// Basic Input
<Input 
  placeholder="Enter text..."
  onChange={handleChange}
/>

// With Label
<Input
  label="Email"
  type="email"
  placeholder="your@email.com"
/>

// With Icon
import { Search } from 'lucide-react';
<Input
  icon={Search}
  placeholder="Search..."
/>

// With Validation Error
<Input
  label="Username"
  error="Username must be at least 3 characters"
  value={username}
  onChange={handleChange}
/>
```

### Spinner

Loading indicator component.

**Props:**
- `size`: 'sm' | 'md' | 'lg' (default: 'md')

**Examples:**
```jsx
// Default Spinner
<Spinner />

// Different Sizes
<Spinner size="sm" />
<Spinner size="md" />
<Spinner size="lg" />

// In a Button
<Button loading>
  <Spinner size="sm" /> Loading...
</Button>
```

### Progress

Progress bar indicator with optional label.

**Props:**
- `value`: number (current progress)
- `max`: number (max progress, default: 100)
- `showLabel`: boolean (default: true)

**Examples:**
```jsx
// Basic Progress
<Progress value={50} max={100} />

// Without Label
<Progress value={75} max={100} showLabel={false} />

// Upload Progress
<Progress value={uploadProgress} max={100} showLabel />
```

### Tooltip

Information on hover.

**Props:**
- `children`: React.ReactNode
- `content`: string (tooltip text)
- `side`: 'top' | 'bottom' (default: 'top')

**Examples:**
```jsx
// Tooltip on Top
<Tooltip content="Click to delete">
  <Button icon={Trash2}>Delete</Button>
</Tooltip>

// Tooltip on Bottom
<Tooltip content="Save changes" side="bottom">
  <Button>Save</Button>
</Tooltip>
```

### Modal

Dialog overlay for confirmation or user interaction.

**Props:**
- `isOpen`: boolean
- `onClose`: () => void
- `title`: string (optional)
- `children`: React.ReactNode
- `footer`: React.ReactNode (optional)

**Examples:**
```jsx
// Basic Modal
<Modal
  isOpen={isModalOpen}
  onClose={handleClose}
  title="Confirm Action"
>
  <p>Are you sure you want to proceed?</p>
</Modal>

// Modal with Footer Actions
<Modal
  isOpen={isOpen}
  onClose={onClose}
  title="Edit Profile"
  footer={
    <div className="flex gap-3 justify-end">
      <Button variant="secondary" onClick={onClose}>Cancel</Button>
      <Button variant="primary" onClick={handleSave}>Save</Button>
    </div>
  }
>
  <form>
    {/* form content */}
  </form>
</Modal>
```

### Tabs

Tab navigation component.

**Props:**
- `tabs`: Array of { label: string, content: React.ReactNode }
- `defaultTab`: number (default: 0)
- `onChange`: (index: number) => void (optional)

**Examples:**
```jsx
<Tabs
  tabs={[
    {
      label: 'Overview',
      content: <OverviewContent />
    },
    {
      label: 'Details',
      content: <DetailsContent />
    },
    {
      label: 'Settings',
      content: <SettingsContent />
    }
  ]}
  defaultTab={0}
  onChange={(index) => console.log('Tab changed to', index)}
/>
```

## Layout Components

### DashboardLayout

Main layout with sidebar and header.

**Props:**
- `children`: React.ReactNode
- `sidebar`: React.ReactNode | (expanded: boolean) => React.ReactNode
- `logo`: React.ReactNode
- `title`: string (optional)

**Examples:**
```jsx
<DashboardLayout
  logo={<Logo />}
  title="Dashboard"
  sidebar={<SidebarNav items={navItems} />}
>
  <PageContainer title="Welcome">
    Your content here
  </PageContainer>
</DashboardLayout>
```

### SidebarNav

Navigation menu for sidebar.

**Props:**
- `items`: Array of { id: string, label: string, icon?: React.ReactNode }
- `expanded`: boolean (default: true)

**Examples:**
```jsx
<SidebarNav
  items={[
    { id: 'home', label: 'Home', icon: <Home /> },
    { id: 'users', label: 'Users', icon: <Users /> },
    { id: 'settings', label: 'Settings', icon: <Settings /> }
  ]}
/>
```

### PageContainer

Container for page content with title and actions.

**Props:**
- `children`: React.ReactNode
- `title`: string (optional)
- `description`: string (optional)
- `actions`: React.ReactNode (optional)

**Examples:**
```jsx
<PageContainer
  title="Users"
  description="Manage platform users"
  actions={
    <Button icon={Plus}>Add User</Button>
  }
>
  <DataTable {...props} />
</PageContainer>
```

## Data Components

### DataTable

Display data in a sortable, filterable table.

**Props:**
- `columns`: Array of { key: string, label: string, sortable?: boolean, render?: (value, row) => React.ReactNode }
- `data`: Array of objects
- `onRowClick`: (row: any) => void (optional)
- `selectable`: boolean (default: false)
- `sortable`: boolean (default: true)
- `paginated`: boolean (default: true)
- `itemsPerPage`: number (default: 10)

**Examples:**
```jsx
<DataTable
  columns={[
    { key: 'name', label: 'Name', sortable: true },
    { key: 'email', label: 'Email' },
    {
      key: 'status',
      label: 'Status',
      render: (value) => <Badge>{value}</Badge>
    }
  ]}
  data={users}
  selectable
  paginated
  itemsPerPage={20}
  onRowClick={handleRowClick}
/>
```

### FormBuilder

Dynamic form generation.

**Props:**
- `fields`: Array of field configurations
- `onSubmit`: (values: any) => void | Promise<void>
- `submitLabel`: string (default: 'Submit')
- `isLoading`: boolean (default: false)

**Field Configuration:**
- `name`: string (required)
- `label`: string
- `type`: 'text' | 'email' | 'password' | 'number' | 'textarea' | 'select' | 'checkbox'
- `placeholder`: string
- `required`: boolean
- `defaultValue`: any
- `validate`: (value) => string | null (optional)
- `options`: Array of { label, value } (for select)
- `rows`: number (for textarea)

**Examples:**
```jsx
<FormBuilder
  fields={[
    {
      name: 'username',
      label: 'Username',
      placeholder: 'john_doe',
      required: true,
      validate: (value) => value.length < 3 ? 'Too short' : null
    },
    {
      name: 'email',
      label: 'Email',
      type: 'email',
      required: true
    },
    {
      name: 'country',
      label: 'Country',
      type: 'select',
      options: [
        { label: 'USA', value: 'us' },
        { label: 'UK', value: 'uk' }
      ]
    },
    {
      name: 'subscribe',
      label: 'Subscribe',
      type: 'checkbox',
      description: 'Subscribe to newsletter'
    }
  ]}
  onSubmit={async (values) => {
    await apiService.post('/users', values);
  }}
  submitLabel="Create Account"
/>
```

### StatCard

Display metric with trend.

**Props:**
- `label`: string
- `value`: string | number
- `change`: number (percentage change)
- `icon`: React.ComponentType
- `color`: 'primary' | 'success' | 'warning' | 'error' (default: 'primary')

**Examples:**
```jsx
<StatCard
  label="Total Users"
  value="2,543"
  change={12}
  icon={Users}
  color="primary"
/>
```

## Context & Providers

### ThemeProvider

Dark mode support with persistence.

**Usage:**
```jsx
import { ThemeProvider, useTheme } from '@/context/ThemeContext';

// Wrap your app
<ThemeProvider>
  <App />
</ThemeProvider>

// Use theme hook
const { isDark, toggle } = useTheme();
```

### ToastProvider

Notification/toast system.

**Usage:**
```jsx
import { ToastProvider, useToast } from '@/context/NotificationContext';

// Wrap your app
<ToastProvider>
  <App />
</ToastProvider>

// Show notifications
const { success, error, warning, info } = useToast();
success('Operation successful');
error('Something went wrong');
```

### DialogProvider

Confirmation dialogs.

**Usage:**
```jsx
import { DialogProvider, useDialog } from '@/context/NotificationContext';

// Wrap your app
<DialogProvider>
  <App />
</DialogProvider>

// Open dialog
const { openDialog } = useDialog();
openDialog({
  title: 'Confirm',
  message: 'Are you sure?',
  type: 'warning',
  onConfirm: () => handleConfirm(),
  confirmText: 'Yes',
  cancelText: 'No'
});
```

### AuthProvider

Authentication management.

**Usage:**
```jsx
import { AuthProvider, useAuth } from '@/context/AuthContext';

// Wrap your app
<AuthProvider>
  <App />
</AuthProvider>

// Use auth hook
const { user, isAuthenticated, login, logout } = useAuth();
```

## Hooks

### useForm

Manage form state and validation.

```jsx
const form = useForm(
  { email: '', password: '' },
  async (values) => {
    await apiService.auth.login(values.email, values.password);
  },
  (values) => {
    const errors = {};
    if (!values.email) errors.email = 'Email required';
    return errors;
  }
);

<Input
  name="email"
  value={form.values.email}
  onChange={form.handleChange}
  error={form.errors.email}
/>
```

### useAsync

Handle async operations.

```jsx
const { data, isLoading, error, execute } = useAsync(fetchUsers);

// Or with manual execution
const { execute: search } = useAsync(
  (query) => apiService.search.global(query),
  false
);

<Input onChange={(e) => search(e.target.value)} />
```

### useDebounce

Debounce value changes.

```jsx
const debouncedSearchTerm = useDebounce(searchTerm, 500);

useEffect(() => {
  if (debouncedSearchTerm) {
    searchUsers(debouncedSearchTerm);
  }
}, [debouncedSearchTerm]);
```

### useLocalStorage

Persist state to localStorage.

```jsx
const [theme, setTheme] = useLocalStorage('theme', 'light');

setTheme('dark'); // Persisted automatically
```

### usePagination

Handle pagination logic.

```jsx
const { currentPage, totalPages, currentItems, nextPage, prevPage } = 
  usePagination(items, 10);
```

### useOutsideClick

Detect clicks outside element.

```jsx
const ref = useOutsideClick(() => {
  setMenuOpen(false);
});

<div ref={ref}>Menu</div>
```

### useToggle

Simple toggle state.

```jsx
const [isOpen, toggle, setTrue, setFalse] = useToggle(false);

<button onClick={toggle}>Toggle</button>
```

### useMediaQuery

Check if media query matches.

```jsx
const isMobile = useMediaQuery('(max-width: 768px)');

{isMobile ? <MobileNav /> : <DesktopNav />}
```

### useCopyToClipboard

Copy text to clipboard.

```jsx
const { copied, copy } = useCopyToClipboard();

<button onClick={() => copy('text')}>
  {copied ? 'Copied!' : 'Copy'}
</button>
```

## Utilities

See [Utils Documentation](./UTILS.md) for complete utility functions reference.

## Styling

All components use Tailwind CSS with custom variables. To customize:

1. Edit `tailwind.config.js` for theme configuration
2. Edit `src/styles-new.css` for global styles
3. Use Tailwind classes directly or create custom components

## Accessibility

All components include:
- Semantic HTML
- ARIA labels and attributes
- Keyboard navigation support
- Focus indicators
- Color contrast compliance

## Performance

- Components use React.memo where appropriate
- Animations use Framer Motion with GPU acceleration
- Lazy loading for heavy components
- Code splitting for routes
