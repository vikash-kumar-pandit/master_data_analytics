import React, { useState } from 'react';
import { DashboardLayout, SidebarNav, PageContainer } from '../components/layout/DashboardLayout';
import {
  Alert,
  Badge,
  Button,
  Card,
  Input,
  Spinner,
  Progress,
  Tooltip,
  Modal,
  Tabs,
} from '../components/ui';
import { DataTable, FormBuilder, StatCard } from '../components/ui/DataComponents';
import { useToast } from '../context/NotificationContext';
import { useTheme } from '../context/ThemeContext';
import {
  Home,
  Settings,
  Users,
  BarChart3,
  Bell,
  LogOut,
  Plus,
  Edit2,
  Trash2,
} from 'lucide-react';

/**
 * Example Dashboard Page
 * Demonstrates usage of all UI components
 */
export function ExampleDashboard() {
  const { isDark } = useTheme();
  const { success, error, warning } = useToast();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [alertVisible, setAlertVisible] = useState(true);

  // Sample data
  const navItems = [
    { id: 'home', label: 'Home', icon: <Home className="w-5 h-5" /> },
    { id: 'users', label: 'Users', icon: <Users className="w-5 h-5" /> },
    { id: 'analytics', label: 'Analytics', icon: <BarChart3 className="w-5 h-5" /> },
    { id: 'settings', label: 'Settings', icon: <Settings className="w-5 h-5" /> },
  ];

  const users = [
    { id: 1, name: 'John Doe', email: 'john@example.com', role: 'Admin', status: 'Active' },
    { id: 2, name: 'Jane Smith', email: 'jane@example.com', role: 'User', status: 'Active' },
    { id: 3, name: 'Bob Johnson', email: 'bob@example.com', role: 'User', status: 'Inactive' },
  ];

  const columns = [
    { key: 'name', label: 'Name', sortable: true },
    { key: 'email', label: 'Email', sortable: true },
    { key: 'role', label: 'Role' },
    {
      key: 'status',
      label: 'Status',
      render: (value) => (
        <Badge variant={value === 'Active' ? 'secondary' : 'outline'}>
          {value}
        </Badge>
      ),
    },
    {
      key: 'actions',
      label: 'Actions',
      render: () => (
        <div className="flex gap-2">
          <Button size="sm" variant="ghost" icon={Edit2} />
          <Button size="sm" variant="ghost" icon={Trash2} />
        </div>
      ),
    },
  ];

  const tabs = [
    {
      label: 'Overview',
      content: (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <StatCard
              label="Total Users"
              value="2,543"
              change={12}
              icon={Users}
              color="primary"
            />
            <StatCard
              label="Revenue"
              value="$45,231"
              change={8}
              icon={BarChart3}
              color="success"
            />
            <StatCard
              label="Engagement"
              value="68%"
              change={-4}
              icon={BarChart3}
              color="warning"
            />
            <StatCard
              label="Alerts"
              value="24"
              change={0}
              icon={Bell}
              color="error"
            />
          </div>

          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Upload Progress</h3>
            <Progress value={75} max={100} showLabel={true} />
          </Card>
        </div>
      ),
    },
    {
      label: 'Users',
      content: (
        <Card className="p-6">
          <DataTable columns={columns} data={users} selectable paginated />
        </Card>
      ),
    },
    {
      label: 'Settings',
      content: (
        <Card className="p-6">
          <FormBuilder
            fields={[
              {
                name: 'apiKey',
                label: 'API Key',
                type: 'text',
                placeholder: 'Your API key',
                required: true,
              },
              {
                name: 'theme',
                label: 'Theme',
                type: 'select',
                options: [
                  { label: 'Light', value: 'light' },
                  { label: 'Dark', value: 'dark' },
                  { label: 'Auto', value: 'auto' },
                ],
              },
              {
                name: 'notifications',
                label: 'Enable notifications',
                type: 'checkbox',
                description: 'Receive email notifications',
              },
            ]}
            onSubmit={(values) => {
              success('Settings saved');
              console.log('Settings:', values);
            }}
            submitLabel="Save Settings"
          />
        </Card>
      ),
    },
  ];

  const handleExportClick = () => {
    success('Data exported successfully');
  };

  const handleDelete = () => {
    error('Unable to delete. Permission denied.');
  };

  const handleConfirm = () => {
    warning('Action requires confirmation');
    setIsModalOpen(true);
  };

  return (
    <DashboardLayout
      logo={
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold">BD</span>
          </div>
          <span className="font-bold hidden sm:inline">Analytics</span>
        </div>
      }
      sidebar={<SidebarNav items={navItems} />}
      title="Dashboard"
    >
      <PageContainer
        title="Welcome to Big Data Analytics Platform"
        description="Monitor your data and analytics in real-time"
        actions={
          <div className="flex gap-3">
            <Button variant="secondary" onClick={handleExportClick}>
              Export Data
            </Button>
            <Button variant="primary" icon={Plus} onClick={handleConfirm}>
              New Dataset
            </Button>
          </div>
        }
      >
        {/* Alerts Section */}
        <div className="space-y-4 mb-6">
          {alertVisible && (
            <Alert
              type="info"
              title="Welcome"
              onClose={() => setAlertVisible(false)}
            >
              This is a comprehensive example of the Big Data Analytics Platform UI
              components. Explore all sections to see the features.
            </Alert>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Alert type="success" title="Deployment">
              Latest version deployed successfully
            </Alert>
            <Alert type="warning" title="Warning">
              High memory usage detected
            </Alert>
            <Alert type="error" title="Error">
              Failed to sync data
            </Alert>
          </div>
        </div>

        {/* Badges Section */}
        <Card className="p-6 mb-6">
          <h3 className="text-lg font-semibold mb-4">Badge Examples</h3>
          <div className="flex flex-wrap gap-2">
            <Badge variant="default">Default</Badge>
            <Badge variant="secondary">Secondary</Badge>
            <Badge variant="accent">Accent</Badge>
            <Badge variant="neutral">Neutral</Badge>
            <Badge variant="outline">Outline</Badge>
          </div>
        </Card>

        {/* Buttons Section */}
        <Card className="p-6 mb-6">
          <h3 className="text-lg font-semibold mb-4">Button Variants</h3>
          <div className="flex flex-wrap gap-3">
            <Button variant="primary">Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="accent">Accent</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="ghost">Ghost</Button>
            <Tooltip content="Click to perform action">
              <Button size="sm" disabled>
                Disabled
              </Button>
            </Tooltip>
          </div>
        </Card>

        {/* Spinners */}
        <Card className="p-6 mb-6">
          <h3 className="text-lg font-semibold mb-4">Loading States</h3>
          <div className="flex gap-8">
            <div className="flex flex-col items-center gap-2">
              <Spinner size="sm" />
              <p className="text-xs text-neutral-600 dark:text-neutral-400">Small</p>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Spinner size="md" />
              <p className="text-xs text-neutral-600 dark:text-neutral-400">Medium</p>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Spinner size="lg" />
              <p className="text-xs text-neutral-600 dark:text-neutral-400">Large</p>
            </div>
          </div>
        </Card>

        {/* Tabs Section */}
        <Card className="p-6 mb-6">
          <Tabs tabs={tabs} />
        </Card>

        {/* Modal Example */}
        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title="Confirm Action"
          footer={
            <div className="flex gap-3 justify-end">
              <Button
                variant="secondary"
                onClick={() => setIsModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  setIsModalOpen(false);
                  success('Action confirmed');
                }}
              >
                Confirm
              </Button>
            </div>
          }
        >
          <p>Are you sure you want to proceed with this action? This cannot be undone.</p>
        </Modal>

        {/* Form Section */}
        <Card className="p-6 mb-6">
          <h3 className="text-lg font-semibold mb-4">Contact Form Example</h3>
          <FormBuilder
            fields={[
              {
                name: 'name',
                label: 'Full Name',
                placeholder: 'John Doe',
                required: true,
              },
              {
                name: 'email',
                label: 'Email Address',
                type: 'email',
                placeholder: 'john@example.com',
                required: true,
                validate: (value) => {
                  if (!value.includes('@')) return 'Invalid email';
                  return null;
                },
              },
              {
                name: 'message',
                label: 'Message',
                type: 'textarea',
                placeholder: 'Your message here...',
                required: true,
              },
              {
                name: 'subscribe',
                label: 'Subscribe',
                type: 'checkbox',
                description: 'Subscribe to our newsletter',
              },
            ]}
            onSubmit={(values) => {
              success('Form submitted successfully');
              console.log('Form data:', values);
            }}
            submitLabel="Send Message"
          />
        </Card>

        {/* Input Examples */}
        <Card className="p-6 mb-6">
          <h3 className="text-lg font-semibold mb-4">Input Examples</h3>
          <div className="space-y-4">
            <Input
              label="Text Input"
              placeholder="Enter text..."
            />
            <Input
              label="Email Input"
              type="email"
              placeholder="Enter email..."
            />
            <Input
              label="With Error"
              error="This field is required"
            />
          </div>
        </Card>

        {/* Footer */}
        <div className="text-center py-8 text-neutral-600 dark:text-neutral-400">
          <p>End of example page</p>
        </div>
      </PageContainer>
    </DashboardLayout>
  );
}

export default ExampleDashboard;
