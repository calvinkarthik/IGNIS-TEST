import "@testing-library/jest-dom/vitest";

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

Object.defineProperty(globalThis, "ResizeObserver", { value: ResizeObserverStub, writable: true });
Object.defineProperty(URL, "createObjectURL", { value: () => "blob:test", writable: true });
Object.defineProperty(URL, "revokeObjectURL", { value: () => undefined, writable: true });

