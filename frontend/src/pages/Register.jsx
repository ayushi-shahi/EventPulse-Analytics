import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, Activity, CheckCircle } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import { validateEmail, validatePassword } from '../utils/validators';

/**
 * Register Page Component
 */
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

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  // Check password strength
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
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-purple-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo and Title */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-white rounded-2xl shadow-xl mb-4">
            <Activity className="w-10 h-10 text-blue-600" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Create Account</h1>
          <p className="text-blue-200">Get started with EventPulse Analytics</p>
        </div>

        {/* Register Card */}
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          {/* Global Error */}
          {errors.general && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{errors.general}</p>
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
                <div className="mt-2 space-y-1">
                  {passwordStrength.isValid ? (
                    <div className="flex items-center gap-2 text-green-600 text-sm">
                      <CheckCircle className="w-4 h-4" />
                      <span>Strong password</span>
                    </div>
                  ) : (
                    <div className="space-y-1">
                      {passwordStrength.errors.map((error, index) => (
                        <p key={index} className="text-xs text-red-600">
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
            >
              Create Account
            </Button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">Already have an account?</span>
            </div>
          </div>

          {/* Login Link */}
          <Link to="/login">
            <Button variant="outline" size="lg" fullWidth>
              Sign In
            </Button>
          </Link>
        </div>

        {/* Footer */}
        <p className="text-center text-blue-200 text-sm mt-8">
          © 2024 EventPulse. All rights reserved.
        </p>
      </div>
    </div>
  );
};

export default Register;