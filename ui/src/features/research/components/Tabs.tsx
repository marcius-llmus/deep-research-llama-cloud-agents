import { ReactNode } from "react";

export type TabItem<T extends string> = {
  key: T;
  label: string;
  content: ReactNode;
};

export function TabButton({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={`px-3 py-2 text-sm rounded-lg border transition ${
        active
          ? "bg-gray-900 text-white border-gray-900"
          : "bg-white text-gray-700 border-gray-200 hover:border-gray-300"
      }`}
      onClick={onClick}
    >
      {label}
    </button>
  );
}

