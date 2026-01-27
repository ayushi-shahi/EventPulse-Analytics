# EventPulse Analytics - Frontend

Modern React dashboard for the EventPulse Analytics Platform.

## Features

- 📊 **Real-time Dashboard** - Live metrics and analytics
- 🔑 **API Key Management** - Create and manage API keys
- 📡 **Live Event Feed** - WebSocket-powered real-time event stream
- 🔍 **Event Browser** - Search, filter, and export events
- 🚨 **Alert Management** - Configure smart alerts with notifications
- 🎨 **Modern UI** - Built with Tailwind CSS and Recharts

## Prerequisites

- Node.js 18+ and npm
- Backend API running on http://localhost:8000

## Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` if your backend runs on a different URL.

### 3. Start Development Server

```bash
npm run dev
```

The app will be available at http://localhost:3000

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build

## Project Structure

```
src/
├── components/          # Reusable components
│   ├── common/         # Generic UI components
│   ├── dashboard/      # Dashboard-specific components
│   └── layout/         # Layout components
├── context/            # React Context providers
├── hooks/              # Custom React hooks
├── pages/              # Page components
├── services/           # API services
├── utils/              # Utility functions
├── config.js           # App configuration
├── App.jsx             # Main app component
└── main.jsx            # Entry point
```

## Key Technologies

- **React 18** - UI framework
- **React Router** - Routing
- **Tailwind CSS** - Styling
- **Recharts** - Data visualization
- **WebSocket** - Real-time communication
- **Vite** - Build tool

## Configuration

### API Endpoints

The frontend connects to these backend endpoints:

- `/auth/*` - Authentication
- `/api-keys/*` - API key management
- `/metrics/*` - Analytics and metrics
- `/alerts/*` - Alert configuration
- `/ingest/*` - Event ingestion
- `/ws/live/*` - WebSocket connection

### WebSocket Connection

WebSocket connects to: `ws://localhost:8000/api/v1/ws/live/{client_id}?token={api_key}`

## Development Guide

### Adding a New Page

1. Create page component in `src/pages/`
2. Add route in `src/App.jsx`
3. Add navigation link in `src/components/layout/Sidebar.jsx`

### Adding a New API Endpoint

1. Add method to `src/services/api.js`
2. Use in component with `useAPI` hook for loading states

### Styling Guidelines

- Use Tailwind utility classes
- Follow existing component patterns
- Maintain responsive design (mobile-first)
- Use consistent spacing and colors

## Building for Production

```bash
npm run build
```

Output will be in `dist/` directory.

### Deploy to Netlify/Vercel

1. Connect your Git repository
2. Set build command: `npm run build`
3. Set publish directory: `dist`
4. Add environment variables:
   - `VITE_API_URL` - Your production API URL
   - `VITE_WS_URL` - Your production WebSocket URL

## Troubleshooting

### WebSocket Connection Issues

- Ensure backend is running
- Check API key is selected
- Verify WebSocket URL in `.env`
- Check browser console for errors

### API Errors

- Verify backend is accessible
- Check API_BASE_URL in config
- Ensure JWT token is valid
- Check network tab in browser DevTools

### Build Errors

- Clear node_modules: `rm -rf node_modules && npm install`
- Clear cache: `rm -rf dist`
- Update dependencies: `npm update`

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Performance

- Code splitting with React Router
- Lazy loading for charts
- Optimized bundle size
- Service worker ready

## Security

- JWT token stored in localStorage
- API keys never exposed in URLs
- CORS configured for backend
- XSS protection via React

## Contributing

1. Create feature branch
2. Make changes
3. Test thoroughly
4. Submit pull request

## License

MIT License - see LICENSE file

## Support

For issues and questions, please open a GitHub issue.
