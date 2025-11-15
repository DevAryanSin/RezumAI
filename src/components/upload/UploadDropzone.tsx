import { useCallback, useState, useEffect, useMemo } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import type { UploadStatus } from "@/types/candidate";

// generate a UUID
const generateUUID = () => crypto?.randomUUID?.() || `rec_${Date.now()}`;

type InternalUpload = {
  uploadId: string;
  filename: string;
  status: "uploading" | "uploaded" | "parsing" | "parsed" | "error";
  progress: number;
  candidateId?: string;
  errorMessage?: string;
};

interface UploadDropzoneProps {
  onUpload: (files: File[]) => void;
  batchName?: string;
  acceptedTypes?: string[];
  maxSizeMB?: number;
  className?: string;
}

export default function UploadDropzone({
  onUpload,
  batchName: initialBatchName,
  acceptedTypes = [".pdf", ".docx"],
  maxSizeMB = 10,
  className,
}: UploadDropzoneProps) {
  const [uploadQueue, setUploadQueue] = useState<InternalUpload[]>([]);

  // 🔥 Recruiter UUID auto-load or auto-create
  const [recruiterId, setRecruiterId] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem("rezumai_recruiter_uuid");
    if (stored) {
      setRecruiterId(stored);
    } else {
      const created = generateUUID();
      localStorage.setItem("rezumai_recruiter_uuid", created);
      setRecruiterId(created);
    }
  }, []);

  // Batch name editable
  const [batchName, setBatchName] = useState(initialBatchName ?? "");

  const acceptMap = useMemo(() => {
    return acceptedTypes.reduce<Record<string, string[]>>((acc, ext) => {
      const e = ext.toLowerCase();
      if (e === ".pdf") acc["application/pdf"] = [".pdf"];
      else if (e === ".docx")
        acc["application/vnd.openxmlformats-officedocument.wordprocessingml.document"] = [".docx"];
      else acc[e] = [ext];
      return acc;
    }, {});
  }, [acceptedTypes]);

  const updateQueue = (uploadId: string, patch: Partial<InternalUpload>) =>
    setUploadQueue((prev) => prev.map((u) => (u.uploadId === uploadId ? { ...u, ...patch } : u)));

  // Upload to backend
  const uploadFileToServer = useCallback(
    (file: File, uploadId: string) =>
      new Promise<void>((resolve) => {
        if (!recruiterId || !batchName) {
          resolve();
          return;
        }

        const xhr = new XMLHttpRequest();
        const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
        xhr.open("POST", `${apiUrl}/upload_resume`, true);

        // progress
        xhr.upload.onprogress = (ev) => {
          if (ev.lengthComputable) {
            const pct = Math.round((ev.loaded / ev.total) * 100);
            updateQueue(uploadId, { progress: pct, status: "uploading" });
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            updateQueue(uploadId, { progress: 100, status: "uploaded" });

            // simulate parsing stage
            setTimeout(() => updateQueue(uploadId, { status: "parsing" }), 300);
            setTimeout(() => {
              updateQueue(uploadId, {
                status: "parsed",
                candidateId: `c_${Date.now()}`,
                progress: 100,
              });
              resolve();
            }, 1700);
          } else {
            const msg = xhr.responseText || xhr.statusText || `Upload failed (${xhr.status})`;
            updateQueue(uploadId, { status: "error", errorMessage: msg, progress: 0 });
            resolve();
          }
        };

        xhr.onerror = () => {
          updateQueue(uploadId, {
            status: "error",
            errorMessage: "Network error",
            progress: 0,
          });
          resolve();
        };

        const fd = new FormData();
        fd.append("recruiter_uuid", recruiterId);
        fd.append("batch_name", batchName);
        fd.append("original_filename", file.name);
        fd.append("file", file);

        xhr.send(fd);
      }),
    [recruiterId, batchName]
  );

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      const timestamp = Date.now();

      const newUploads: InternalUpload[] = acceptedFiles.map((file, idx) => ({
        uploadId: `upload_${timestamp}_${idx}`,
        filename: file.name,
        status: "uploading",
        progress: 0,
      }));

      setUploadQueue((prev) => [...prev, ...newUploads]);

      if (recruiterId && batchName) {
        (async () => {
          for (let i = 0; i < acceptedFiles.length; i++) {
            await uploadFileToServer(acceptedFiles[i], newUploads[i].uploadId);
          }
        })();
      } else {
        onUpload(acceptedFiles);
      }
    },
    [uploadFileToServer, recruiterId, batchName, onUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptMap,
    maxSize: maxSizeMB * 1024 * 1024,
  });

  const removeFromQueue = (uploadId: string) =>
    setUploadQueue((prev) => prev.filter((u) => u.uploadId !== uploadId));

  const getStatusColor = (s: UploadStatus["status"]) => {
    switch (s) {
      case "uploading":
      case "uploaded":
        return "bg-primary";
      case "parsing":
        return "bg-warning";
      case "parsed":
        return "bg-success";
      case "error":
        return "bg-destructive";
      default:
        return "bg-muted";
    }
  };

  const getStatusText = (u: InternalUpload) => {
    switch (u.status) {
      case "uploading":
        return `Uploading... ${u.progress}%`;
      case "uploaded":
        return "Uploaded";
      case "parsing":
        return "Parsing...";
      case "parsed":
        return "Ready";
      case "error":
        return u.errorMessage || "Error";
      default:
        return "";
    }
  };

  return (
    <div className={cn("space-y-6", className)}>
      {/* Recruiter + batch */}
      <div className="space-y-2">
        <div>
          <label className="text-xs text-muted-foreground">Recruiter ID (auto-generated)</label>
          <input
            type="text"
            value={recruiterId}
            readOnly
            className="rounded border p-2 w-full bg-muted cursor-not-allowed"
          />
        </div>

        <div>
          <label className="text-xs text-muted-foreground">Batch Name</label>
          <input
            type="text"
            value={batchName}
            onChange={(e) => setBatchName(e.target.value)}
            placeholder="Enter batch name"
            className="rounded border p-2 w-full"
          />
        </div>
      </div>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 transition-all",
          isDragActive ? "border-primary bg-primary/5 scale-[1.02]" : "border-border hover:border-primary hover:bg-accent"
        )}
      >
        <input {...getInputProps()} />
        <Upload className="mb-4 h-12 w-12 text-muted-foreground" />
        <p className="mb-2 text-lg font-semibold text-foreground">
          {isDragActive ? "Drop files here" : "Drag & drop resumes here"}
        </p>
        <p className="mb-4 text-sm text-muted-foreground">or click to browse</p>
        <p className="text-xs text-muted-foreground">
          Supports {acceptedTypes.join(", ")} • Max {maxSizeMB}MB
        </p>
      </div>

      {/* Upload Queue */}
      {uploadQueue.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-foreground">Upload Queue</h3>

          {uploadQueue.map((upload) => (
            <div key={upload.uploadId} className="flex items-center gap-3 rounded-lg border p-4 bg-card">
              <FileText className="h-8 w-8 text-muted-foreground" />

              <div className="flex-1">
                <div className="flex justify-between items-center mb-1">
                  <p className="truncate text-sm">{upload.filename}</p>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => removeFromQueue(upload.uploadId)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>

                {upload.status === "uploading" && <Progress value={upload.progress} className="mb-1" />}

                <div className="flex items-center gap-2">
                  <div className={cn("h-2 w-2 rounded-full", getStatusColor(upload.status))} />
                  <span className="text-xs text-muted-foreground">{getStatusText(upload)}</span>

                  {upload.candidateId && (
                    <a className="ml-auto text-xs text-primary" href={`/candidate/${upload.candidateId}`}>
                      View →
                    </a>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
