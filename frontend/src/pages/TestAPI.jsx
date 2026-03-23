import { useEffect, useState } from "react";
import API from "../api";

function TestAPI() {
  const [subjects, setSubjects] = useState([]);

  useEffect(() => {
    API.get("subjects/")
      .then((res) => {
        setSubjects(res.data);
      })
      .catch((err) => {
        console.error(err);
      });
  }, []);

  return (
    <div>
      <h2>Subjects</h2>
      {subjects.map((sub) => (
        <p key={sub.id}>{sub.name}</p>
      ))}
    </div>
  );
}

export default TestAPI;