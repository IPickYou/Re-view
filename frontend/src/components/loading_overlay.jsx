import React from "react";

export default function LoadingOverlay({ message }) {
    return (
    <div className="overlay" aria-live="assertive" aria-busy="true">
      <div className="overlay-content" role="status">
        <div className="spinner-large" aria-hidden="true" />
        <div className="overlay-text">{message}</div>
      </div>
    </div>
  );
}