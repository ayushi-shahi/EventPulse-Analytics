import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, Activity, CheckCircle, XCircle, ArrowRight } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import { validateEmail, validatePassword } from '../utils/validators';

const Register = () => {
  const navigate = useNavigate();
  const { register, isAuthenticated } = useAuth();

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [passwordStrength, setPasswordStrength] = useState(null);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    if (formData.password) {
      const validation = validatePassword(formData.password);
      setPasswordStrength(validation);
    } else {
      setPasswordStrength(null);
    }
  }, [formData.password]);

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
    } else {
      const validation = validatePassword(formData.password);
      if (!validation.isValid) {
        newErrors.password = validation.errors[0];
      }
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validate()) return;

    setLoading(true);
    try {
      await register(formData.email, formData.password);
      navigate('/dashboard');
    } catch (err) {
      setErrors({ general: err.message });
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
          <h1 className="text-3xl sm:text-4xl font-bold text-gray-100 mb-2 sm:mb-3">Join EventPulse</h1>
          <p className="text-base sm:text-lg text-gray-400">Create your analytics account</p>
        </div>

        {/* Register Card */}
        <div className="bg-ink-900 rounded-2xl shadow-xl border-2 border-ink-800 p-6 sm:p-8 transform hover:shadow-2xl transition-all">
          <div className="mb-6">
            <h2 className="text-xl sm:text-2xl font-bold text-gray-100 mb-1 sm:mb-2">Get started</h2>
            <p className="text-sm sm:text-base text-gray-400">Fill in your details to create an account</p>
          </div>

          {/* Global Error */}
          {errors.general && (
            <div className="mb-5 sm:mb-6 p-3 sm:p-4 bg-bad/10 border-2 border-bad/30 rounded-xl animate-shake">
              <p className="text-xs sm:text-sm font-medium text-bad">{errors.general}</p>
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

            <div>
              <Input
                label="Password"
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Create a strong password"
                icon={Lock}
                error={errors.password}
                required
                autoComplete="new-password"
              />

              {/* Password Strength Indicator */}
              {passwordStrength && (
                <div className="mt-2.5 sm:mt-3 p-2.5 sm:p-3 rounded-lg border-2 border-ink-700 ">
                  {passwordStrength.isValid ? (
                    <div className="flex items-center gap-2 text-ok">
                      <CheckCircle className="w-4 h-4 sm:w-5 sm:h-5 flex-shrink-0" />
                      <span className="text-xs sm:text-sm font-semibold">Strong password! ✓</span>
                    </div>
                  ) : (
                    <div className="space-y-1.5 sm:space-y-2">
                      <div className="flex items-center gap-2 text-bad mb-1.5 sm:mb-2">
                        <XCircle className="w-4 h-4 sm:w-5 sm:h-5 flex-shrink-0" />
                        <span className="text-xs sm:text-sm font-semibold">Password requirements:</span>
                      </div>
                      {passwordStrength.errors.map((error, index) => (
                        <p key={index} className="text-xs text-bad ml-6 sm:ml-7">
                          • {error}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <Input
              label="Confirm Password"
              type="password"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              placeholder="Confirm your password"
              icon={Lock}
              error={errors.confirmPassword}
              required
              autoComplete="new-password"
            />

            <Button
              type="submit"
              variant="primary"
              size="lg"
              fullWidth
              loading={loading}
              icon={ArrowRight}
            >
              Create Account
            </Button>
          </form>

          {/* Divider */}
          <div className="relative my-6 sm:my-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t-2 border-ink-700"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-3 sm:px-4 bg-ink-900 text-gray-500 font-medium">Already have an account?</span>
            </div>
          </div>

          {/* Login Link */}
          <Link to="/login">
            <Button variant="outline" size="lg" fullWidth>
              Sign In Instead
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

export default Register;