import React from 'react';
import { AuthForm } from '../features/auth/AuthForm';
import '../styles/auth.css';

export const AuthPage: React.FC = () => (
    <div className="auth-wrapper">
      <div className="auth-page">
        <AuthForm />
      </div>
    </div>
);
