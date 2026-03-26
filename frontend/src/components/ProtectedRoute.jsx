import { Navigate, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import API from "../api";

export default function ProtectedRoute({ children, allowedRoles }) {
  const [isValidating, setIsValidating] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userRole, setUserRole] = useState(null);
  const [needsPasswordChange, setNeedsPasswordChange] = useState(false);
  const location = useLocation();

  useEffect(() => {
    let cancelled = false;

    const validateToken = async () => {
      const token = localStorage.getItem("access_token");
      const userStr = localStorage.getItem("user");
      
      if (!token || !userStr) {
        if (!cancelled) setIsValidating(false);
        return;
      }

      try {
        // Parse stored user data for quick role check
        const storedUser = JSON.parse(userStr);

        // Quick local validation first — only call API if token exists
        const response = await API.get("auth/profile/");
        const user = response.data?.user;

        if (cancelled) return;

        if (!user) {
          setIsAuthenticated(false);
          setIsValidating(false);
          return;
        }

        setUserRole(user.role);
        
        if (user.is_first_login && location.pathname !== '/change-password') {
          setNeedsPasswordChange(true);
        }
        
        // Check if user role is allowed
        if (allowedRoles && !allowedRoles.includes(user.role)) {
          setIsAuthenticated(false);
        } else {
          setIsAuthenticated(true);
        }
      } catch (error) {
        if (cancelled) return;

        // If the error is a 403 and indicates a forced password change, don't logout
        if (error.response?.status === 403 && error.response?.data?.force_password_change) {
          setNeedsPasswordChange(true);
          setIsAuthenticated(true);
        } else {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          localStorage.removeItem("user");
          setIsAuthenticated(false);
        }
      } finally {
        if (!cancelled) setIsValidating(false);
      }
    };

    validateToken();

    return () => { cancelled = true; };
  }, [allowedRoles, location.pathname]);

  if (isValidating) {
    return (
      <div className="min-h-screen bg-mesh flex items-center justify-center">
        <div className="text-center">
          <div className="spinner mx-auto mb-3" />
          <p className="text-surface-400 text-sm">Verifying session...</p>
        </div>
      </div>
    );
  }

  if (needsPasswordChange) {
    return <Navigate to="/change-password" />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/" />;
  }

  return children;
}
