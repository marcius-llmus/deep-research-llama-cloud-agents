export function MarkdownPreview({ value }: { value: string }) {
  // No markdown renderer dependency in the current template.
  // For now we show it in a preformatted block.
  return (
    <pre className="whitespace-pre-wrap break-words text-sm leading-6 text-gray-800">
      {value}
    </pre>
  );
}

