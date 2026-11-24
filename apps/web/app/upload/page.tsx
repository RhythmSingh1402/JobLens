"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { UploadDropzone } from "@/components/UploadDropzone";
import { uploadResume } from "@/lib/api";

type Status = "idle" | "processing" | "error";

export default function UploadPage() {
  const router = useRouter();
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  async function handleFile(file: File) {
    setStatus("processing");
    setError(null);
    setFileName(file.name);
    try {
      await uploadResume(file);
      router.push("/matches");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold">Upload your resume</h1>
        <p className="mt-1 text-slate-600">
          We&apos;ll extract your experience and rank it against open roles.
        </p>
      </div>

      <UploadDropzone onFileSelected={handleFile} disabled={status === "processing"} />

      {status === "processing" && (
        <div className="flex items-center gap-3 rounded-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-900" />
          Reading {fileName} and scoring it against open roles — this can take up to a minute...
        </div>
      )}

      {status === "error" && error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}
    </div>
  );
}
