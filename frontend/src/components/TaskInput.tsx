"use client";

import { useState, useRef } from "react";

interface TaskInputProps {
  onSubmit: (input: string) => void;
  onFileUpload: (filePath: string, filename: string) => void;
  isRunning: boolean;
}

const EXAMPLE_PROMPTS = [
  "Read this inspection report, extract key findings and risks, and draft an approval note",
  "Write a Python function that detects duplicate rows in a CSV file",
  "What is shown in this image? Extract all text and identify all components",
  "Analyze this document and summarize the key points",
  "Debug this code and fix any issues",
];

export default function TaskInput({
  onSubmit,
  onFileUpload,
  isRunning,
}: TaskInputProps) {
  const [input, setInput] = useState("");
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const [uploadedFilename, setUploadedFilename] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isRunning) return;
    onSubmit(input.trim());
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const resp = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      });

      if (!resp.ok) throw new Error(`Upload failed: ${resp.statusText}`);

      const data = await resp.json();
      setUploadedFile(data.file_path);
      setUploadedFilename(data.filename);
      onFileUpload(data.file_path, data.filename);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const clearFile = () => {
    setUploadedFile(null);
    setUploadedFilename(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <span className="text-blue-400 text-sm font-semibold">Task Input</span>
      </div>

      {/* File Upload */}
      <div>
        <label className="block text-xs text-gray-500 mb-1">
          Attach File (PDF, image, or code)
        </label>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading || isRunning}
            className="px-3 py-1.5 text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700 
                       rounded-lg text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {uploading ? "Uploading..." : "📎 Attach File"}
          </button>
          {uploadedFilename && (
            <div className="flex items-center gap-1 text-xs text-green-400 bg-green-400/10 
                            px-2 py-1 rounded-lg border border-green-400/20">
              <span>✓ {uploadedFilename}</span>
              <button
                onClick={clearFile}
                className="ml-1 text-gray-500 hover:text-gray-300"
                title="Remove file"
              >
                ×
              </button>
            </div>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          onChange={handleFileChange}
          accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.webp,.bmp,.tiff,.py,.js,.ts,.cpp,.java,.c,.go"
        />
        {uploadError && (
          <p className="text-xs text-red-400 mt-1">{uploadError}</p>
        )}
      </div>

      {/* Text Input */}
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <label className="text-xs text-gray-500">Request / Instruction</label>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isRunning}
          placeholder="Describe what you want the agent to do..."
          className="w-full h-32 bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm 
                     text-gray-200 placeholder-gray-600 resize-none focus:outline-none 
                     focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          onKeyDown={(e) => {
            if (e.key === "Enter" && e.ctrlKey) handleSubmit(e as unknown as React.FormEvent);
          }}
        />
        <p className="text-xs text-gray-600">Ctrl+Enter to submit</p>

        <button
          type="submit"
          disabled={!input.trim() || isRunning}
          className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 
                     disabled:text-gray-500 text-white text-sm font-semibold rounded-lg 
                     transition disabled:cursor-not-allowed"
        >
          {isRunning ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin">⟳</span> Agent Running...
            </span>
          ) : (
            "▶  Run Agent"
          )}
        </button>
      </form>

      {/* Example prompts */}
      <div>
        <p className="text-xs text-gray-600 mb-2">Examples:</p>
        <div className="flex flex-col gap-1">
          {EXAMPLE_PROMPTS.map((prompt, i) => (
            <button
              key={i}
              onClick={() => setInput(prompt)}
              disabled={isRunning}
              className="text-left text-xs text-gray-500 hover:text-gray-300 hover:bg-gray-800 
                         px-2 py-1 rounded transition truncate disabled:cursor-not-allowed"
              title={prompt}
            >
              → {prompt}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
