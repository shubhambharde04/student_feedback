import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
import Login from "./pages/Login";
import StudentDashboard from "./pages/StudentDashboard";
import TeacherDashboard from "./pages/TeacherDashboard";
import HODDashboard from "./pages/HODDashboard";
import EnrollmentPage from "./pages/EnrollmentPage";
import TeacherProfile from "./pages/TeacherProfile";
import ReportsPage from "./pages/ReportsPage";
import Feedback from "./pages/Feedback";
import ProtectedRoute from "./components/ProtectedRoute";
import ErrorBoundary from "./components/ErrorBoundary";
import BackendStatusNotification from "./components/BackendStatusNotification";
import BackendStatusDemo from "./components/BackendStatusDemo";
import ChangePassword from "./pages/ChangePassword";
import StudentManagement from "./pages/StudentManagement";
import TeacherManagement from "./pages/TeacherManagement";
import SubjectManagement from "./pages/SubjectManagement";
import DepartmentManagement from "./pages/DepartmentManagement";
import SessionManagement from "./pages/SessionManagement";
import FormBuilder from "./pages/FormBuilder";
import { checkBackendHealth } from "./api";

function App() {
  // Check backend health on app startup
  useEffect(() => {
    const checkInitialBackendHealth = async () => {
      try {
        const isHealthy = await checkBackendHealth();
        if (!isHealthy) {
          console.log('⚠️ Backend is offline on app startup');
          // The BackendStatusNotification will handle showing the appropriate message
        }
      } catch (error) {
        console.log('❌ Backend health check failed on startup');
      }
    };

    checkInitialBackendHealth();

    // Listen for successful reconnection to refresh data
    const handleBackendReconnected = () => {
      console.log('🎉 Backend reconnected, refreshing page data...');
      // You can trigger data refreshes here or dispatch events
      window.location.reload(); // Simple refresh for now
    };

    window.addEventListener('backendReconnected', handleBackendReconnected);

    return () => {
      window.removeEventListener('backendReconnected', handleBackendReconnected);
    };
  }, []);

  return (
    <ErrorBoundary>
      <Router>
        <Routes>
          <Route path="/" element={<Login />} />
          
          <Route 
            path="/student-dashboard" 
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <StudentDashboard />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/feedback" 
            element={
              <ProtectedRoute allowedRoles={['student']}>
                <Feedback />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/teacher-dashboard" 
            element={
              <ProtectedRoute allowedRoles={['teacher']}>
                <TeacherDashboard />
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/hod-dashboard" 
            element={
              <ProtectedRoute allowedRoles={['hod']}>
                <HODDashboard />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/hod/teacher/:id" 
            element={
              <ProtectedRoute allowedRoles={['hod']}>
                <TeacherProfile />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/hod/reports" 
            element={
              <ProtectedRoute allowedRoles={['hod']}>
                <ReportsPage />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/hod/enrollments" 
            element={
              <ProtectedRoute allowedRoles={['hod']}>
                <EnrollmentPage />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/hod/students" 
            element={
              <ProtectedRoute allowedRoles={['hod']}>
                <StudentManagement />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/hod/subjects" 
            element={
              <ProtectedRoute allowedRoles={['hod']}>
                <SubjectManagement />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/hod/teachers-manage" 
            element={
              <ProtectedRoute allowedRoles={['hod']}>
                <TeacherManagement />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/hod/sessions" 
            element={
              <ProtectedRoute allowedRoles={['hod']}>
                <SessionManagement />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/hod/structure" 
            element={
              <ProtectedRoute allowedRoles={['hod']}>
                <DepartmentManagement />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/hod/forms" 
            element={
              <ProtectedRoute allowedRoles={['hod']}>
                <FormBuilder />
              </ProtectedRoute>
            } 
          />

          <Route 
            path="/change-password" 
            element={
              <ProtectedRoute allowedRoles={['student', 'teacher', 'hod', 'admin']}>
                <ChangePassword />
              </ProtectedRoute>
            } 
          />

          {/* Dashboard redirector */}
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute allowedRoles={['student', 'teacher', 'hod']}>
                <DashboardRedirector />
              </ProtectedRoute>
            } 
          />
          
          {/* Backend Status Demo (for testing) */}
          <Route path="/backend-demo" element={<BackendStatusDemo />} />
          
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
        
        {/* Global Backend Status Notification */}
        <BackendStatusNotification />
      </Router>
    </ErrorBoundary>
  );
}

function DashboardRedirector() {
  const userStr = localStorage.getItem("user");
  if (!userStr) return <Navigate to="/" />;
  
  try {
    const user = JSON.parse(userStr);
    
    if (user.role === 'student' && user.is_first_login) {
      return <Navigate to="/change-password" />;
    }
    
    if (user.role === "student") return <Navigate to="/student-dashboard" />;
    if (user.role === "teacher") return <Navigate to="/teacher-dashboard" />;
    if (user.role === "hod") return <Navigate to="/hod-dashboard" />;
  } catch (e) {
    return <Navigate to="/" />;
  }
  
  return <Navigate to="/" />;
}

export default App;
