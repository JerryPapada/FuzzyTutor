import { useEffect, useMemo, useRef, useState } from "react";

export default function useElapsedTimer(activeTask) {
  const [clock, setClock] = useState(Date.now());
  const taskStartedAt = useRef(Date.now());

  useEffect(() => {
    const intervalId = window.setInterval(() => setClock(Date.now()), 1000);
    return () => window.clearInterval(intervalId);
  }, []);

  useEffect(() => {
    taskStartedAt.current = Date.now();
    setClock(Date.now());
  }, [activeTask?.id]);

  const elapsedSeconds = useMemo(() => {
    if (!activeTask) {
      return 0;
    }

    return Math.max(0, Math.round((clock - taskStartedAt.current) / 1000));
  }, [activeTask, clock]);

  return { elapsedSeconds, taskStartedAt };
}
