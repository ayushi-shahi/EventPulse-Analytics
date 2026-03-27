import React, { createContext, useState, useCallback, useContext } from 'react';

const BellContext = createContext(null);

export const BellProvider = ({ children }) => {
  const [items, setItems] = useState([]);

  const addBell = useCallback((message, type = 'info') => {
    setItems((prev) => [
      { id: Date.now(), message, type, timestamp: new Date() },
      ...prev,
    ].slice(0, 20)); // keep max 20
  }, []);

  const clearBell = useCallback(() => setItems([]), []);

  return (
    <BellContext.Provider value={{ items, addBell, clearBell }}>
      {children}
    </BellContext.Provider>
  );
};

export const useBell = () => useContext(BellContext);