import { FormEvent, useState } from 'react';

import '../styles/page.css';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    // Placeholder submit handler; real implementation will call backend
    console.info('Login submitted', { email, password: password.replace(/./g, '*') });
  };

  return (
    <section className="page page--centered">
      <h1>Admin Login</h1>
      <form className="form" onSubmit={handleSubmit}>
        <label>
          Email
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
        </label>
        <button type="submit">Sign In</button>
      </form>
    </section>
  );
};

export default LoginPage;
