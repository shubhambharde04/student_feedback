import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api";
import TeacherDashboard from "./TeacherDashboard";
import HODDashboard from "./HODDashboard";

function StudentDashboard() {
  const [subjects, setSubjects] = useState([]);
  const [user, setUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [subjectsResponse, profileResponse] = await Promise.all([
          API.get("subjects/"),
          API.get("auth/profile/")
        ]);
        
        setSubjects(subjectsResponse.data);
        setUser(profileResponse.data.user);
      } catch (err) {
        console.error("Error fetching data:", err);
      }
    };

    fetchData();
  }, []);

  const handleLogout = async () => {
    try {
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        await API.post("auth/logout/", { refresh: refreshToken });
      }
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");
      navigate("/");
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center p-4 bg-white shadow">
        <h2 className="text-2xl font-bold">Student Dashboard</h2>
        <div className="flex items-center gap-4">
          {user && (
            <span className="text-gray-600">
              Welcome, {user.first_name || user.email} ({user.role})
            </span>
          )}
          <button
            onClick={handleLogout}
            className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600 transition"
          >
            Logout
          </button>
        </div>
      </div>
      
      <div className="p-4">
        <h3 className="text-xl mb-4">Select Subject to Give Feedback</h3>

        {subjects.map((sub) => (
          <div
            key={sub.id}
            onClick={() => navigate("/feedback", { state: { subject: sub } })}
            style={{
              border: "1px solid black",
              padding: "10px",
              margin: "10px",
              cursor: "pointer",
            }}
          >
            {sub.name}
          </div>
        ))}
      </div>
    </div>
  );
}

function Dashboard() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUserProfile = async () => {
      try {
        const response = await API.get("auth/profile/");
        setUser(response.data.user);
      } catch (error) {
        console.error("Error fetching user profile:", error);
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/";
      } finally {
        setLoading(false);
      }
    };

    fetchUserProfile();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg text-red-600">Error loading user profile</div>
      </div>
    );
  }

  switch (user.role) {
    case 'student':
      return <StudentDashboard />;
    case 'teacher':
      return <TeacherDashboard />;
    case 'hod':
      return <HODDashboard />;
    default:
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-lg text-red-600">Unknown user role: {user.role}</div>
        </div>
      );
  }
}

export default Dashboard;