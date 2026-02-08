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
      className={`inline-flex items-center min-w-0 max-w-full overflow-hidden px-3 py-1.5 text-sm font-medium rounded-lg border transition h-9 ${
        active
          ? "bg-gray-900 text-white border-gray-900"
          : "bg-white text-gray-700 border-gray-200 hover:border-gray-300"
      }`}
      onClick={onClick}
    >
      <span className="truncate min-w-0">{label}</span>
    </button>
  );
}
