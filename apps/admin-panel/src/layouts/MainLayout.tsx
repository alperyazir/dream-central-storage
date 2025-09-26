import { Outlet } from 'react-router-dom';

import NavBar from '../components/NavBar';

import '../styles/layout.css';

const MainLayout = () => {
  return (
    <div className="layout">
      <aside className="layout__sidebar">
        <NavBar />
      </aside>
      <main className="layout__content">
        <Outlet />
      </main>
    </div>
  );
};

export default MainLayout;
