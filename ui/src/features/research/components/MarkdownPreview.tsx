export function MarkdownPreview({ value }: { value: string }) {
  return (
    <pre className="whitespace-pre-wrap break-words text-sm leading-6 text-gray-800">
      {value}
    </pre>
  );
}

