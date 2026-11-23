# Frontend (React + TypeScript + Vite)

Test GUI for the ice radar. The dev server forwards `/api` to the backend on port 8000
(`vite.config.ts`), so start the backend first.

```powershell
npm install
npm run dev      # http://localhost:5173
npm run build    # type-check + production build
```

| File | Role |
|---|---|
| `src/App.tsx` | Page layout and state (sweep, references, A-scan options, log) |
| `src/api.ts` | Typed client for the backend API |
| `src/types.ts` | Shared types (mirror the backend JSON) |
| `src/components/LineChart.tsx` | Dependency-free SVG line chart with hover readout and markers |
| `src/components/*Panel.tsx` | Connection, sweep, references, measurements, simulator, A-scan |
