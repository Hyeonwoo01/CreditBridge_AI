import { useEffect, useState } from 'react';

/** localStorage에 저장되는 상태. 저장소를 쓸 수 없으면 메모리 상태로 동작한다. */
export function useStored<T>(key: string, initial: T): [T, (v: T | ((prev: T) => T)) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(key);
      return raw ? (JSON.parse(raw) as T) : initial;
    } catch {
      return initial;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // 저장 실패는 무시
    }
  }, [key, value]);

  return [value, setValue];
}
