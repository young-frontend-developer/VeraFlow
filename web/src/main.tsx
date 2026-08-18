import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { migrateStorageKeys } from "./lib/storage-migrations";
import "./index.css";

// Before the first render, and before App's lazy useState initialisers read
// storage. See storage-migrations.ts.
migrateStorageKeys();

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
