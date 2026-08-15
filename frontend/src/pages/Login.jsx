import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, Activity, ArrowRight } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import { validateEmail } from '../utils/validators';

const Login = () => {
  const navigate = useNavigate();
  const { login, isAuthenticated, error: authError } = useAuth();

  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
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
      console.error('Login error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className=" flex items-center justify-center px-4 py-8 sm:py-12">
      <div className="w-full max-w-md">
        {/* Logo and Title */}
        <div className="text-center mb-8 sm:mb-10 animate-fade-in">
          <div className="inline-flex items-center justify-center w-16 h-16 sm:w-20 sm:h-20 bg-brand-600 rounded-2xl shadow-xl mb-5 sm:mb-6 transform hover:scale-105 transition-transform">
            <Activity className="w-9 h-9 sm:w-11 sm:h-11 text-white" />
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-gray-100 mb-2 sm:mb-3">EventPulse</h1>
          <p className="text-base sm:text-lg text-gray-400">Real-time Analytics Platform</p>
        </div>

        {/* Login Card */}
        <div className="bg-ink-900 rounded-2xl shadow-xl border-2 border-ink-800 p-6 sm:p-8 transform hover:shadow-2xl transition-all">
          <div className="mb-6">
            <h2 className="text-xl sm:text-2xl font-bold text-gray-100 mb-1 sm:mb-2">Welcome back</h2>
            <p className="text-sm sm:text-base text-gray-400">Sign in to your account to continue</p>
          </div>

          {/* Global Error */}
          {authError && (
            <div className="mb-5 sm:mb-6 p-3 sm:p-4 bg-bad/10 border-2 border-bad/30 rounded-xl animate-shake">
              <p className="text-xs sm:text-sm font-medium text-bad">{authError}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5">
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
              icon={ArrowRight}
            >
              Sign In
            </Button>
          </form>

          {/* Divider */}
          <div className="relative my-6 sm:my-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t-2 border-ink-700"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-3 sm:px-4 bg-ink-900 text-gray-500 font-medium">New to EventPulse?</span>
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
        <p className="text-center text-gray-500 text-xs sm:text-sm mt-6 sm:mt-8">
          © 2026 EventPulse Analytics. All rights reserved.
        </p>
      </div>
    </div>
  );
};

export default Login;