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
    const validateToken = async () => {
      const token = localStorage.getItem("access_token");
      const userStr = localStorage.getItem("user");
      
      if (!token || !userStr) {
        setIsValidating(false);
        return;
      }

      try {
        const response = await API.get("auth/profile/");
        const user = response.data.user;
        setUserRole(user.role);
        
        if (user.role === 'student' && user.is_first_login && location.pathname !== '/change-password') {
          setNeedsPasswordChange(true);
        }
        
        // Check if user role is allowed
        if (allowedRoles && !allowedRoles.includes(user.role)) {
          setIsAuthenticated(false);
        } else {
          setIsAuthenticated(true);
        }
      } catch (error) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user");
        setIsAuthenticated(false);
      } finally {
        setIsValidating(false);
      }
    };

    validateToken();
  }, [allowedRoles]);

  if (isValidating) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
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
