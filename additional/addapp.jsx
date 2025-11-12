// src/App.js
import React, { useEffect, useState } from "react";
import {  BrowserRouter as Router, Routes, Route, Navigate, useNavigate,} from "react-router-dom";

import SignIn from "./components/SignIn";
import SignUp from "./components/SignUp";
import TimeUtilizer from "./components/TimeUtilizer";
import History from "./components/History";

// Simple protected-route wrapper
function ProtectedRoute({ isLoggedIn, children }) {
  if (!isLoggedIn) return <Navigate to="/signin" replace />;
  return children;
}

// Small wrappers so we can pass the onSwitch + setIsLoggedIn props
function SignInPage({ setIsLoggedIn }) {
  const navigate = useNavigate();
  const onSwitch = () => navigate("/signup");
  return <SignIn onSwitch={onSwitch} setIsLoggedIn={setIsLoggedIn} />;
}

function SignUpPage({ setIsLoggedIn }) {
  const navigate = useNavigate();
  const onSwitch = () => navigate("/signin");
  return <SignUp onSwitch={onSwitch} setIsLoggedIn={setIsLoggedIn} />;
}

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  // Persist auth via localStorage (you already set username on login)
  useEffect(() => {
    const hasUser = !!localStorage.getItem("username");
    setIsLoggedIn(hasUser);
  }, []);

  return (
    <Router>
      <Routes>
        {/* Auth */}
        <Route path="/signin" element={<SignInPage setIsLoggedIn={setIsLoggedIn} />} />
        <Route path="/signup" element={<SignUpPage setIsLoggedIn={setIsLoggedIn} />} />

        {/* App (protected) */}
        <Route
          path="/timeutilizer"
          element={
            <ProtectedRoute isLoggedIn={isLoggedIn}>
              <TimeUtilizer />
            </ProtectedRoute>
          }
        />
        <Route
          path="/history"
          element={
            <ProtectedRoute isLoggedIn={isLoggedIn}>
              <History />
            </ProtectedRoute>
          }
        />


        {/* Defaults / redirects */}
        <Route
          path="/"
          element={<Navigate to={isLoggedIn ? "/timeutilizer" : "/signin"} replace />}
        />
        <Route path="/" element={<SignIn />} />
      </Routes>
    </Router>
  );
}
//additional app.jsx in case of emergency