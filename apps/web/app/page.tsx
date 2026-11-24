import Link from "next/link";

export default function HomePage() {
  return (
    <div className="flex flex-col items-start gap-4">
      <h1 className="text-2xl font-bold">Find jobs that fit your resume</h1>
      <p className="text-slate-600">
        Upload your resume and get a ranked list of job matches with an explanation for each
        score.
      </p>
      <Link
        href="/upload"
        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
      >
        Get started
      </Link>
    </div>
  );
}
