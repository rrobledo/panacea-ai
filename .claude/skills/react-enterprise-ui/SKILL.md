---
name: react-enterprise-ui
description: >
  Use this skill whenever the user asks to build, extend, or modify any part of a React
  enterprise application: pages, forms, grids, charts, reports, auth screens, modals,
  layouts, or navigation. Triggers include: "add a page", "create a form", "make a grid",
  "add a chart", "printable report", "social login", "master-detail", "CRUD screen",
  "deploy to Vercel", "REST API integration", or any feature that belongs in a business SPA.
---

# React Enterprise UI Skill

## Project Overview

A Vite + React 18 enterprise starter deployed on **Vercel**, with a **REST API** back-end.
Installed libraries:
- **react-router-dom** v6 – SPA routing with auth guard
- **axios** – HTTP client with JWT interceptor
- **react-hook-form** + **@hookform/resolvers/zod** – forms & validation
- **@tanstack/react-table** v8 – feature-rich data grid
- **recharts** – charts & data visualization
- **react-to-print** – printable reports
- **lucide-react** – icon set
- **date-fns** – date utilities

## Directory Structure

```
src/
├── components/
│   ├── auth/          LoginPage.jsx, OAuthCallback.jsx, auth.css
│   ├── layout/        AppLayout.jsx, layout.css
│   ├── ui/            index.jsx  (Modal, Field, Badge, Tabs, EmptyState…)
│   ├── forms/         MasterDetailForm.jsx, ComplexForm.jsx
│   ├── charts/        index.jsx  (KpiCard, RevenueChart, DonutChart…)
│   ├── grid/          DataGrid.jsx
│   └── reports/       PrintableReport.jsx
├── context/           AuthContext.jsx, ToastContext.jsx
├── hooks/             index.js  (useFetch, useList, useMutation, useDebounce…)
├── pages/             DashboardPage, ChartsPage, ProductsPage, FormPages, PrintableReportPage
├── services/          api.js  (axios instance + createCrudService factory)
├── utils/
├── App.jsx            (router + PrivateRoute + AppLayout)
├── main.jsx
└── index.css          (global design tokens + utility classes)
vercel.json            (SPA rewrites + asset cache headers)
.env.example           (VITE_API_URL)
```

---

## 1. Authentication & Social Login

### Social providers (OAuth redirect flow)
```jsx
// LoginPage already wires these. Backend must redirect to /auth/callback?token=JWT
loginWithGoogle()     →  GET  ${VITE_API_URL}/auth/google
loginWithGithub()     →  GET  ${VITE_API_URL}/auth/github
loginWithMicrosoft()  →  GET  ${VITE_API_URL}/auth/microsoft
```

### Protecting routes
```jsx
// Any route wrapped in <PrivateRoute> redirects unauthenticated users to /login
<Route path="/secret" element={<PrivateRoute><SecretPage /></PrivateRoute>} />
```

### Reading the current user
```jsx
const { user, logout, isAuthenticated } = useAuth();
```

---

## 2. REST API Integration

### Pre-built CRUD factory
```js
import { createCrudService } from '../services/api';
const invoicesService = createCrudService('invoices');

// Usage:
await invoicesService.list({ page: 1, limit: 20, status: 'open' });
await invoicesService.get(42);
await invoicesService.create({ ... });
await invoicesService.update(42, { ... });
await invoicesService.remove(42);
```

### Data-fetching hooks
```js
// Paginated list with sort / search / filter baked in:
const { items, total, pages, loading, setPage, setSort, search, filter } = useList('/products');

// Simple fetch:
const { data, loading, error, refetch } = useFetch('/dashboard/stats');

// Mutation:
const { mutate: save, loading: saving } = useMutation(
  (data) => api.post('/invoices', data),
  { onSuccess: () => toast.success('Saved!') }
);
```

---

## 3. Adding a New Page

1. Create `src/pages/WidgetsPage.jsx`
2. Add a route in `App.jsx` inside the protected `<Routes>`:
   ```jsx
   <Route path="/widgets" element={<WidgetsPage />} />
   ```
3. Add to `NAV` array in `AppLayout.jsx`:
   ```js
   { label: 'Widgets', icon: BoxIcon, to: '/widgets' }
   ```

### Page template
```jsx
import { PageLoader, EmptyState, ErrorState } from '../components/ui';
import { useList } from '../hooks';

export const WidgetsPage = () => {
  const { items, loading, error, refetch } = useList('/widgets');

  if (loading) return <PageLoader />;
  if (error)   return <ErrorState message={error.message} onRetry={refetch} />;

  return (
    <div>
      <div className="page-header">
        <div className="page-header-left">
          <div className="page-title">Widgets</div>
          <div className="page-subtitle">Manage widgets</div>
        </div>
        <button className="btn btn-primary btn-sm"><Plus size={14}/> Add Widget</button>
      </div>
      {/* content */}
    </div>
  );
};
```

---

## 4. Master–Detail Form

`MasterDetailForm` handles:
- Header / master fields (customer info, dates, status)
- Dynamic line-item rows with **useFieldArray**
- Real-time computed totals (subtotal → tax → grand total)
- Zod validation
- Dirty-state cancel guard

```jsx
<MasterDetailForm
  initialData={existingOrder}          // optional; omit for "new"
  onSubmit={async (data) => {
    await ordersService.create(data);  // or .update(id, data)
  }}
  onCancel={() => navigate('/orders')}
/>
```

**To add a new line-item column**, add to the schema + add a `<th>/<td>` pair in the table section.

---

## 5. Complex Multi-Tab Form

`ComplexForm` has four tabs: Personal, Company, Security, Notifications.

```jsx
<ComplexForm
  initialData={user}
  onSubmit={async (data) => usersService.update(user.id, data)}
/>
```

**To add a tab**: add to `TABS[]`, add a `{tab === 'mytab' && …}` block in the form body, extend the Zod schema.

---

## 6. DataGrid

`DataGrid` wraps TanStack Table v8 with built-in:
- Column sorting (click header)
- Global search filter
- Row selection checkboxes
- Pagination + page-size selector
- CSV export
- Loading / empty states

```jsx
const COLUMNS = [
  { accessorKey: 'name',   header: 'Name' },
  { accessorKey: 'email',  header: 'Email' },
  { accessorKey: 'status', header: 'Status',
    cell: ({ getValue }) => <StatusBadge status={getValue()} /> },
  { id: 'actions', header: '',
    cell: ({ row }) => <button onClick={() => edit(row.original)}>Edit</button> },
];

<DataGrid
  title="Users"
  columns={COLUMNS}
  data={items}
  loading={loading}
  total={total}
  selectable               // enables checkbox column
  onRowClick={(row) => navigate(`/users/${row.id}`)}
  actions={<button className="btn btn-primary btn-sm">Add User</button>}
/>
```

---

## 7. Charts

All charts are self-contained card components using Recharts:

| Component | Props |
|-----------|-------|
| `KpiCard` | `label, value, change, icon, color` |
| `RevenueChart` | `data[{month, revenue}], height?` |
| `DonutChart` | `data[{name, value}], title?, donut?` |
| `GroupedBarChart` | `data, keys[], title?, height?` |
| `MultiLineChart` | `data, keys[], title?, height?` |
| `RadarChartWidget` | `data, keys[], title?, height?` |

All charts are responsive (`ResponsiveContainer`). `data` can come from a `useFetch()` call.

---

## 8. Printable Reports

```jsx
<PrintableReport
  title="Sales Report Q3 2026"
  subtitle="All regions"
  data={rows}
  columns={[
    { key: 'id',       header: 'Order ID' },
    { key: 'customer', header: 'Customer' },
    { key: 'total',    header: 'Total', align: 'right',
      render: v => `$${v.toFixed(2)}`,
      total:  rows => `$${rows.reduce((s, r) => s + r.total, 0).toFixed(2)}` },
  ]}
  summary={[
    { label: 'Total Orders', value: rows.length },
    { label: 'Revenue',      value: '$12,000' },
  ]}
/>
```

- "Print / PDF" button uses `react-to-print` → triggers native browser print dialog
- "Export CSV" button generates a downloadable `.csv` file
- `columns[].total(rows)` renders a bold footer row for aggregates
- `columns[].render(value, row)` for custom cell rendering
- Wrap in any parent `<div className="no-print">` to hide from print output

---

## 9. UI Components Reference

```jsx
import { Modal, ConfirmDialog, Field, PageLoader, InlineLoader,
         EmptyState, ErrorState, SearchInput, Select,
         StatusBadge, Tabs } from '../components/ui';

// Modal
<Modal open={open} onClose={() => setOpen(false)} title="Edit User" size="lg"
  footer={<><button className="btn btn-secondary" onClick={close}>Cancel</button>
            <button className="btn btn-primary" onClick={save}>Save</button></>}>
  {/* content */}
</Modal>

// Field wrapper (label + error + hint)
<Field label="Email" required error={errors.email?.message} hint="We won't share this">
  <input {...register('email')} className="form-input" />
</Field>

// Status badge (auto-colors: active→green, inactive→gray, pending→yellow…)
<StatusBadge status="active" />

// Tabs
<Tabs tabs={[{value:'a', label:'Tab A'}, {value:'b', label:'Tab B', count: 3}]}
      active={tab} onChange={setTab} />
```

---

## 10. Toast Notifications

```jsx
const toast = useToast();
toast.success('Order created!');
toast.error('Save failed', 5000);   // custom duration ms
toast.warning('Low stock');
toast.info('Sync in progress');
```

---

## 11. CSS Design Tokens

All tokens live in `index.css` as `:root` custom properties:

```css
--primary, --primary-dark, --primary-light
--success, --warning, --danger, --secondary
--gray-50 … --gray-900
--sidebar-width: 260px
--header-height: 64px
--radius, --radius-lg
--shadow, --shadow-md, --shadow-lg
--transition: 0.2s ease
--font: Inter, system-ui…
```

**Utility classes** (use directly in JSX `className`):
- Layout: `flex`, `flex-col`, `grid-2`, `grid-3`, `grid-4`, `gap-2/3/4`, `items-center`, `justify-between`, `justify-end`, `w-full`, `col-span-2`
- Cards: `card`, `card-header`, `card-body`, `card-footer`, `card-title`
- Buttons: `btn btn-primary/secondary/danger/ghost/success`, `btn-sm`, `btn-lg`, `btn-icon`
- Badges: `badge badge-primary/success/warning/danger/gray`
- Forms: `form-group`, `form-label`, `form-input`, `form-select`, `form-textarea`, `form-error`, `form-hint`
- Table: wraps in `table-container` for horizontal scroll
- Alerts: `alert alert-info/success/warning/danger`
- Spacing: `mt-1/2/4`, `mb-2/4`, `p-4/6`
- Print: `no-print`, `print-only`
- Responsive: `hide-mobile`, `show-mobile`

---

## 12. Deploying to Vercel

### One-time setup
1. Push project to GitHub
2. In Vercel → New Project → Import repo
3. Framework: **Vite** (auto-detected)
4. Build command: `npm run build`
5. Output directory: `dist`
6. Add Environment Variable: `VITE_API_URL` = `https://your-api.example.com/api`
7. Deploy

### `vercel.json` handles
- SPA fallback: all routes → `index.html`
- Long-term caching for hashed assets

### Backend CORS
Your REST API must allow `https://your-app.vercel.app` in `Access-Control-Allow-Origin`.

---

## 13. Common Patterns

### CRUD page checklist
- [ ] `useList('/resource')` for paginated data
- [ ] `DataGrid` with action column (Edit / Delete buttons)
- [ ] `Modal` + `react-hook-form` for create/edit
- [ ] `ConfirmDialog` for deletes
- [ ] `useMutation` to call the API
- [ ] `useToast` for feedback

### Form checklist
- [ ] Define Zod schema (`z.object({…})`)
- [ ] `useForm({ resolver: zodResolver(schema) })`
- [ ] Wrap inputs in `<Field>` for label+error
- [ ] `className={errors.field ? 'error' : ''}` on inputs
- [ ] Submit button `disabled={isSubmitting}`

### API response conventions expected
```json
// List endpoint: GET /products?page=1&limit=20
{ "items": [...], "total": 120, "pages": 6 }

// Auth callback redirect: GET /auth/callback?token=JWT_STRING
// or POST /auth/login → { "token": "...", "user": {...} }
```
