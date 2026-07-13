"use client";

import { useState } from "react";

export default function TestComponent() {
  const [count, setCount] = useState(0);

  return (
    <div className="p-4 bg-red-500">
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>Increment</button>
    </div>
  );
}