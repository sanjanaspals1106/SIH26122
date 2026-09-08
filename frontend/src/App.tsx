import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './auth/AuthProvider';
import { ThemeProvider } from './theme/ThemeProvider';
import ProtectedRoute from './auth/ProtectedRoute';
import AppShell from './layout/AppShell';

// Pages
import LoginScreen from './pages/LoginScreen';
import ClaimIntake from './pages/ClaimIntake';
import DailyDigest from './pages/DailyDigest';
import ReviewWorkspace from './pages/ReviewWorkspace';
import Dashboard from './pages/Dashboard';
import ActivityHistory from './pages/ActivityHistory';
import ImpactPreview from './pages/ImpactPreview';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <Router>
            <Routes>
              <Route path="/login" element={<LoginScreen />} />

              <Route element={<AppShell />}>
                {/* Supervisor-only routes */}
                <Route element={<ProtectedRoute allowedRoles={['SUPERVISOR']} />}>
                  <Route path="/" element={<DailyDigest />} />
                  <Route path="/digest" element={<DailyDigest />} />
                  <Route path="/review" element={<ReviewWorkspace />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/history" element={<ActivityHistory />} />
                  <Route path="/impact" element={<ImpactPreview />} />
                </Route>

                {/* Site Engineer-only routes */}
                <Route element={<ProtectedRoute allowedRoles={['SITE_ENGINEER']} />}>
                  <Route path="/intake" element={<ClaimIntake />} />
                </Route>
              </Route>

              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Router>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;