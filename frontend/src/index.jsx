import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

import Job from './job';
import Interview from "./interview";

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<Job />} />
      <Route path="/interview" element={<Interview />} />
    </Routes>
  </BrowserRouter>
);