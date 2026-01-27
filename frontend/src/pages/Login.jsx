import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, Activity } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import { validateEmail } from '../utils/validators';

/**
 * Login Page Component
 */
const Login = () => {
  const navigate = useNavigate();
  const { login, isAuthenticated, error: authError } = useAuth();

  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error for this field
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: null }));
    }
  };

  const validate = () => {
    const newErrors = {};

    if (!formData.email) {
      newErrors.email = 'Email is required';
    } else if (!validateEmail(formData.email)) {
      newErrors.email = 'Invalid email format';
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validate()) return;

    setLoading(true);
    try {
      await login(formData.email, formData.password);
      navigate('/dashboard');
    } catch (err) {
      // Error is handled by AuthContext
      console.error('Login error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-purple-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo and Title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-white rounded-2xl shadow-xl mb-4">
            <Activity className="w-10 h-10 text-blue-600" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">EventPulse Analytics</h1>
          <p className="text-blue-200">Sign in to your account</p>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          {/* Global Error */}
          {authError && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{authError}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <Input
              label="Email Address"
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="you@example.com"
              icon={Mail}
              error={errors.email}
              required
              autoComplete="email"
            />

            <Input
              label="Password"
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="Enter your password"
              icon={Lock}
              error={errors.password}
              required
              autoComplete="current-password"
            />

            <Button
              type="submit"
              variant="primary"
              size="lg"
              fullWidth
              loading={loading}
            >
              Sign In
            </Button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">Don't have an account?</span>
            </div>
          </div>

          {/* Register Link */}
          <Link to="/register">
            <Button variant="outline" size="lg" fullWidth>
              Create Account
            </Button>
          </Link>
        </div>

        {/* Footer */}
        <p className="text-center text-blue-200 text-sm mt-8">
          © 2026 EventPulse. All rights reserved.
        </p>
      </div>
    </div>
  );
};

export default Login;