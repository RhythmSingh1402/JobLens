"use client";

import { useRef, useState } from "react";

const ACCEPTED_TYPES = ["application/pdf", "image/png", "image/jpeg"];

export function UploadDropzone({
  onFileSelected,
  disabled,
}: {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function validateAndEmit(file: File) {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setError("Please upload a PDF, PNG, or JPEG file.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("File must be under 10MB.");
      return;
    }
    setError(null);
    onFileSelected(file);
  }

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !disabled) inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          if (disabled) return;
          const file = e.dataTransfer.files?.[0];
          if (file) validateAndEmit(file);
        }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-12 text-center transition-colors ${
          isDragging ? "border-slate-900 bg-slate-100" : "border-slate-300 bg-white"
        } ${disabled ? "cursor-not-allowed opacity-60" : "hover:border-slate-400"}`}
      >
        <p className="font-medium text-slate-700">Drag & drop your resume here</p>
        <p className="mt-1 text-sm text-slate-500">or click to browse — PDF, PNG, or JPEG, up to 10MB</p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_TYPES.join(",")}
          className="hidden"
          disabled={disabled}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) validateAndEmit(file);
          }}
        />
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}
