import { useEffect, useState } from "react";

export function useTypewriter(text: string, speed = 10) {
  const [displayed, setDisplayed] = useState("");

  useEffect(() => {
    let index = 0;
    let intervalId: ReturnType<typeof setInterval> | null = null;

    const resetId = setTimeout(() => {
      setDisplayed("");

      intervalId = setInterval(() => {
        index += 1;
        setDisplayed(text.slice(0, index));

        if (index >= text.length && intervalId) {
          clearInterval(intervalId);
        }
      }, speed);
    }, 0);

    return () => {
      clearTimeout(resetId);
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [text, speed]);

  return displayed;
}